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
        use_mcs = settings.getynd('UseMCS')
        use_stbc = settings.getynd('UseSTBC')
        use_ldpc = settings.get('UseLDPC')
        video_udp_host = settings.get('VIDEO_UDP_HOST')
        video_udp_port = settings.get('VIDEO_UDP_PORT')
        video_blocks = settings.get('VIDEO_BLOCKS')
        video_fecs = settings.get('VIDEO_FECS')
        video_blocklength = settings.get('VIDEO_BLOCKLENGTH')
        video_blocks_secondary = settings.get('VIDEO_BLOCKS_SECONDARY')
        video_fecs_secondary = settings.get('VIDEO_FECS_SECONDARY')
        video_blocklength_secondary = video_blocklength
        video_udp_host_secondary = settings.get('VIDEO_UDP_HOST2')
        video_udp_port_secondary = settings.get('VIDEO_UDP_PORT2')
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
            modified |= settings.update_option(parser, 'global', 'mode', 'ground')
        else:
            modified |= settings.update_option(parser, 'global', 'mode', 'air')
        modified |= settings.update_option(parser, 'video', 'outhost', video_udp_host)
        modified |= settings.update_option(parser, 'video', 'outport', video_udp_port)
        modified |= settings.update_option(parser, 'video', 'blocks', video_blocks)
        modified |= settings.update_option(parser, 'video', 'fec', video_fecs)
        modified |= settings.update_option(parser, 'video', 'blocksize', video_blocklength)
        modified |= settings.update_option(parser, 'video2', 'outhost', video_udp_host_secondary)
        modified |= settings.update_option(parser, 'video2', 'outport', video_udp_port_secondary)
        modified |= settings.update_option(parser, 'video2', 'blocks', video_blocks_secondary)
        modified |= settings.update_option(parser, 'video2', 'fec', video_fecs_secondary)
        modified |= settings.update_option(parser, 'video2', 'blocksize', video_blocklength)
        modified |= settings.update_option(parser, 'telemetry', 'outhost', telemetry_udp_host)
        modified |= settings.update_option(parser, 'telemetry', 'outport', telemetry_udp_port)
        modified |= settings.update_option(parser, 'packed_status_down', 'outhost', link_status_udp_host)
        modified |= settings.update_option(parser, 'packed_status_down', 'outport', link_status_udp_port)
        modified |= settings.update_option(parser, 'rc', 'inport', telemetry_up_udp_port)

        # The datarate should only apply to the video link
        datarate -= 1
        modified != settings.update_option(parser, 'video', 'datarate', str(datarate))

        # Loop through each section modifying the wifi parameters
        for sec in parser.sections():
            modified |= settings.update_option(parser, sec, 'mcs', str(use_mcs))
            modified |= settings.update_option(parser, sec, 'stbc', str(use_stbc))
            modified |= settings.update_option(parser, sec, 'ldpc', str(use_ldpc))

        # Write out the modified settings file
        if modified:
            logging.info("Writing updated configuration file to: " + self.config_filename)
            with open(self.config_filename, "w") as fp:
                parser.write(fp)

            # Force the wfb_bridge daemon to reload the configuration
            logging.info("Restarting wfb_bridge")
            os.system("systemctl restart wfb_bridge")

        return modified
