import asyncio, threading
from timeit import *
import os, math, subprocess, time
import mplfinance as mpf
from alpaca_trade_api.rest import *
from repos.report_model import *
from repos.price_database import *
from Calculate.calculations import Calculations
from values.report import Entry, Report
from repos.price_database import PricesDatabase
from Calculate.momentum import Momentum
from values.order import Order
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from repos.report_database import ReportDatabase
from broker import Broker
from values.portfolio import Portfolio
import janus
from sty import fg
import pandas as pd

#personal
account_info1 = {
      "public_key": 'PKG77R4EUWQ76WC12PI5',
      "private_key": 'YvNim9ia5ov4oJ7WHLv6ElPYQMcMTZMMTP3pLjtp',
      "api_link": 'https://paper-api.alpaca.markets'
}
#08
account_info2 = {
  "public_key": "PKAJ6YB539JWBMJT81Q8",
  "private_key": "clxZoMjA1rc7RFA42aFcbnAwggp95buT1bwGCHxe",
  "api_link": "https://paper-api.alpaca.markets"
}
#02
account_info3 = {
  "public_key": "PKZBZND7F6PH39SMHJPQ",
  "private_key": "2gENBEvKNSEss7zWkY8N290eIANnv32iUeuHPRFy",
  "api_link": "https://paper-api.alpaca.markets"
}
#03
account_info4 = {
  "public_key": "PKQMDMXG2T2FMQ8AZOY5",
  "private_key": "YVdUWYT7hTVPxpkuwDFi07i3Ib8E1AceHPZha46a",
  "api_link": "https://paper-api.alpaca.markets"
}

account_info5 = {
  "public_key": "PKP33J9QMA0IK97MBED5",
  "private_key": "D2cP3slrGwPm3MeAdQdar2MawUNmYMwaK1Wq99lv",
  "api_link": "https://paper-api.alpaca.markets"
}


broker = Broker(account_info1)
broker2 = Broker(account_info2)
broker3 = Broker(account_info3)
broker4 = Broker(account_info4)
broker5 = Broker(account_info5)


count = 0

