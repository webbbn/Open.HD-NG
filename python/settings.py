#!/usr/bin/env python3

import os
from io import StringIO
import logging
from configparser import ConfigParser
from openhd.wifi_settings import WifiSettings
from openhd.openhd_settings import OpenHDSettings
from openhd.wfb_bridge_settings import WFBBridgeSettings

class Settings:
    '''Read and OpenHD paraemter file and support reading the name/value pairs'''

    def __init__(self, filename):

        # Read the settings file.
        with open(filename, 'r') as fp:
            settings = fp.read()

        # Add a ini file section header so we can parse it as a config file.
        settings = "[settings]\n" + settings

        # Parse as a config file.
        self.parser = ConfigParser()
        self.parser.read_string(settings)

    def get(self, name):
        '''Get a value by name'''
        try:
            return self.parser.get('settings', name)
        except:
            return None

    def getbool(self, name):
        '''Get the value of a boolean setting, which should be one of 0,no,false,1,yes,true'''
        try:
            return self.parser.getboolean('settings', name)
        except:
            return None

    def getint(self, name):
        '''Get the value of an integer setting'''
        try:
            return self.parser.getint('settings', name)
        except:
            return None

    def getfloat(self, name):
        '''Get the value of a floating point setting'''
        try:
            return self.parser.getfloat('settings', name)
        except:
            return None

    def getyn(self, name):
        '''Get the value of a yes/no boolean setting, which should be either Y, or N'''
        try:
            val = self.get(name)
        except:
            return False
        if val.lower()[0] == 'y':
            return True
        else:
            return False

    def update(self, is_ground):
        '''Update all the component settings files and restart the components if necessary'''

        # Ensure we're running with root permissions
        if os.getuid() != 0:
            logging.info("Must be run with root privileges")
            return

        # Update the settings for each of the components
        openhd_settings = OpenHDSettings()
        openhd_settings.update(self, is_ground)
        wifi_settings = WifiSettings()
        wifi_settings.update(self, is_ground)
        wfb_bridge_settings = WFBBridgeSettings()
        wfb_bridge_settings.update(self, is_ground)
