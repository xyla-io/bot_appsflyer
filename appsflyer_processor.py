import pandas as pd
import numpy as np

from datetime import date
from pathlib import Path
from typing import Optional, Dict

class AppsFlyerProcessor:
  source_directory_path: Path
  platform_directory_map: Dict[str, str]
  processed_data: Optional[pd.DataFrame]=None

  def __init__(self, source_directory_path: Path, platform_directory_map: Dict[str, str]):
    self.source_directory_path = source_directory_path
    self.platform_directory_map = platform_directory_map

  def process(self):
    processed_data = pd.DataFrame()

    for platform, app_id in self.platform_directory_map.items():
      files_path = self.source_directory_path / app_id
      for path in files_path.glob('*.csv'):
        file_name = path.absolute()

        df = pd.read_csv(file_name)
        day_list = [
          x 
          for x in df.columns 
          if x not in ('Cohort Day', 'Media Source', 'Ltv Country', 'Campaign Id', 'Users',
            'Cost', 'Average eCPI', 'Users')
        ]

        df_final = pd.DataFrame()
        for i in day_list:
          event_day = i.split(' ')[-1]
          if event_day == 'partial':
            event_day = i.split(' ')[-3]
          df_temp = df[['Cohort Day', 'Media Source', 'Ltv Country', 'Campaign Id']]

          # Ensure Campaign Id can be read as a string
          df_temp['Campaign Id'] = df_temp['Campaign Id'].astype(str)
          df_temp['Campaign Id'] = '"' + df_temp['Campaign Id'] + '"'
          
          df_temp['event_day'] = event_day
          df_temp['cohort_revenue'] = df[[i]]
          df_temp.cohort_revenue = df_temp.cohort_revenue.apply(lambda s: float(s.split('/')[0]) / float(s.split('/')[1]) if isinstance(s, str) and '/' in s else s)
          df_temp['platform'] = platform
          df_temp['install'] = df[['Users']]

          df_final = df_temp.append(df_final, sort=True)
        
        processed_data = processed_data.append(df_final, sort=True)
    
    self.processed_data = processed_data
  
  def process_old(self):
    today = date.today()
    file_name = input('Please enter file name: ')

    platform = ''
    if file_name.find('ios') != -1: platform = 'ios'
    elif file_name.find('android') != -1: platform = 'android'
    else: platform = 'error'

    df = pd.read_csv('{}.csv'.format(file_name))
    day_list = [x for x in df.columns if x not in ('Cohort Day', 'Media Source', 'Ltv Country', 'Campaign Id', 'Users',
          'Cost', 'Average eCPI','Users')]

    df_final = pd.DataFrame()
    for i in day_list:
        event_day = i.split(' ')[-1]
        df_temp = df[['Cohort Day', 'Media Source', 'Ltv Country', 'Campaign Id']]

        # Ensure Campaign Id can be read as a string
        df_temp['Campaign Id'] = df_temp['Campaign Id'].astype(str)
        df_temp['Campaign Id'] = '"' + df_temp['Campaign Id'] + '"'
        
        df_temp['event_day'] = event_day
        df_temp['cohort_revenue'] = df[[i]]
        df_temp['platform'] = platform
        df_temp['install'] = df[['Users']]

        df_final = df_temp.append(df_final, sort = True)
    df_final.to_csv('AF Total Revenue Data Lot - {}.csv'.format(today), index=False)
    print('Exported CSV')