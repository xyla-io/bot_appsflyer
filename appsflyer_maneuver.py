import re
import pandas as pd
import importlib
import calendar
import os

from appsflyer.appsflyer_pilot import AppsFlyerPilot
from appsflyer.appsflyer_processor import AppsFlyerProcessor

from selenium.webdriver.common.keys import Keys
from raspador import Maneuver, OrdnanceManeuver, NavigationManeuver, SequenceManeuver, UploadReportRaspador, ClickXPathSequenceManeuver, InteractManeuver, OrdnanceParser, XPath, RaspadorNoOrdnanceError, ClickXPathManeuver, SeekParser, SoupElementParser, FindElementManeuver, ClickSoupElementManeuver, Element, ClickElementManeuver, CollectReportManeuver
from typing import Generator, Optional, Dict, List, Callable
from time import sleep
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, date

import appsflyer.appsflyer_parser
importlib.reload(appsflyer.appsflyer_parser)
from appsflyer.appsflyer_parser import GroupByDropdownsParser, ReportCalendarsParser, DownloadButtonParser

class SignInManeuver(Maneuver[AppsFlyerPilot]):
  def attempt(self, pilot: AppsFlyerPilot):
    email_element = yield ClickElementManeuver(
      instruction='click the email filed',
      seeker=lambda p: p.soup.find('input', {'id': 'user-email'})
    )
    email_element.ordnance.send_keys(pilot.email)
    sleep(1)

    password_element = yield ClickElementManeuver(
      instruction='click the password field',
      seeker=lambda p: p.soup.find('input', {'id': 'password-field'})
    )
    password_element.ordnance.send_keys(pilot.password)
    sleep(1)
    password_element.ordnance.send_keys(Keys.RETURN)
    sleep(pilot.sign_in_wait)

class AddReportGroupingsManeuver(Maneuver[AppsFlyerPilot]):
  groupings: List[str]

  def __init__(self, groupings: List[str]):
    super().__init__()
    self.groupings = groupings

  def attempt(self, pilot: AppsFlyerPilot):
    yield ClickElementManeuver(
      instruction='click the edit cohort button',
      seeker=lambda p: p.soup.find('div', {'class': 'edit-button'}, text=re.compile('Edit cohort'))
    )
    sleep(1)
    for _ in range(max(0, len(self.groupings) - 1)):
      yield ClickElementManeuver(
        instruction='add a report grouping',
        seeker=lambda p: p.soup.find('div', {'class': 'link-title'}, text=re.compile('Group by'))
      )
      sleep(.5)
    
    parser = GroupByDropdownsParser.from_browser(browser=pilot.browser)
    group_by_children = parser.parse().deploy()

    assert len(group_by_children) == len(self.groupings)
    children = [Element(soup_element=c, browser=pilot.browser) for c in group_by_children]
    children = [c for c in children if c.soup_element.text not in self.groupings]
    filtered_groupings = [g for g in self.groupings if g not in [g.text for g in group_by_children]]

    for index, child in enumerate(children):
      child.click()
      input_element = Element(
        soup_element=child.soup_element.findChild('input'),
        browser=pilot.browser
      )
      input_element.send_keys(filtered_groupings[index])
      sleep(.5)
      input_element.send_keys(Keys.DOWN)
      input_element.send_keys(Keys.ENTER)
      sleep(.5)
    
    yield ClickElementManeuver(
      instruction='click the apply changes button',
      seeker=lambda p: p.soup.find('button', text=re.compile('Apply changes'))
    )

class ToggleReportOptionsManeuver(Maneuver[AppsFlyerPilot]):
  def attempt(self, pilot: AppsFlyerPilot):
    yield ClickElementManeuver(
      instruction='click the table toggle button',
      seeker=lambda p: p.soup.find('div', {'class': 'toggle-button-label'}, text=re.compile('Table'))
    )
    yield ClickElementManeuver(
      instruction='click the on day toggle button',
      seeker=lambda p: p.soup.find('div', {'class': 'toggle-button-label'}, text=re.compile('On day'))
    )
    yield ClickElementManeuver(
      instruction='select days dropdown',
      seeker=lambda p: p.soup.find('div', {'class': 'qa-days-selector'})
    )
    yield ClickElementManeuver(
      instruction='select 180 days',
      seeker=lambda p: p.soup.find('div', {'class': 'af-tooltip-content'}, text=re.compile('180 Days'))
    )