assets = broker.getAllAssets()
asset_amount = len(assets)
#assets2 = broker2.getAllAssets()
amount = list(zip(*[iter(assets)]*(len(assets)//10)))

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

brokers = [broker,broker2,broker3,broker4,broker5]

def timeFunc(func):
  def wrapper(*args, **kwargs):
    start_time = datetime.now().timestamp()
    value = func(*args, **kwargs)
    end_time = datetime.now().timestamp()
    print(f"{fg.yellow}TIME:{fg.rs} {func.__name__} took {end_time - start_time}")
    return value
  return wrapper


def dfToDict(date, prices):
  return {
    "date":date,
    "open": prices['open'][date],
    "close": prices['close'][date],
    "high": prices['high'][date],
    "low": prices['low'][date]
  }

@timeFunc
def getTwoYearPrices(stock, prices: DataFrame, orig_date: datetime):
  date_format = "%Y-%m-%d"
  start = orig_date - relativedelta(weeks=104)
  date = orig_date.strftime(date_format)
  start = start.strftime(date_format)
  prices.index = pd.to_datetime(prices.index, format=date_format)
  prices = prices.loc[str(start):str(date)]
  dates = [str(date) for date in prices['open'].keys()]
  data = [dfToDict(date, prices) for date in dates]
  return data

def createBrokerThreadFunc(thread_name):
  def threadFunc(price_queue, gen_report_queue, asset_group, broker):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_date = datetime(2018, 2, 21)
    end_date = datetime(2022, 2, 23)
    broker.getPriceData(asset_group, price_queue.sync_q, gen_report_queue.sync_q, thread_name, start_date=start_date, end_date=end_date)
    print(f"{thread_name} Done")
  
  return threadFunc

def createPriceSaveThreadFunc(thread_name, asset_amount):
  def threadFunc(save_price_queue):
    prices_database = PricesDatabase(price_proxy, "Data/prices.db")
    print(f"Starting {thread_name}")
    for i in range(asset_amount):
      print(i, f"{thread_name} getting data now...")
      message = save_price_queue.sync_q.get()
      asset = message["asset"]
      data = message["data"]
      print(i, f"{thread_name} GOT data for {asset}")
      prices_database.setupPrices(asset, data)
      save_price_queue.sync_q.task_done()
      print(f"{thread_name} done saving for {asset}")
  
  return threadFunc

# async def updateReport(session, stock, prices, current_date):
#   price_data = prepareData(prices)
#   if len(price_data) > 500:
#     result = await session.call('my.func', stock, price_data)
#     column = result['column']
#     trend = result['trend']
    
#     return (trend, column)
#   return None

def generateReportThreadFunc(thread_name):
  def threadFunc(gen_report_queue, save_report_queue):
    keepRunning = True

    while keepRunning:
      try:
        message = gen_report_queue.sync_q.get()
        asset = message["asset"]
        data = message["data"]
        end_date = message["date"]
        start_date = datetime(2018, 2, 21)
      except:
        keepRunning = False
        continue

      print(f"Processing {asset}")
      #result = await updateReport(wamp_session, asset, prices, now)
      now = datetime.fromisoformat(end_date)
      foo = True
      while start_date < now:
        prices = getTwoYearPrices(asset, data, now)
        try:
          entry = ReportDatabase.generateEntry(asset, prices, now)
          print(entry)
        except Exception as e:
          raise e
          keepRunning = False
          print(f"{fg.red}GETTING ENTRY FAILED{fg.rs}")
          entry = None

        now = now - relativedelta(days=7)
        print(f"{fg.cyan}NOW{fg.rs}", str(now))
        print("ENTRY", entry!=None, entry)
        if entry != None:
          print("SENDING", entry.stock)
          print(f"{fg.green}DATE:{fg.rs}", entry.date)
          #save_report_queue.sync_q.put(entry)
        foo = False

    print(f"{thread_name} DONE!")
    keepRunning = False
  return threadFunc

def createReportSaveThreadFunc(thread_name, asset_amount):
  def threadFunc(report_queue):
    report_database = ReportDatabase(report_proxy, "Data/reports.db")
    print("Starting")
    print("ASSET AMOUNT:",asset_amount)
    for i in range(asset_amount):
      entry = report_queue.sync_q.get()
      print("SAVING"*10)
      report_database.saveEntry(entry)
      print(f"Saved {entry}")
  return threadFunc

async def main():
  for i in range(1):
    price_queue = janus.Queue()
    gen_report_queue = janus.Queue()
    save_price_queue = janus.Queue()
    save_report_queue = janus.Queue()
    threadFunc = createBrokerThreadFunc(f"Get Price Thread {i}")
    broker = brokers[i//2]
    thread = threading.Thread(target=threadFunc, args=[price_queue, gen_report_queue, amount[i], broker])
    thread.setDaemon(True)
    thread.start()

  #for i in range(1):
    threadFunc = generateReportThreadFunc(f"Gen Report Thread {i}")
    thread = threading.Thread(target=threadFunc, args=[gen_report_queue, save_report_queue])
    thread.setDaemon(True)
    thread.start()

  for i in range(0):
    priceThreadFunc = createPriceSaveThreadFunc(f"Price Save Thread {i}", asset_amount)
    thread = threading.Thread(target=priceThreadFunc, args=[price_queue])
    thread.setDaemon(True)
    thread.start()


  for i in range(0):
    reportThreadFunc = createReportSaveThreadFunc(f"Report Save Thread{i}", asset_amount)
    thread = threading.Thread(target=reportThreadFunc, args=[save_report_queue])
    thread.setDaemon(True)
    thread.start()

  try:
    while True:
      pass
  except:
    pass
    #print(f"{asset}")

  

    #await prices_database.setupPrices(asset, data)




# thread2 = threading.Thread(target=main)
# thread2.setDaemon(True)
# thread2.start()
asyncio.run(main())
#main()
#prices_database.setupPrices(broker.api, assets)
