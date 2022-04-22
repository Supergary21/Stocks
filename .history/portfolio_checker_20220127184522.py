import asyncio, threading
from timeit import *
import os, math, subprocess, time
import mplfinance as mpf
from alpaca_trade_api.rest import *
from autobahn.asyncio.component import Component, run, Session
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

account_info1 = {
  "public_key": 'PKG77R4EUWQ76WC12PI5',
  "private_key": 'YvNim9ia5ov4oJ7WHLv6ElPYQMcMTZMMTP3pLjtp',
  "api_link": 'https://paper-api.alpaca.markets'
}

def dfToDict(date, prices):
  return {
    "open": prices['open'][date],
    "close": prices['close'][date],
    "high": prices['high'][date],
    "low": prices['low'][date]
  }

async def main():
  report_database = ReportDatabase(report_proxy, None)

  broker = Broker(account_info1)
  api = broker.api

  now = datetime.fromisoformat("2022-01-21")
  report = report_database.getTopResults(now, 6)
  stocks = [entry.stock for entry in report.entries]
  print(stocks)
  queue = janus.Queue()
  price_data = {}
  for stock in stocks:
    data = api.get_bars(stock, TimeFrame.Day, "2022-01-25", "2022-01-26", adjustment='raw')
    price_data[stock] = data[-1].c


  for entry in report.entries:
    recent_price = price_data[entry.stock]
    profit = recent_price - entry.close_price
    
    print(entry.stock, round(profit,2))

asyncio.run(main())