#!/usr/bin/env python3

import os
from iniparse import ConfigParser
import logging


class WifiSettings:
    config_filename = '/etc/default/wifi_config'

    def __init__(self):
        '''Parse and update wifi configuration settings'''

    def update(self, settings, is_ground):
        '''Perform the update of the wifi settings'''

        # Fetch the settings values from the settings file
        freq = settings.getint('FREQ')
        datarate = settings.getint('DATARATE')
        if is_ground:
            tx_power = settings.getint('TxPowerGround')
        else:
            tx_power = settings.getint('TxPowerAir')

        # Keep track of if we modified a setting
        modified = False

        # Read the current wifi settings file.
        parser = ConfigParser()
        parser.read(self.config_filename)

        # Loop through each section modifying the frequency and/or power
        for sec in parser.sections() + ['DEFAULT']:
            if parser.has_option(sec, 'frequency'):
                sec_freq = int(parser.get(sec, 'frequency'))
                if sec_freq != freq:
                    parser.set(sec, 'frequency', freq)
                    logging.info("Changing frequecy in section " + sec +
                                 " from " + str(sec_freq) + " to " + str(freq))
                    modified = True
            if parser.has_option(sec, 'txpower'):
                sec_tx_power = int(parser.get(sec, 'txpower'))
                if sec_tx_power != tx_power:
                    parser.set(sec, 'txpower', tx_power)
                    logging.info("Changing TX power in section " + sec +
                                 " from " + str(sec_tx_power) + " to " + str(tx_power))
                    modified = True

        # Write out the modified settings file
        if modified:
            logging.info("Writing updated configuration file to: " + self.config_filename)
            with open(self.config_filename, "w") as fp:
                parser.write(fp)

            # Force the wifi_config daemon to reload the configuration
            logging.info("Forcing reload on wifi_config")
            os.system("systemctl reload wifi_config")
