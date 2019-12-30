#!/usr/bin/env python3

import os
import socket
import struct
import array
import time
import logging
import math
import numpy as np
import subprocess
import threading
import multiprocessing as mp
import openhd.py_v4l2 as v4l
from openhd.py_v4l2 import Frame
from openhd.py_v4l2 import Control

from openhd.format_as_table import format_as_table
from openhd import fec

def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True

# Try loading picamera module
found_picamera = module_exists("picamera")
if found_picamera:
    import picamera

class FPSLogger(object):

    def __init__(self, port):
        self.bytes = 0
        self.count = 0
        self.blocks = 0
        self.port = port
        self.prev_time = time.time()

    def log(self, frame_size, blocks = 0):
        self.bytes += frame_size
        self.blocks += blocks
        self.count += 1
        cur_time = time.time()
        dur = (cur_time - self.prev_time)
        if dur > 2.0:
            if self.blocks > 0:
                logging.debug("port: %d  fps: %f  Mbps: %6.3f  blocks: %d" %
                              (self.port, self.count / dur, 8e-6 * self.bytes / dur, self.blocks))
            else:
                logging.debug("port: %d  fps: %f  Mbps: %6.3f" %
                              (self.port, self.count / dur, 8e-6 * self.bytes / dur))
            self.prev_time = cur_time
            self.bytes = 0
            self.count = 0

class UDPOutputStream(object):

    def __init__(self, host, port, broadcast = False, maxpacket = 1400, fec_ratio=0.0):
        self.log = FPSLogger(port)
        self.broadcast = broadcast
        self.maxpacket = maxpacket
        self.host = host
        self.port = port
        if fec_ratio > 0:
            self.fec = fec.PyFECBufferEncoder(maxpacket, fec_ratio)
        else:
            self.fec = None

        # Create the communication socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if broadcast:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
    def write(self, s):
        t = time.time()
        ts = "%03d:%03d" % (int(t) % 1000, round(t * 1000) % 1000)
        #t = round(time.time() * 1000) % 1000
        self.log.log(len(s))
        if self.broadcast:
            host = '<broadcast>'
        else:
            host = self.host
        if self.fec:
            for b in self.fec.encode_buffer(s):
                self.sock.sendto(b, (host, self.port))
        else:
            np = math.ceil((len(s) + 8) / self.maxpacket)
            #s = b'FRAM' + struct.pack('HH', t, np) + s
            #with open(ts, "wb") as fp:
            #    fp.write(s)
            for i in range(0, len(s), self.maxpacket):
                self.sock.sendto(s[i : min(i + self.maxpacket, len(s))], (host, self.port))

class Camera(object):

    def __init__(self, host, port, device=False, blocksize=1400, fec_ratio=0.0):
        self.streaming = False
        self.recording = False
        self.device = device

        # Streaming - Use the maximum resolution detected
        self.width = 0
        self.height = 0
        self.bitrate = 6000000
        self.fps = 60
        self.intra_period = 3
        self.quality = 20
        self.inline_headers = True

        # Recording - Use the maximum resolution detected
        self.rec_width = 0
        self.rec_height = 0
        self.rec_bitrate = 25000000
        self.rec_intra_period = 30
        self.rec_quality = 30
        self.rec_inline_headers = True

        # Create streaming output
        self.stream = UDPOutputStream(host, port, maxpacket=blocksize, fec_ratio=fec_ratio)

    def __del__(self):
        self.stop_streaming()

    # Change the parameters for the video stream
    def streaming_params(self, width, height, bitrate, intra_period = 30, quality=20, fps = 60, inline_headers = True) :
        self.width = width
        self.height = height
        self.bitrate = bitrate
        self.intra_period = intra_period
        self.quality = quality
        self.fps = fps
        self.inline_headers = inline_headers

    # Change the parameters for the video recording
    def recording_params(self, width, height, bitrate, intra_period = 30, quality=20, fps = 60, inline_headers = True) :
        self.rec_width = width
        self.rec_height = height
        self.rec_bitrate = bitrate
        self.rec_intra_period = intra_period
        self.rec_quality = quality
        self.fps = fps
        self.rec_inline_headers = inline_headers


    def start_streaming(self, rec_filename = False):

        # Create the camera source
        if self.device == 'picam1' or self.device == 'picam2':
            if self.device == 'picam1':
                self.camera = picamera.PiCamera(camera_num=0)
            else:
                self.camera = picamera.PiCamera(camera_num=1)

            # The camera frame size has to be the larger of the streaming and recording size
            self.rec_width = max(self.width, self.rec_width)
            self.rec_height = max(self.height, self.rec_height)

            # Initilize the camera parameters
            self.camera.resolution = (self.rec_width, self.rec_height)
            self.camera.framerate = self.fps
            self.camera.awb_mode = 'sunlight'

            # Are we recording and streaming, or just streaming?
            self.streaming = True
            if rec_filename:
                self.recording = True
                self.camera.start_recording(rec_filename, format='h264', intra_period=self.rec_intra_period,
                                            inline_headers=self.rec_inline_headers, bitrate=self.rec_bitrate, quality=self.rec_quality)
                self.camera.start_recording(self.stream, format='h264', intra_period=self.intra_period,
                                            inline_headers=self.inline_headers, bitrate=self.bitrate, quality=self.quality,
                                            splitter_port=2, resize=(self.width, self.height))
            else:
                self.camera.start_recording(self.stream, format='h264', intra_period=self.intra_period,
                                            inline_headers=self.inline_headers, bitrate=self.bitrate)

            while self.streaming:
                self.wait_streaming(1)

        else:

            # We can only read one stream, so we'll use the best
            self.width = max(self.width, self.rec_width)
            self.height = max(self.height, self.rec_height)

            # Open the device
            control = Control(self.device)
            control.set_control_value(9963800, 2)
            control.close()

            # Start streaming frames
            frame = Frame(self.device, self.width, self.height)
            self.streaming = True
            while self.streaming:
                frame_data = frame.get_frame()
                self.stream.write(frame_data)

    def wait_streaming(self, time):
        if self.camera:
            self.camera.wait_recording(time)

    def stop_streaming(self):
        if found_picamera:
            if self.recording:
                self.camera.stop_recording(splitter_port=2)
            if self.streaming:
                self.camera.stop_recording()
        self.streaming = False
        self.recording = False