class GetLastDateAvailableManeuver(OrdnanceManeuver[AppsFlyerPilot, datetime]):
  def attempt(self, pilot: AppsFlyerPilot):
    yield ClickElementManeuver(
      instruction='click the date range picker',
      seeker=lambda p: p.soup.find('div', {'class': 'date-range-picker-button'})
    )

    selector = CalendarSelector(browser=pilot.browser)
    self.ordnance = selector.get_last_day_available()

    yield ClickElementManeuver(
      instruction='dismiss date range picker',
      seeker=lambda p: p.soup.find('button', {'class': 'date-range-picker-control-button'}, text=re.compile('Cancel'))
    )

class SelectDateRangeManeuver(Maneuver[AppsFlyerPilot]):
  start_date: datetime
  end_date: datetime

  def __init__(self, start: datetime, end: datetime):
    super().__init__()
    self.start_date = start
    self.end_date = end

  def attempt(self, pilot: AppsFlyerPilot):
    yield ClickElementManeuver(
      instruction='click the date range picker',
      seeker=lambda p: p.soup.find('div', {'class': 'date-range-picker-button'})
    )

    selector = CalendarSelector(browser=pilot.browser)
    selector.select_start_date(self.start_date)
    selector.select_end_date(self.end_date)

    yield ClickElementManeuver(
      instruction='apply date range',
      seeker=lambda p: p.soup.find('button', {'class': 'date-range-picker-control-button'}, text=re.compile('Apply'))
    )

class CalendarSelector:
  browser: any

  def __init__(self, browser: any):
    self.browser = browser
  
  @property
  def start_calendar(self) -> any:
    parser = ReportCalendarsParser.from_browser(self.browser)
    calendars = parser.parse().deploy()
    return calendars[0]
  
  @property
  def end_calendar(self) -> any:
    parser = ReportCalendarsParser.from_browser(self.browser)
    calendars = parser.parse().deploy()
    return calendars[1]
  
  @property
  def start_calendar_month(self) -> int:
    month_text = self.start_calendar.findChild('span', {'class': 'rdr-MonthAndYear-month'}).text
    return datetime.strptime(month_text, '%B').month
  
  @property
  def end_calendar_month(self) -> int:
    month_text = self.end_calendar.findChild('span', {'class': 'rdr-MonthAndYear-month'}).text
    return datetime.strptime(month_text, '%B').month
  
  def get_last_day_available(self) -> datetime:
    def get_day_children():
      return self.end_calendar.findChildren('span', {'class': 'rdr-Day'})

    def get_disabled_children():
      return [d for d in get_day_children() if 'is-passive' in d.attrs['class']]

    while len(get_disabled_children()) != len(get_day_children()):
      self.navigate_end_calendar(forward=True)
      sleep(.5)
    
    self.navigate_end_calendar(forward=False)
    sleep(.5)

    enabled_children = [d for d in get_day_children() if 'is-passive' not in d.attrs['class']]
    last_day_child = enabled_children[-1]
    year = self.end_calendar.findChild('span', {'class': 'rdr-MonthAndYear-year'}).text
    date_value = date(int(year), self.end_calendar_month, int(last_day_child.text))
    return datetime.combine(date_value, datetime.min.time())
  
  def navigate_start_calendar(self, forward: bool):
    next_button = Element(
      soup_element=self.start_calendar.findChild('button', {'class': f'rdr-MonthAndYear-button {"next" if forward else "prev"}'}),
      browser=self.browser
    )
    next_button.click()

  def navigate_end_calendar(self, forward: bool):
    next_button = Element(
      soup_element=self.end_calendar.findChild('button', {'class': f'rdr-MonthAndYear-button {"next" if forward else "prev"}'}),
      browser=self.browser
    )
    next_button.click()
  
  def select_start_date(self, date: datetime) -> bool:
    if date.month < self.start_calendar_month:
      while date.month != self.start_calendar_month:
        self.navigate_start_calendar(forward=False)
        sleep(.5)
    elif date.month > self.start_calendar_month:
      while date.month != self.start_calendar_month:
        self.navigate_start_calendar(forward=True)
        sleep(.5)
    
    day_children = self.start_calendar.findChildren('span', {'class': 'rdr-Day'}, text=re.compile(f'^{date.day}$'))
    filtered_children = [c for c in day_children if 'is-passive' not in c.attrs['class']]
    assert len(filtered_children) == 1

    day_element = Element(
      soup_element=filtered_children[0],
      browser=self.browser
    )
    day_element.click()
  
  def select_end_date(self, date: datetime) -> bool:
    if date.month < self.end_calendar_month:
      while date.month != self.end_calendar_month:
        self.navigate_end_calendar(forward=False)
        sleep(.5)
    elif date.month > self.end_calendar_month:
      while date.month != self.end_calendar_month:
        self.navigate_end_calendar(forward=True)
        sleep(.5)
    
    day_children = self.end_calendar.findChildren('span', {'class': 'rdr-Day'}, text=re.compile(f'^{date.day}$'))
    filtered_children = [c for c in day_children if 'is-passive' not in c.attrs['class']]
    assert len(filtered_children) == 1

    day_element = Element(
      soup_element=filtered_children[0],
      browser=self.browser
    )
    day_element.click()

