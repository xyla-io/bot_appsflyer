import pandas as pd

from raspador import OrdnancePilot, UserInteractor, BrowserInteractor
from typing import Dict, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta

class AppsFlyerPilot(OrdnancePilot[pd.DataFrame]):
  config: Dict[str, any]
  sign_in_wait = 3.0
  _download_path: Optional[Path]

  def __init__(self, config: Dict[str, any], user: UserInteractor, browser: BrowserInteractor):
    self.config = config
    self._download_path = None
    super().__init__(user=user, browser=browser)
  
  @property
  def email(self) -> str:
    return self.config['email']

  @property
  def password(self) -> str:
    return self.config['password']

  @property
  def schema(self) -> str:
    return self.config['schema']
  
  @property
  def company_name(self) -> str:
    return self.config['company_name']
  
  @property
  def app_ids(self) -> Dict[str, str]:
    return self.config['app_ids']
  
  @property
  def report_groupings(self) -> List[str]:
    return self.config['report_groupings']
  
  @property
  def report_start_date(self) -> datetime:
    return datetime.strptime(self.config['report_start_date'], '%Y-%m-%d')
  
  def report_date_groupings(self, end_date: datetime) -> List[Tuple]:
    report_date_groupings = [
      (self.report_start_date, min(self.report_start_date + timedelta(days=32), end_date))
    ]
    current = report_date_groupings[0][1] + timedelta(days=1)
    while current <= end_date:
      grouping = (current, min(current + timedelta(days=32), end_date))
      report_date_groupings.append(grouping)
      current = grouping[1] + timedelta(days=1)
    
    return report_date_groupings

  @property
  def download_path(self) -> Path:
    if self._download_path:
      return self._download_path

    user_directory_path = Path(f'output/appsflyer/{self.schema}')
    if not user_directory_path.exists():
      user_directory_path.mkdir()
  
    download_path = user_directory_path / self.user.date_file_name()
    download_path.mkdir()
    self._download_path = download_path
    return download_path