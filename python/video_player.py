#!/usr/bin/env python3

import os
import threading
import subprocess as sp

class VideoPlayer(object):
    '''Constrols the ground-side video player / OSD'''

    def __init__(self):
        self.done = False;
        self.video_thread = threading.Thread(target = self.start_video)
        self.video_thread.start()
        self.osd_thread = threading.Thread(target = self.start_osd)
        self.osd_thread.start()

    def __del__(self):
        self.done = True
        self.join()

    def join(self):
        if self.video_thread:
            self.video_thread.join()
        if self.osd_thread:
            self.osd_thread.join()

    def start_video(self):
        nc = sp.Popen(["/bin/nc", "-l", "-u", "5600"], stdout=sp.PIPE)
        hv = sp.Popen(["/opt/vc/src/hello_pi/hello_video/hello_video.bin.48-mm"], stdin=nc.stdout)
        hv.wait()

    def start_osd(self):
        qopenhd = sp.run("/usr/local/bin/QOpenHD")

if __name__ == '__main__':
    vid = VideoPlayer()
    vid.join()
