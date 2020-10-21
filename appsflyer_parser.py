import re
import pandas as pd

from raspador import OrdnanceParser, XPath
from typing import List

class GroupByDropdownsParser(OrdnanceParser[List[any]]):
  def parse(self):
    children = self.soup.find('div', {'class': 'cohort-grouping'}).findChildren('div', {'class': 'af-tag-input'})
    self.ordnance = children
    return self

class ReportCalendarsParser(OrdnanceParser[List[any]]):
  def parse(self):
    calendars = self.soup.find_all('div', {'class': 'rdr-Calendar'})
    self.ordnance = calendars
    return self

class DownloadButtonParser(OrdnanceParser[any]):
  def parse(self):
    button = self.soup.find('button', {'aria-label': 'Export CSV'})
    self.ordnance = button
    return self