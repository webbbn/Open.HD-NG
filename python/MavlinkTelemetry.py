#!/usr/bin/env python3

import queue
import threading
import socket
import pymavlink.mavutil as mavutil
from pymavlink.dialects.v10 import ardupilotmega as mavlink2

class MavlinkTelemetry(object):
    """
    Receive telemetry over a standard UART connection
    and relayit out over UDP
    """

    def __init__(self, uart = "/dev/ttyS0", baudrate = 57600,
                 host = "127.0.0.1", port = 14550,
                 rc_host = None, rc_port = 14551, min_packet=128):
        print(uart, baudrate)
        self.queue = queue.Queue()
        self.uart = uart
        self.baudrate = baudrate
        self.done = False
        self.host = host
        self.port = port
        self.rc_host = rc_host
        self.rc_port = rc_port
        self.rc_chan = None
        self.min_packet = min_packet
        self.mavs = mavutil.mavlink_connection(uart, baud=baudrate)

        # Create the RC receive thread
        if rc_host:
            self.recv_thread = threading.Thread(target = self.recv_rc)
        else:
            self.recv_thread = None

        # Start the processing threads
        self.thread = threading.Thread(target = self.start)
        self.send_thread = threading.Thread(target = self.start_send)
        self.thread.start()
        self.send_thread.start()

    def __del__(self):
        self.done = True
        self.join()

    def join(self):
        self.thread.join()
        if self.send_thread:
            self.send_thread.start()

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

    def start(self):
        while not self.done:
            msg = self.mavs.recv_msg()
            if msg:
                self.queue.put(msg)

    def start_send(self):
        obuf = bytearray()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while not self.done:
            msg = self.queue.get()
            buf = msg.get_msgbuf()
            obuf += buf
            if len(obuf) > self.min_packet:
                sock.sendto(obuf, (self.host, self.port))
                obuf = bytearray()

if __name__ == '__main__':
    # /dev/ttyS0 pi, /dev/ttyS1 nanopi
    telem = MavlinkTelemetry(uart='/dev/ttyS1', baudrate=57600)
    telem.join()
