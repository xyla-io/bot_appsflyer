import os

from pathlib import Path
from raspador import Raspador, ScriptManeuver
from typing import Dict
from .appsflyer_pilot import AppsFlyerPilot

class AppsFlyerBot(Raspador):
  def scrape(self):
    maneuver = ScriptManeuver(script_path=str(Path(__file__).parent / 'appsflyer_maneuver.py'))
    pilot = AppsFlyerPilot(config=self.configuration, browser=self.browser, user=self.user)
    self.fly(pilot=pilot, maneuver=maneuver)

    super().scrape()