class CameraProcess(object):

    def __init__(self, width = 10000, height = 10000, device = False, prefer_picam = True,
                 host = "", port = 5600, bitrate = 3000000, quality = 20, inline_headers = True, \
                 fps = 30, intra_period = 5, blocksize=1400, fec_ratio=0.0):
        self.host = host
        self.port = port
        self.bitrate = bitrate
        self.quality = quality
        self.inline_headers = inline_headers
        self.intra_period = intra_period
        self.blocksize = blocksize
        self.fec_ratio = fec_ratio
        self.width = width
        self.height = height
        self.device = device
        self.fps = fps
        self.prefer_picam = prefer_picam

    def start(self):
        self.proc = mp.Process(target=self.run)
        self.proc.start()
        return True;

    def run(self):
        if self.host != "":
            host_port = self.host + ":" + str(self.port)
        else:
            host_port = str(self.port)

        # Find the camera that best fits the user specified parameters
        modes = detect_cameras(self.device)
        if not modes:
            logging.error("No camera matching the specified parameters were detected")
            return
        found = False
        for mode in modes:
            logging.debug(format_as_table(mode, mode[0].keys(), mode[0].keys(), 'device', add_newline=True))
            cur_mode = best_camera(mode, self.width, self. height, self.prefer_picam, self.fps, self.device)
            if cur_mode != False:
                self.width = cur_mode['width']
                self.height = cur_mode['height']
                self.device = cur_mode['device']
                self.type = cur_mode['type']
                self.fps = min(self.fps, cur_mode['fps'])
                found = True
                break
        if not found:
            logging.error("No camera matching the specified parameters were detected")
            return
        logging.info("Streaming %dx%d/%d video to %s at %f Mbps from %s" % \
                     (self.width, self.height, self.fps, host_port, self.bitrate, self.device))

        self.camera = Camera(self.host, self.port, self.device, blocksize=self.blocksize, fec_ratio=self.fec_ratio)
        self.camera.streaming_params(self.width, self.height, self.bitrate, self.intra_period, self.quality,
                                     self.fps, self.inline_headers)

        # Start streaming
        self.camera.start_streaming()

    def join(self):
        if self.proc:
            self.proc.join()


