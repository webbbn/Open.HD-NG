#!/usr/bin/env python3

import os
import threading
import subprocess as sp

class VideoPlayer(object):
    '''Constrols the ground-side video player / OSD'''
    video_player="/home/pi/wifibroadcast-hello_video/hello_video.bin.48-mm"
    osd_program="/usr/local/bin/QOpenHD"

    def __init__(self):
        self.done = False;
        if os.path.isfile(self.video_player) and os.access(self.video_player, os.X_OK) and \
           os.path.isfile(self.osd_program) and os.access(self.osd_program, os.X_OK):
            self.video_thread = threading.Thread(target = self.start_video)
            self.video_thread.start()
            self.osd_thread = threading.Thread(target = self.start_osd)
            self.osd_thread.start()
        else:
            self.video_thread = None
            self.osd_thread = None

    def __del__(self):
        self.done = True
        self.join()

    def running(self):
        return self.video_thread or self.osd_thread

    def join(self):
        if self.video_thread:
            self.video_thread.join()
        if self.osd_thread:
            self.osd_thread.join()

    def start_video(self):
        nc = sp.Popen(["/bin/nc", "-l", "-u", "5600"], stdout=sp.PIPE)
        hv = sp.Popen([self.video_player], stdin=nc.stdout)
        hv.wait()

    def start_osd(self):
        qopenhd = sp.run(self.osd_program)

if __name__ == '__main__':
    vid = VideoPlayer()
    vid.join()
