#!/usr/bin/env python3

import socket
import struct
import array
import time
import logging
import math
import numpy as np
import subprocess
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

    def __init__(self):
        self.bytes = 0
        self.count = 0
        self.blocks = 0
        self.prev_time = time.time()

    def log(self, frame_size, blocks = 0):
        self.bytes += frame_size
        self.blocks += blocks
        self.count += 1
        cur_time = time.time()
        dur = (cur_time - self.prev_time)
        if dur > 2.0:
            if self.blocks > 0:
                logging.debug("fps: %f  Mbps: %6.3f  blocks: %d" %
                              (self.count / dur, 8e-6 * self.bytes / dur, self.blocks))
            else:
                logging.debug("fps: %f  Mbps: %6.3f" % (self.count / dur, 8e-6 * self.bytes / dur))
            self.prev_time = cur_time
            self.bytes = 0
            self.count = 0

class UDPOutputStream(object):

    def __init__(self, host, port, broadcast = False, maxpacket = 1400, fec_ratio=0.0):
        self.log = FPSLogger()
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
        self.log.log(len(s))
        if self.broadcast:
            host = '<broadcast>'
        else:
            host = self.host
        if self.fec:
            for b in self.fec.encode_buffer(s):
                self.sock.sendto(b, (host, self.port))
        else:
            for i in range(0, len(s), self.maxpacket):
                self.sock.sendto(s[i : min(i + self.maxpacket, len(s))], (host, self.port))

class Camera(object):

    def __init__(self, host, port, device=False, fec_ratio=0.0):
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
        self.stream = UDPOutputStream(host, port, fec_ratio=fec_ratio)

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


    def start_streaming(self, rec_filename = False, sock = None):

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
                 fps = 30, intra_period = 5, fec_ratio=0.0):
        self.host = host
        self.port = port
        self.bitrate = bitrate
        self.quality = quality
        self.inline_headers = inline_headers
        self.intra_period = intra_period
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
        logging.debug(format_as_table(modes, modes[0].keys(), modes[0].keys(), 'device', add_newline=True))
        mode = best_camera(modes, self.width, self. height, self.prefer_picam, self.fps, self.device)
        if not mode:
            logging.error("No camera matching the specified parameters were detected")
            return
        self.width = mode['width']
        self.height = mode['height']
        self.device = mode['device']
        self.type = mode['type']
        self.fps = min(self.fps, mode['fps'])

        logging.info("Streaming %dx%d/%d video to %s at %f Mbps from %s" % \
                     (self.width, self.height, self.fps, host_port, self.bitrate, self.device))

        self.camera = Camera(self.host, self.port, self.device, fec_ratio=self.fec_ratio)
        self.camera.streaming_params(self.width, self.height, self.bitrate, self.intra_period, self.quality,
                                     self.fps, self.inline_headers)

        # Start streaming
        self.camera.start_streaming()

    def join(self):
        if self.proc:
            self.proc.join()


def detect_cameras(device = None):
    '''
    Detect all available cameras and modes, and return a list containing:
       type, device, width, height
    '''

    # Create a list of all available camera modes detected
    cam_modes = []

    # Try to detect Raspberry Pi cameras
    if found_picamera:
        picam_types = []

        # Try to detect the first pi camera
        try:
            cam = picamera.PiCamera(camera_num=0)
            type = cam.revision
            logging.info("Found Raspberry Pi camera 1 " + type)
            picam_types.append(type)
            cam.close()
        except:
            pass

        # Try to detect the second pi camera
        try:
            cam = picamera.PiCamera(camera_num=1)
            type = cam.revision
            logging.info("Find Raspberry Pi camera 2 " + type)
            picam_types.append(type)
            cam.close()
        except:
            pass

        # Fill in the standard pi camera modes
        for idx, type in enumerate(picam_types):
            if idx == 0:
                device = 'picam1'
            else:
                device = 'picam2'

            # V1 camera
            if type == 'ov5647':
                cam_modes.append({ 'type': 'picam',
                                     'device': device,
                                     'width': 1920,
                                     'height': 1080,
                                     'fps': 30 })
                cam_modes.append({ 'type': 'picam',
                                     'device': device,
                                     'width': 1296,
                                     'height': 972,
                                     'fps': 42 })
                cam_modes.append({ 'type': 'picam',
                                     'device': device,
                                     'width': 1296,
                                     'height': 730,
                                     'fps': 49 })
                cam_modes.append({ 'type': 'picam',
                                     'device': device,
                                     'width': 640,
                                     'height': 480,
                                     'fps': 90 })

            # V2 camera
            if type == 'imx219':
                cam_modes.append({ 'type': 'picam',
                                     'device': device,
                                     'width': 1920,
                                     'height': 1080,
                                     'fps': 30 })
                cam_modes.append({ 'type': 'picam',
                                     'device': device,
                                     'width': 1640,
                                     'height': 1232,
                                     'fps': 40 })
                cam_modes.append({ 'type': 'picam',
                                     'device': device,
                                     'width': 1640,
                                     'height': 922,
                                     'fps': 40 })
                cam_modes.append({ 'type': 'picam',
                                     'device': device,
                                     'width': 1280,
                                     'height': 720,
                                     'fps': 90 })
                cam_modes.append({ 'type': 'picam',
                                     'device': device,
                                     'width': 640,
                                     'height': 480,
                                     'fps': 200 })

    # Try to find an H264 capable device
    for d in v4l.get_devices():
        if device and d != device:
            continue
        try:
            control = Control(d)
            controls = control.get_controls()
            logging.debug(format_as_table(controls, controls[0].keys(), controls[0].keys(), 'name', add_newline=True))
            formats = control.get_formats()
            logging.debug(format_as_table(formats, formats[0].keys(), formats[0].keys(), 'format', add_newline=True))
            for format in formats:
                if format["format"] == "H264":
                    cam_modes.append({ 'type': 'v4l2',
                                       'device': d,
                                       'width': format["width"],
                                       'height': format["height"],
                                       'fps': 30 })
                    logging.info("Found V4L2: " + d + " " + str(format["width"]) + "x" +  str(format["height"]))
        except Exception as e:
            continue

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

if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    cam = CameraProcess(host="192.168.1.38", port=5600)
    # cam = CameraProcess()
    # cam = CameraProcess(host="127.0.0.1", port=5700, width=2560, height=1280, fec_ratio=0.5)
    # cam = CameraProcess(host="127.0.0.1", port=5700, fec_ratio=0.5)
    #cam = CameraProcess()
    if cam.start():
        cam.join()
    else:
        logging.error("Error starting camera process")