def detect_cameras(device = False):
    '''
    Detect all available cameras and modes, and return a list containing:
       type, device, width, height
    '''

    # Create a list of all available camera modes detected
    cam_modes = []

    # Try to find an H264 capable device
    picam_device = 'picam1'
    for d in v4l.get_devices():
        cur_modes = []
        logging.debug("Device: " + d)

        # Try to create the control interface
        try:
            control = Control(d)
        except Exception as e:
            continue

        # Get the capabilities of this camera
        caps = control.get_capabilities()
        if len(caps):
            logging.debug("  driver:       " + caps['driver'])
            logging.debug("  card:         " + caps['card'])
            logging.debug("  bus_info:     " + caps['bus_info'])
            logging.debug("  version:      " + str(caps['version']))
            logging.debug("  capabilities: " + str(caps['capabilities']))
            logging.debug("  device_caps:  " + str(caps['device_caps']) + "\n")
        
        # Try to read all the controls for this camera
        controls = control.get_controls()
        if len(controls):
            logging.debug(format_as_table(controls, controls[0].keys(), controls[0].keys(), 'name', add_newline=True))

        # Read all the formats supported by this camera
        formats = control.get_formats()
        if len(formats):
            logging.debug(format_as_table(formats, formats[0].keys(), formats[0].keys(), 'format', add_newline=True))

        # Try to detect Raspberry Pi cameras
        picam = False
        if 'mmal' in caps['driver']:
            for format in formats:
                if format['format'] == 'H264' and format['type'] == 'stepwise':
                    if format['max_width'] == 2592:
                        picam = 'ov5647'
                        break
                    elif format['max_width'] == 3280:
                        picam = 'imx219'
                        break

        # Fill in the standard camera modes for Rapberry Pi cameras
        if picam:
            type = picam

            # V1 camera
            if type == 'ov5647':
                cur_modes.append({ 'type': 'picam' + '_' + type,
                                   'device': picam_device,
                                   'width': 1920,
                                   'height': 1080,
                                   'fps': 30 })
                cur_modes.append({ 'type': 'picam' + '_' + type,
                                   'device': picam_device,
                                   'width': 1296,
                                   'height': 972,
                                   'fps': 42 })
                cur_modes.append({ 'type': 'picam' + '_' + type,
                                   'device': picam_device,
                                   'width': 1296,
                                   'height': 730,
                                   'fps': 49 })
                cur_modes.append({ 'type': 'picam' + '_' + type,
                                   'device': picam_device,
                                   'width': 640,
                                   'height': 480,
                                   'fps': 90 })

            # V2 camera
            if type == 'imx219':
                cur_modes.append({ 'type': 'picam' + '_' + type,
                                   'device': picam_device,
                                   'width': 1920,
                                   'height': 1080,
                                   'fps': 30 })
                cur_modes.append({ 'type': 'picam' + '_' + type,
                                   'device': picam_device,
                                   'width': 1640,
                                   'height': 1232,
                                   'fps': 40 })
                cur_modes.append({ 'type': 'picam' + '_' + type,
                                   'device': picam_device,
                                   'width': 1640,
                                   'height': 922,
                                   'fps': 40 })
                cur_modes.append({ 'type': 'picam' + '_' + type,
                                   'device': picam_device,
                                   'width': 1280,
                                   'height': 720,
                                   'fps': 90 })
                cur_modes.append({ 'type': 'picam' + '_' + type,
                                   'device': picam_device,
                                   'width': 640,
                                   'height': 480,
                                   'fps': 200 })


            # Is this the device the user is looking for?
            if (device != False) and (device != picam_device):
                picam_device = 'picam2'
                continue

            picam_device = 'picam2'

        else:

            # Is this the device the user is looking for?
            if (device != False) and (device != d):
                continue

            for format in formats:
                if format["format"] == "H264":
                    cur_modes.append({ 'type': 'v4l2',
                                       'device': d,
                                       'width': format["width"],
                                       'height': format["height"],
                                       'fps': 30 })

        if len(cur_modes) > 0:
            for mode in cur_modes:
                logging.debug("Found camera: %s %s %dx%d" %
                              (mode['device'], mode['type'], mode['width'], mode['height']))
            cam_modes.append(cur_modes)

        control.close()

    logging.info("Detected %d cameras:" % (len(cam_modes)))
    for modes in cam_modes:
        if len(modes) > 0:
            logging.info("  %s:" % (modes[0]['device']))
        for mode in modes:
            logging.info("    %s: %s %dx%d" %
                         (mode['device'], mode['type'], mode['width'], mode['height']))

    return cam_modes


def best_camera(modes, width = 10000, height = 10000, fps = 60, prefer_picam=True, device=None):
    '''Find the camera mode that best fits the specified parameters'''

    # Find the device/mode that is closest to the users selection
    found_picam = False
    closest = None
    closest_dist = 1e100
    for m in modes:
        if prefer_picam and found_picam and m['type'] != 'picam':
            break
        dw = math.fabs(m['width'] - width)
        dh = math.fabs(m['height'] - height)
        dist = math.sqrt(dw * dw + dh + dh)
        if dist < closest_dist:
            closest = m
            closest_dist = dist
        if m['type'] == 'picam':
            found_picam = True

    # Did we dectect any cameras?
    if not closest:
        logging.error("No cameras were detected")
        return False

    return closest

def start_cam1():
    #cam1 = Camera("192.168.1.182", 5600, 'picam1')
    cam1 = Camera("127.0.0.1", 5600, 'picam1')
    cam1.streaming_params(1296, 972, 6000000, intra_period = 30, quality=20, fps = 30, inline_headers = True)
    cam1.start_streaming()
    cam1.wait_streaming(1)

def start_cam2():
    #cam2 = Camera("192.168.1.182", 5601, 'picam2')
    cam2 = Camera("127.0.0.1", 5601, 'picam2')
    cam2.streaming_params(1296, 972, 6000000, intra_period = 30, quality=20, fps = 30, inline_headers = True)
    cam2.start_streaming()
    cam2.wait_streaming(1)

if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    detect_cameras()
    th1 = threading.Thread(target = start_cam1)
    th1.start()
    time.sleep(1)
    th2 = threading.Thread(target = start_cam2)
    th2.start()
    th1.join()
    th2.join()
