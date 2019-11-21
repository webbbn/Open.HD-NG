#!/usr/bin/env python3

import math
import time
import queue
import threading
import socket
import struct
import pymavlink.mavutil as mavutil
from pymavlink.dialects.v10 import ardupilotmega as mavlink2
from openhd.MultiWii import MultiWii
from openhd.MavlinkTelemetry import MavlinkTelemetry

class Telemetry(object):
    '''Process (send/receive/relay) telemetry of various types'''

    def __init__(self, protocol='mavlink', uart = "/dev/ttyS0", baudrate = 57600,
                 host = "127.0.0.1", port = 14550,
                 rc_host = None, rc_port = 14551):
        self.uart = uart
        self.baudrate = baudrate
        self.done = False
        self.rc_host = rc_host
        self.rc_port = rc_port
        self.rc_chan = None
        self.mavlink = None
        self.thread = None

        if protocol == "msp":

            # Create the MSP interface to the flight controller.
            self.mw = MultiWii()
            self.mw.connect(uart, baudrate)

            # Create the mavlink UDP output port
            self.mavdown = mavutil.mavlink_connection('udpout:127.0.0.1:14550')

            # Create the procesing thread
            self.thread = threading.Thread(target = self.start_msp)

        elif protocol == "mavlink":

            # Create the mavlink telemetry class
            self.mavlink = MavlinkTelemetry(uart=uart, baudrate=baudrate, host=host, port=port,
                                            rc_host=rc_host, rc_port=rc_port)

        else:
            raise Exception("Unsupported telemetry format: " + protocol)

        # Create the RC receive thread
        if rc_host:
            self.recv_thread = threading.Thread(target = self.recv_rc)
        else:
            self.recv_thread = None

        # Start the processing threads
        if self.thread:
            self.thread.start()
        if self.recv_thread:
            self.recv_thread.start()

    def __del__(self):
        self.done = True
        self.join()

    def join(self):
        if self.thread:
            self.thread.join()
        if self.recv_thread:
            self.recv_thread.start()
        if self.mavlink:
            self.mavlink.join()

    def start_msp(self):

        counter = 0
        while not self.done:

            # High frequency messages
            if counter % 10:
                att = self.mw.getAttitude()
                misc = self.mw.getMisc()

                # Send the attitude message
                roll = float(att["angx"]) * math.pi / 180.0
                pitch = float(att["angy"]) * math.pi / 180.0
                yaw = float(att["heading"]) * math.pi / 18.0
                rollspeed = 0; # rad/s
                pitchspeed = 0; # rad/s
                yawspeed = 0; # rad/s
                self.mavdown.mav.attitude_send(0, roll, pitch, yaw, rollspeed, pitchspeed, yawspeed)
            
            # Low frequency messages
            if counter % 100:

                # Send a heartbeat message
                self.mavdown.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER,
                                                mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)

            # Update the RC channels if available
            if self.rc_chan:
                self.mw.setRC(self.rc_chan)
                self.rc_chan = None

            # Loop with a period of 10ms
            counter += 1
            time.sleep(0.01)

    def recv_rc(self):

        # Create the receive socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Find to the receive port
        sock.bind((self.rc_host, self.rc_port))

        # Receive RC messages off the UDP port
        while True:

            # Receive the next RC message
            data, addr = sock.recvfrom(1024)

            # Unpack the channels
            self.rc_chan = struct.unpack("<HHHHHHHHHHHHHHHH", data)

class UDPTelemetryRx(object):
    """Receive telemetry over a standard UDP port"""

    def __init__(self, queue, host, port):
        self.queue = queue
        self.host = host
        self.port = port
        self.done = False
        self.mavs = mavutil.mavlink_connection(host + ":" + str(port), write=False, input=True)
        self.thread = threading.Thread(target = self.start)
        self.thread.start()

    def __del__(self):
        self.done = True
        self.thread.join()

    def start(self):
        while not self.done:
            msg = self.mavs.recv_msg()
            if msg:
                self.queue.put(msg)

class UDPTelemetryTx(object):
    """Send telemetry over a UDP socket"""

    def __init__(self, queue, host, port, broadcast=False):
        self.queue = queue
        self.host = host
        self.port = port
        self.done = False
        self.mavs = mavutil.mavlink_connection(host + ":" + str(port), write=True, input=False)
        self.thread = threading.Thread(target = self.start)
        self.thread.start()

    def __del__(self):
        self.done = True
        self.thread.join()

    def start(self):
        while not self.done:
            msg = self.queue.get()
            self.mavs.write(msg.get_msgbuf())

class SerialTelemetryTx(object):
    """Send telemetry over a standard UART connection"""

    def __init__(self, queue, uart = "/dev/ttyS1", baudrate = 57600):
        self.queue = queue
        self.uart = uart
        self.baudrate = baudrate
        self.done = False
        self.mavs = mavutil.mavlink_connection(uart, baud=baudrate)
        self.thread = threading.Thread(target = self.start)
        self.thread.start()

    def __del__(self):
        self.done = True
        self.thread.join()

    def start(self):
        while not self.done:
            msg = self.mavs.recv_msg()
            if msg:
                self.queue.put(msg)

class UDPStatusRx(object):
    """Receive link status messages over UDP"""

    def __init__(self, host, port):
        self.max_packet = 1500

        # Create the receive socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))

        # Start the receive thread
        self.done = False
        self.thread = threading.Thread(target = self.start)
        self.thread.start()

    def __del__(self):
        self.done = True
        self.thread.join()

    def start(self):
        while not self.done:
            data, addr = self.sock.recvfrom(self.max_packet)
            status = str(data.decode('utf-8')).split(',')

    def join(self):
        self.thread.join()

if __name__ == '__main__':
    # /dev/ttyS0 pi, /dev/ttyS1 nanopi
    telem = Telemetry(uart='/dev/ttyS1')
    telem.join()
