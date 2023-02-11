from peewee import *
from src.stock.repos.report_model import *
from pandas import DataFrame
from alpaca_trade_api.rest import *
from alpaca_trade_api.rest import REST
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from src.stock.calculate.calculations import Calculations
from src.stock.calculate.momentum import Momentum
from src.stock.values.report import Entry, Report
from time import sleep, strftime
from peewee import FieldAccessor
import traceback
from pyoink.values.chart import Chart

from src.stock.values.strategy import *
from src.stock.values.prices import Prices, Price

from src.stock.lib.log.log import Log
import json

class ReportDatabase:
    def __init__(self, log=False):
        self.proxy = report_proxy
        #self.proxy.initialize(SqliteDatabase(name))
        self.database = PostgresqlDatabase(
          "reports",
          user="postgres",
          password="stock",
          host="localhost",
          port=5433
        )
        self.log = Log(can_log=log)
        self.proxy.initialize(self.database)
        self.proxy.connect()

    @property
    def symbols(self) -> list[str]:
      return self.proxy.get_tables()

    def deleteAll(self):
      tables = [newReport(t) for t in self.database.get_tables()]
      self.log.info("Reports Amount Before:", len(tables))
      for t in chunked(tables, 50):
        self.database.drop_tables(t)
      self.log.info("Reports Amount After:", len(self.database.get_tables()))

    def getEntryByDate(self, symbol, date):
      table: ReportsModel = newReport(symbol)
      query = list(table.select().where(table.date == date))
      return Entry.fromDB(query[0])

    def getDatesForSymbol(self, symbol):
      table: ReportsModel = newReport(symbol)
      query = list(table.select(table.date).tuples())
      return [q[0] for q in query]

    def getEntriesByDate(self, date):
      symbols = self.proxy.get_tables()
      entries = []
      for symbol in symbols:
        entry = self.getEntryByDate(symbol, date)
        entries.append(entry)
      
      return entries

    def setupReports(self, all_assets, start_date='2019-11-20', end_date='2022-02-17'):
      for asset in all_assets:
        self.log.info("Loading reports for ", asset)

        # tables = self.proxy.get_tables()
        # table = newReport(asset)
        # if table not in tables:
        #     self.report_proxy.create_tables([table])
        

        weekly_dates = self.getWeeklyDates('2019-11-20', '2022-02-17')

        for date in weekly_dates:
          date = datetime.fromisoformat(date)
          self.saveReport(date)

    def saveEntry(self, entry):
      table = newReport(entry.stock)
      tables = self.proxy.get_tables()
      if table not in tables:
        self.proxy.create_tables([table])
      with self.database.atomic():
        table.create(**entry.toDict())
        self.log.info(f"Saved {entry.stock} on {entry.dateString()}")
    
    def saveEntries(self, entries):
      data = [entry.toDict() for entry in entries]
      if not entries:
        print("GOt None")
        return None
      table = newReport(entries[0].stock)
      tables = self.proxy.get_tables()
      if table not in tables:
        self.proxy.create_tables([table])
      
      with self.database.atomic():
        table.insert_many(data).execute()
      
      print(f"SAVED {entries[0].stock} "*10)
    
    def getMOstRecent(self, symbol) -> list[Entry]:
      table = newReport(symbol)
      query = table.select().paginate(1, 1)
      cursor = self.database.execute(query)
      db_entries = []
      for data in cursor:
        db_entry = ReportsModel(
          id = data[0],
          date = data[1],
          stock = data[2],
          open_price = data[3],
          close_price = data[4],
          atr = data[5],
          percent_atr = data[6],
          two_year_momentum = data[7],
          one_year_momentum = data[8],
          acceleration = data[9],
          column = data[10],
          trend = data[11],
          rsi14 = data[12],
          rsi28 = data[13]
        )
        db_entries.append(db_entry)
      return [Entry.fromDB(db_entry) for db_entry in db_entries]

    def saveReport(self, date):
      all_stocks = self.price_repo.getAllStocks()
      for asset in all_stocks:
        entry = self.generateEntry(asset, date)
        if entry != None:
          self.saveEntry(entry)

    def getWeeklyDates(self, start, end):
      start = datetime.fromisoformat(start)
      end = datetime.fromisoformat(end)
      dates = []
      current = start
      while (current < end):
        dates.append(current)
        current += relativedelta(days=7)

      return dates

    def filledPNF(self, date, stock):
      table_name = f"{date.year}-{date.month}-{date.day}"
      table = newReport(table_name)
      report = table.get(table.stock == stock)
      self.log.info(report.stock, report.column, report.trend)
      if report.column == 'UP' and report.trend == 'UP':
        return True
      else:
        return False

    def updatePnf(self, date, symbol, column, trend):
      table = newReport(symbol)
      with self.database.atomic():
        query = table.update({'column': column, 'trend': trend}).where(table.date == date)
        query.execute()

    def getTopResults(self, date, number_of_results=20):
      table_name = date.strftime("%Y-%m-%d")
      table = newReport(table_name)
      ordering = table.acceleration.desc()
      results = list(table.select().where(table.column == "UP", table.open_price != table.close_price).order_by(ordering).limit(number_of_results))
      #results = list(table.select().where(table.column == "UP" and 1 == 1).limit(number_of_results))
      entries =  [Entry.fromDB(result) for result in results]
      entries = sorted(entries, key=lambda entry: entry.current_momentum, reverse=False)
      return Report(date, entries, number_of_results)

    def getReportsByWeek(self, date):
      all_stocks = self.database.get_tables()
      db_entries = []

      for stock in all_stocks:
        table = newReport(stock)
        db_entry = table.get_by_id(date)
        db_entries.append(db_entry)
      
      return db_entries

    def getReports(self, date, strategy: Strategy, stocks_to_exclude: list[str]):
      number_of_results = 10
      table_name = date.strftime("%Y-%m-%d")
      table = newReport(table_name)

      ordering = Sorting.getFunc(table, strategy.initial_sort)
      secondary_ordering = Sorting.getFunc(table, strategy.secondary_sort)

      #query = table.select().where(table.rsi14 < 50, table.rsi28 < 50, table.rsi28 - table.rsi14 < 4, table.one_year_momentum > 2.3, table.one_year_momentum< 4)
      filters = [Filter.getFunc(table, filter) for filter in strategy.filters]
      query = table.select().where(table.stock.not_in(stocks_to_exclude), *filters)
      query = query.order_by(ordering).limit(strategy.cutoff.value)
      query = query.order_by(secondary_ordering).limit(strategy.portfolio_size.value)
      results = list(query)
      entries =  [Entry.fromDB(result) for result in results]
      return Report(date, entries, number_of_results)

    def generateWeeklyReports(self, stock, start, end):
      dates = self.getWeeklyDates(start, end)
      weekly_reports = []
      start_year = int(datetime.fromisoformat(start).year)

      for date in dates:
        prices = self.price_repo.getTwoYearPrices(stock, str(date))
        entry = self.generateEntry(stock, prices, start_year)
        weekly_reports.append([date, entry])

      return weekly_reports
    
    def generateRepotForStock(self, stock, date):
      pass

    def getReportByDate(self, stock, date):
      table_name = date.strftime("%Y-%m-%d")
      table = newReport(table_name)
      entry = list(table.select().where(table.stock == stock))[0]
      self.log.info(entry.stock)
      return Entry.fromDB(entry)

    @staticmethod
    def getPricesByMonth(prices, current_date):
      result = []
      for price in prices:
        if isinstance(price["date"], str):
          price_date = datetime.fromisoformat(price['date'])
        else:
          price_date = price["date"]

        if price_date.year == current_date.year and price_date.month == current_date.month:
          result.append(price)
      
      return result

    @staticmethod
    def getChartData(prices: Prices):
      box_size = Chart.getBoxSizeATR(prices)
      chart = Chart(prices.symbol, box_size, 3)
      chart.generate(prices.toSimpleDict())
      chart.generateTrends()
      column_direction = ("DOWN", "UP")[chart.last_direction.value]
      trend_direction = ("DOWN", "UP")[chart.trends[-1].direction.value]
      return column_direction, trend_direction

    @staticmethod
    def generateEntry(prices: Prices):
      if not prices.canGetYears(2):
        return None
        
      try:
        r = ReportDatabase.getChartData(prices)
        column_direction , trend_direction = r
      except Exception as e:
        print(f"ERROR -> {prices.symbol} {prices.pretty_date_range}")
        file_name = f"{prices.symbol}-{prices.pretty_date_range}"
        with open(f'problem_json/{file_name}.json', 'w') as f:
          json.dump(prices.toSimpleDict(), f)
        with open(f"errors/{file_name}.txt", "w") as f:
          f.write(str(e))
          f.write(traceback.format_exc())
        return None

      years = prices.getLastYears(2).splitByYear()
      last_year_prices = years[0]
      two_year_prices = years[1]

      current_momentum = Momentum.momentumOneYear(last_year_prices)
      prev_momentum = Momentum.momentumOneYear(two_year_prices)

      rsi14 = Momentum.calculateRsis(prices, 14)[-1]
      rsi28= Momentum.calculateRsis(prices, 28)[-1]

      acceleration = prev_momentum - current_momentum
      price = prices.prices[-1]

      entry = Entry(
        prices.symbol,
        prices.end_date,
        price.open,
        price.close,
        0,
        0,
        current_momentum,
        prev_momentum,
        acceleration,
        rsi14,
        rsi28,
        column=column_direction,
        trend=trend_direction
      )
      return entry