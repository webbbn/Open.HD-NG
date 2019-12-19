#!/usr/bin/env python3

import os
from iniparse import ConfigParser
import logging


class OpenHDSettings:
    config_filename = '/etc/default/openhd'

    def __init__(self):
        '''Parse and update openhd configuration settings'''

    def update(self, settings, is_ground):
        '''Perform the update of the openhd settings'''

        # Fetch the settings values from the settings file
        if is_ground:
            if settings.getyn('ENABLE_SERIAL_TELEMETRY_OUTPUT'):
                uart = settings.get('TELEMETRY_OUTPUT_SERIALPORT_GROUND')
                baudrate = settings.get('TELEMETRY_OUTPUT_SERIALPORT_GROUND_BAUDRATE')
            else:
                uart = None
                baudrate = None
        else:
            uart = settings.get('FC_TELEMETRY_SERIALPORT')
            baudrate = settings.get('FC_TELEMETRY_BAUDRATE')
        video_width = settings.getint('WIDTH')
        video_height = settings.getint('HEIGHT')
        secondary_camera = settings.getyn('SecondaryCamera')
        video_port_secondary = settings.getint('VIDEO_UDP_PORT2')
        fps = settings.get('FPS')

        # Keep track of if we modified a setting
        modified = False

        # Read the current openhd settings file.
        parser = ConfigParser()
        parser.read(self.config_filename)

        # Update the options if they are different
        if uart and baudrate:
            modified |= self.update_option(parser, 'telemetry_uart', uart)
            modified |= self.update_option(parser, 'telemetry_baudrate', baudrate)
        modified |= self.update_option(parser, 'video_width', video_width)
        modified |= self.update_option(parser, 'video_height', video_height)
        modified |= self.update_option(parser, 'secondary_camera', secondary_camera)
        modified |= self.update_option(parser, 'video_port_secondary', video_port_secondary)

        # Write out the modified settings file
        if modified:
            logging.info("Writing updated configuration file to: " + self.config_filename)
            with open(self.config_filename, "w") as fp:
                parser.write(fp)

        return modified

    def update_option(self, parser, name, value):
        section = 'global'
        if parser.has_option(section, name):
            val = parser.get(section, name)
            # The settings might be different types (string, integer, bool, etc)
            # But they all get converted into strings when they get saved, so
            # It seems best to compare the string representations to detect change.
            if str(val) != str(value):
                parser.set(section, name, value)
                logging.info("Changing " + name + " in section " + section +
                             " from " + val + " to " + str(value))
                return True
        return False
