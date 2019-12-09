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
        use_mcs = settings.getyn('UseMCS')
        use_stbc = settings.getyn('UseSTBC')
        use_ldpc = settings.getyn('UseLDPC')
        video_udp_host = settings.get('VIDEO_UDP_HOST')
        video_udp_port = settings.get('VIDEO_UDP_PORT')
        telemetry_udp_host = settings.get('TELEMETRY_UDP_HOST')
        telemetry_udp_port = settings.get('TELEMETRY_UDP_PORT')
        link_status_udp_host = settings.get('LINK_STATUS_UDP_HOST')
        link_status_udp_port = settings.get('LINK_STATUS_UDP_PORT')
        telemetry_up_udp_port = settings.get('TELEMETRY_UP_UDP_PORT')
        datarate = settings.getint("DATARATE")

        # Keep track of if we modified a setting
        modified = False

        # Read the current wfb_bridge settings file.
        parser = ConfigParser()
        parser.read(self.config_filename)

        # Update the options if they are different
        if is_ground:
            modified |= self.update_option(parser, 'global', 'mode', 'ground')
        else:
            modified |= self.update_option(parser, 'global', 'mode', 'air')
        modified |= self.update_option(parser, 'video', 'outhost', video_udp_host)
        modified |= self.update_option(parser, 'video', 'outport', video_udp_port)
        modified |= self.update_option(parser, 'telemetry', 'outhost', telemetry_udp_host)
        modified |= self.update_option(parser, 'telemetry', 'outport', telemetry_udp_port)
        modified |= self.update_option(parser, 'packed_status_down', 'outhost', link_status_udp_host)
        modified |= self.update_option(parser, 'packed_status_down', 'outport', link_status_udp_port)
        modified |= self.update_option(parser, 'rc', 'inport', telemetry_up_udp_port)

        # The datarate should only apply to the video link
        if use_mcs:
            if datarate <= 2:
                datarate -= 1
            else:
                datarate -= 2
        else:
            datarate += 2
        modified != self.update_option(parser, 'video', 'datarate', str(datarate))

        # Loop through each section modifying the wifi parameters
        for sec in parser.sections():
            modified |= self.update_option(parser, sec, 'mcs', '1' if use_mcs else '0')
            modified |= self.update_option(parser, sec, 'stbc', '1' if use_stbc else '0')
            modified |= self.update_option(parser, sec, 'ldpc', '1' if use_ldpc else '0')

        # Write out the modified settings file
        if modified:
            logging.info("Writing updated configuration file to: " + self.config_filename)
            with open(self.config_filename, "w") as fp:
                parser.write(fp)

            # Force the wfb_bridge daemon to reload the configuration
            logging.info("Restarting wfb_bridge")
            os.system("systemctl restart wfb_bridge")

        return modified

    def update_option(self, parser, section, name, value):
        if parser.has_option(section, name):
            val = parser.get(section, name)
            if val != value:
                parser.set(section, name, value)
                logging.info("Changing " + name + " in section " + section +
                             " from " + val + " to " + value)
                return True
        return False