class DownloadReportManeuver(OrdnanceManeuver[AppsFlyerPilot, pd.DataFrame]):
  def attempt(self, pilot: AppsFlyerPilot):
    parser = DownloadButtonParser.from_browser(pilot.browser)
    button = parser.parse().deploy()
    element = Element(soup_element=button, browser=pilot.browser)
    element.click()

    while True:
      sleep(3)
      parser = DownloadButtonParser.from_browser(pilot.browser)
      button = parser.parse().deploy()
      if 'loading' in button.attrs['class']:
        continue
      else:
        break

class AppsFlyerManeuver(OrdnanceManeuver[AppsFlyerPilot, pd.DataFrame]):
  def attempt(self, pilot: AppsFlyerPilot, fly: Callable[[Maneuver], Maneuver]):
    yield NavigationManeuver(url='https://hq1.appsflyer.com/auth/login')
    yield SignInManeuver()

    for app_id in pilot.app_ids.values():
      yield NavigationManeuver(
        url=f'https://hq1.appsflyer.com/cohort/overview#appIds={app_id}'
      )
      sleep(3)
      yield AddReportGroupingsManeuver(groupings=pilot.report_groupings)
      sleep(1)
      yield ToggleReportOptionsManeuver()
      sleep(1)
      
      last_date = (yield GetLastDateAvailableManeuver()).deploy()
      date_groupings = pilot.report_date_groupings(end_date=last_date)

      for date_range in date_groupings:
        yield SelectDateRangeManeuver(
          start=date_range[0],
          end=date_range[1]
        )
        sleep(5)
        yield DownloadReportManeuver()
        sleep(2)

      sleep(8)
      # find the downloaded files and make sure the number of them match the files we downloaded
      downloaded_file_paths = [p for p in Path('.').glob(f'cohort_on day_report_{pilot.email}*.csv')]
      assert len(downloaded_file_paths) == len(date_groupings)

      # create the directory for the app that we're iterating over
      (pilot.download_path / app_id).mkdir()

      # move the downloaded files into the newly created app directory
      for file in downloaded_file_paths:
        target = f'{(pilot.download_path / app_id)}/{file.name}'
        file.rename(target)

      pilot.browser.driver.back()
      sleep(5)

    fly(AppsFlyerCollectManeuver())

class AppsFlyerCollectManeuver(OrdnanceManeuver[AppsFlyerPilot, pd.DataFrame]):
  schema: Optional[str]
  table: Optional[str]
  confirm_upload: Optional[bool]
  download_path: Optional[str]
  app_ids: Optional[Dict[str, str]]
  processed_path: Optional[str]

  def __init__(self, schema: Optional[str]=None, table: Optional[str]=None, download_path: Optional[str]=None, app_ids: Optional[Dict[str, str]]=None, confirm_upload: Optional[bool]=None, processed_path: Optional[str]=None):
    super().__init__()
    self.schema = schema
    self.table = table
    self.confirm_upload = confirm_upload
    self.download_path = download_path
    self.app_ids = app_ids
    self.processed_path = processed_path

  def attempt(self, pilot: AppsFlyerPilot, fly: Callable[[Maneuver], Maneuver]):
    download_path = pilot.download_path if self.download_path is None else self.download_path or None
    platform_directory_map = pilot.app_ids if self.app_ids is None else self.app_ids or None
    schema = pilot.schema if self.schema is None else self.schema or None
    table = pilot.config['table'] if self.table is None else self.table or None
    confirm_upload = pilot.config['confirm_upload'] if self.confirm_upload is None else self.confirm_upload

    if download_path is not None and platform_directory_map is not None:
      processor = AppsFlyerProcessor(
        source_directory_path=Path(download_path),
        platform_directory_map=platform_directory_map
      )

      def process_data(*args):
        processor.process()
        return processor.processed_data
    else:
      process_data = None
    
    collect_maneuver = CollectReportManeuver(
      processor=process_data,
      processed_path=self.processed_path,
      schema=schema,
      table=table,
      confirm_upload=confirm_upload,
      replace=True
    )
    fly(collect_maneuver)
    report = collect_maneuver.deploy()
    self.load(report)

if __name__ == '__main__':
  enqueue_maneuver(AppsFlyerManeuver())
else:
  enqueue_maneuver(AppsFlyerCollectManeuver(
    download_path='output/appsflyer/COMPANY/DATE',
    schema='test',
    table='test_appsflyer_scraper'
  ))
