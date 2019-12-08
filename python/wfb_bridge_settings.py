#!/usr/bin/env python3

import os
from iniparse import ConfigParser
import logging


class WFBBridgeSettings:
    config_filename = '/etc/default/wfb_bridge'

    def __init__(self):
        '''Parse and update wfb_bridge configuration settings'''

    def update(self, settings, is_ground):
        '''Perform the update of the wfb_bridge settings'''

        # Fetch the settings values from the settings file

        # Keep track of if we modified a setting
        modified = False

        # Read the current wfb_bridge settings file.
        parser = ConfigParser()
        parser.read(self.config_filename)

        # Update the options if they are different
        if is_ground:
            modified |= self.update_option(parser, 'mode', 'ground')
        else:
            modified |= self.update_option(parser, 'mode', 'air')

        # Write out the modified settings file
        if modified:
            logging.info("Writing updated configuration file to: " + self.config_filename)
            with open(self.config_filename, "w") as fp:
                parser.write(fp)

            # Force the wfb_bridge daemon to reload the configuration
            logging.info("Restarting wfb_bridge")
            os.system("systemctl restart wfb_bridge")

        return modified

    def update_option(self, parser, name, value):
        section = 'global'
        if parser.has_option(section, name):
            val = parser.get(section, name)
            if val != value:
                parser.set(section, name, value)
                logging.info("Changing " + name + " in section " + section +
                             " from " + val + " to " + value)
                return True
        return False
