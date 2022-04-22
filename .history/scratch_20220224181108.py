import holidays
from datetime import datetime
from dateutil.easter import *
from dateutil import rrule
from dateutil.relativedelta import relativedelta
#https://gist.github.com/adamJLev/7535869
start = datetime(2022, 1, 1)
dates = []
rrule.rrule(rrule.YEARLY, dtstart=datetime.now(), bymonth=5, byweekday=rrule.MO(-1))
hdays = []
year = 2022
h = holidays.US(years=year)
good_friday = easter(2022) - relativedelta(days=2)
hdays.append(good_friday)
hdays.append(h.get_named("Martin Luther King Jr. Day")[0])
hdays.append(h.get_named("Juneteenth National Independence Day")[0])
hdays.append(h.get_named("Washington's Birthday")[0])
hdays.append(datetime(year, 7, 4))
hdays.append(datetime(year, 5, 30))
hdays.append(h.get_named("Labor Day")[0])
hdays.append(h.get_named("Thanksgiving")[0])
hdays.append(h.get_named("Christmas Day")[0])
hdays.append(datetime(year, 1, 1))

print(hdays)

def get_schedule_holidays_rrules():
  return [
    rrule.rrule(rrule.YEARLY, dtstart=datetime.now(), bymonth=1, bymonthday=1),              # New Years
    rrule.rrule(rrule.YEARLY, dtstart=datetime.now(), bymonth=5, byweekday=rrule.MO(-1)),    # Memorial
    rrule.rrule(rrule.YEARLY, dtstart=datetime.now(), bymonth=7, bymonthday=4),              # Independence
    rrule.rrule(rrule.YEARLY, dtstart=datetime.now(), bymonth=11, byweekday=rrule.TH(4)),    # Thanksgiving
    rrule.rrule(rrule.YEARLY, dtstart=datetime.now(), bymonth=12, bymonthday=25),            # Christmas
  ]

hdays = get_schedule_holidays_rrules()
for holiday in hdays:
  print(holiday)

# while start != datetime(2023, 1, 1):
#   if start in h and h.get(start) == []