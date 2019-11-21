
import time
import threading
import socket
import struct

import sdl2

class Transmitter(object):
    """Read the transmitter stick/switch postions and relay them out over UDP"""

    def __init__(self, channels=16, period=0.02, ip="127.0.0.1", port=14551):
        """Initialize the joystick class"""
        self.channels = channels
        self.done = False
        self.period = period
        self.ip = ip
        self.port = port
        self.joystick = None

        # Initialize the SDL joystick module
        sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK)

        # Create the UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Spawn a thread to read the transmitter values
        self.thread = threading.Thread(target = self.start)
        self.thread.start()

    def __del__(self):
        self.done = True
        self.thread.join()

    def read(self):
        """Read all the sticks and switches"""

        # Force an update of the joystick channels
        sdl2.SDL_PumpEvents()

        # Ensure that the Tx is connected
        if sdl2.SDL_NumJoysticks() == 0:
            if self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                self.joystick = None
            return False
        elif not self.joystick:
            # Open the first joystick if necessary
            self.joystick = sdl2.SDL_JoystickOpen(0)

        # Read all the channels
        ret = []
        for channel in range(self.channels):
            val = sdl2.SDL_JoystickGetAxis(self.joystick, channel)
            ret.append(int(((val / 65536.0) + 0.5) * 800.0 + 1100.0))

        # Return the list of values
        return ret

    def send(self, channels):
        """Send the channels using a custom UDP message"""
        msg = bytes()
        for ch in channels:
            msg = msg + struct.pack('<H', ch)
        self.sock.sendto(msg, (self.ip, self.port))

    def start(self):
        """Periodically read the transmitter and send the values over UDP"""
        while not self.done:
            channels = self.read()
            if channels:
                self.send(channels)
            time.sleep(self.period)

    def join(self):
        self.thread.join()

if __name__ == '__main__':
    trans = Transmitter()
    trans.join()
