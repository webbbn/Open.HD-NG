
import glob

class CameraError(Exception):
    pass

from libc.errno cimport errno, EINTR, EINVAL
from libc.string cimport memset, memcpy, strerror
from libc.stdlib cimport malloc, calloc, free
from posix.select cimport fd_set, timeval, FD_ZERO, FD_SET, select
from posix.fcntl cimport O_RDWR
from posix.mman cimport PROT_READ, PROT_WRITE, MAP_SHARED
from typing import Any, List

cdef extern from 'linux/videodev2.h':
    ctypedef unsigned char           __u8
    ctypedef signed char             __s8
    ctypedef unsigned short          __u16
    ctypedef signed short            __s16
    ctypedef unsigned int            __u32
    ctypedef signed int              __s32
    ctypedef unsigned long long int  __u64
    ctypedef signed long long int    __s64

    enum: VIDIOC_G_FMT
    enum: VIDIOC_S_FMT
    enum: VIDIOC_S_PARM
    enum: VIDIOC_REQBUFS
    enum: VIDIOC_QUERYBUF
    enum: VIDIOC_STREAMON
    enum: VIDIOC_STREAMOFF
    enum: VIDIOC_QBUF
    enum: VIDIOC_DQBUF
    enum: VIDIOC_QUERYMENU
    enum: VIDIOC_QUERYCTRL
    enum: VIDIOC_G_CTRL
    enum: VIDIOC_S_CTRL
    enum: VIDIOC_ENUM_FMT
    enum: VIDIOC_ENUM_FRAMESIZES
    enum: V4L2_CID_BASE
    enum: V4L2_CID_LASTP1
    enum: V4L2_CID_PRIVATE_BASE
    enum: V4L2_CTRL_FLAG_DISABLED

    enum: V4L2_CTRL_CLASS_USER
    enum: V4L2_CTRL_CLASS_MPEG
    enum: V4L2_CTRL_CLASS_CAMERA
    enum: V4L2_CTRL_CLASS_FM_TX
    enum: V4L2_CTRL_CLASS_FLASH

    enum: V4L2_CTRL_FLAG_DISABLED
    enum: V4L2_CTRL_FLAG_GRABBED
    enum: V4L2_CTRL_FLAG_READ_ONLY
    enum: V4L2_CTRL_FLAG_UPDATE
    enum: V4L2_CTRL_FLAG_INACTIVE
    enum: V4L2_CTRL_FLAG_WRITE_ONLY
    enum: V4L2_CTRL_FLAG_NEXT_CTRL

    enum: V4L2_CID_BRIGHTNESS
    enum: V4L2_CID_CONTRAST
    enum: V4L2_CID_SATURATION
    enum: V4L2_CID_HUE
    enum: V4L2_CID_AUDIO_VOLUME
    enum: V4L2_CID_AUDIO_BALANCE
    enum: V4L2_CID_AUDIO_BASS
    enum: V4L2_CID_AUDIO_TREBLE
    enum: V4L2_CID_AUDIO_MUTE
    enum: V4L2_CID_AUDIO_LOUDNESS
    enum: V4L2_CID_BLACK_LEVEL
    enum: V4L2_CID_AUTO_WHITE_BALANCE
    enum: V4L2_CID_DO_WHITE_BALANCE
    enum: V4L2_CID_RED_BALANCE
    enum: V4L2_CID_BLUE_BALANCE
    enum: V4L2_CID_GAMMA
    enum: V4L2_CID_WHITENESS
    enum: V4L2_CID_EXPOSURE
    enum: V4L2_CID_AUTOGAIN
    enum: V4L2_CID_GAIN
    enum: V4L2_CID_HFLIP
    enum: V4L2_CID_VFLIP
    enum: V4L2_CID_POWER_LINE_FREQUENCY
    enum: V4L2_CID_HUE_AUTO
    enum: V4L2_CID_WHITE_BALANCE_TEMPERATURE
    enum: V4L2_CID_SHARPNESS
    enum: V4L2_CID_BACKLIGHT_COMPENSATION
    enum: V4L2_CID_CHROMA_AGC
    enum: V4L2_CID_COLOR_KILLER
    enum: V4L2_CID_COLORFX

    enum: V4L2_FRMSIZE_TYPE_DISCRETE
    enum: V4L2_FRMSIZE_TYPE_STEPWISE

    enum: V4L2_FRMIVAL_TYPE_DISCRETE
    enum: V4L2_FRMIVAL_TYPE_CONTINUOUS
    enum: V4L2_FRMIVAL_TYPE_STEPWISE

    cdef struct v4l2_pix_format:
        __u32   width
        __u32   height
        __u32   pixelformat
        __u32   field
        __u32   bytesperline
        __u32   sizeimage
        __u32   colorspace
        __u32   priv
        __u32   flags
        __u32   ycbcr_enc
        __u32   quantization
        __u32   xfer_func

    cdef struct v4l2_fract:
        __u32   numerator
        __u32   denominator

    cdef struct v4l2_captureparm:
        __u32              capability    #  Supported modes
        __u32              capturemode   #  Current mode
        v4l2_fract         timeperframe  #  Time per frame in seconds
        __u32              extendedmode  #  Driver-specific extensions
        __u32              readbuffers   #  # of buffers for read
        __u32              reserved[4]

    cdef struct v4l2_outputparm:
        __u32              capability   #  Supported modes
        __u32              outputmode   #  Current mode
        v4l2_fract         timeperframe #  Time per frame in seconds
        __u32              extendedmode #  Driver-specific extensions
        __u32              writebuffers #  # of buffers for write
        __u32              reserved[4]


cdef public union __v4l2_format_fmt:
    v4l2_pix_format        pix
    __u8 data[200]

cdef public union __v4l2_streamparam_param:
    v4l2_captureparm    capture;
    v4l2_outputparm     output;
    __u8        raw_data[200];  # user-defined


cdef extern from 'linux/videodev2.h':
    cdef struct v4l2_format:
        __u32 type
        __v4l2_format_fmt fmt

    cdef struct v4l2_requestbuffers:
        __u32 count
        __u32 type
        __u32 memory

    cdef union __v4l2_buffer_m:
        __u32          offset
        unsigned long  userptr
        __s32          fd

    cdef struct v4l2_buffer:
        __u32 index
        __u32 type
        __u32 memory
        __u32 length
        __u32 bytesused

        __v4l2_buffer_m m

    cdef enum v4l2_ctrl_type:
        V4L2_CTRL_TYPE_INTEGER
        V4L2_CTRL_TYPE_BOOLEAN
        V4L2_CTRL_TYPE_MENU
        V4L2_CTRL_TYPE_BUTTON
        V4L2_CTRL_TYPE_INTEGER64
        V4L2_CTRL_TYPE_STRING
        V4L2_CTRL_TYPE_CTRL_CLASS

    cdef struct v4l2_queryctrl:
        __u32             id
        __u32             type
        __u8              name[32]
        __s32             minimum
        __s32             maximum
        __s32             step
        __s32             default_value
        __u32             flags
        __u32             reserved[2]

    cdef struct v4l2_querymenu:
        __u32 id
        __u32 index
        __u8  name[32]
        __u32 reserved

    cdef struct v4l2_control:
        __u32 id
        __s32 value

    cdef struct v4l2_fmtdesc:
        __u32               index             # Format number
        __u32               type              # enum v4l2_buf_type
        __u32               flags
        __u8                description[32]   # Description string
        __u32               pixelformat       # Format fourcc
        __u32               reserved[4]

    cdef struct v4l2_frmsize_discrete:
        __u32                   width           # Frame width [pixel]
        __u32                   height          # Frame height [pixel]

    cdef struct v4l2_frmsize_stepwise:
        __u32                   min_width       # Minimum frame width [pixel]
        __u32                   max_width       # Maximum frame width [pixel]
        __u32                   step_width      # Frame width step size [pixel]
        __u32                   min_height      # Minimum frame height [pixel]
        __u32                   max_height      # Maximum frame height [pixel]
        __u32                   step_height     # Frame height step size [pixel]

    cdef struct v4l2_frmsizeenum:
        __u32                   index           # Frame size number
        __u32                   pixel_format    # Pixel format
        __u32                   type            # Frame size type the device supports.
        v4l2_frmsize_discrete   discrete
        v4l2_frmsize_stepwise   stepwise
        __u32   reserved[2];                    # Reserved space for future use

    cdef struct v4l2_frmival_stepwise:
        v4l2_fract       min             # Minimum frame interval [s]
        v4l2_fract       max             # Maximum frame interval [s]
        v4l2_fract       step            # Frame interval step size [s]

    cdef struct v4l2_frmivalenum:
        __u32                   index           # Frame format index
        __u32                   pixel_format    # Pixel format
        __u32                   width           # Frame width
        __u32                   height          # Frame height
        __u32                   type            # Frame interval type the device supports.

        # Frame interval
        v4l2_fract              discrete;
        v4l2_frmival_stepwise   stepwise;

        __u32   reserved[2];                    # Reserved space for future use

    cdef struct v4l2_streamparm:
        __u32    type                   # enum v4l2_buf_type
        __v4l2_streamparam_param parm


cdef extern from 'libv4l2.h':
    enum: V4L2_PIX_FMT_RGB24
    enum: V4L2_PIX_FMT_H264
    enum: V4L2_BUF_TYPE_VIDEO_CAPTURE
    enum: V4L2_MEMORY_MMAP
    enum: V4L2_FIELD_INTERLACED

    cdef struct v4lconvert_data:
        pass

    int v4l2_open(const char *device_name, int flags)
    int v4l2_close(int fd)

    int v4l2_ioctl(int fd, int request, void *argp)

    void *v4l2_mmap(void *start, size_t length, int prot, int flags, int fd,
                    __s64 offset)
    int v4l2_munmap(void *_start, size_t length)

cdef extern from 'libv4lconvert.h':
    v4lconvert_data *v4lconvert_create(int fd)
    int v4lconvert_convert(v4lconvert_data *data,
                           const v4l2_format *src_fmt,
                           const v4l2_format *dest_fmt,
                           unsigned char *src, int src_size,
                           unsigned char *dest, int dest_size)

cdef inline int xioctl(int fd, unsigned long int request, void *arg):
    cdef int r = v4l2_ioctl(fd, request, arg)
    while -1 == r and EINTR == errno:
        r = v4l2_ioctl(fd, request, arg)

    return r

cdef struct buffer_info:
    void *start
    size_t length

cdef class Frame:
    cdef int fd
    cdef fd_set fds

    cdef v4l2_format fmt
    cdef v4l2_streamparm parm

    cdef v4l2_requestbuffers buf_req
    cdef v4l2_buffer buf
    cdef buffer_info *buffers

    cdef timeval tv

    def __cinit__(self, device_path, width = 640, height = 480):
        device_path = device_path.encode()

        self.fd = v4l2_open(device_path, O_RDWR)
        if -1 == self.fd:
            raise CameraError('Error opening device {}'.format(device_path))

        memset(&self.fmt, 0, sizeof(self.fmt))
        self.fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        self.fmt.fmt.pix.width = width
        self.fmt.fmt.pix.height = height
        self.fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_H264
        self.fmt.fmt.pix.field = V4L2_FIELD_INTERLACED

        #if -1 == xioctl(self.fd, VIDIOC_G_FMT, &self.fmt):
        #raise CameraError('Getting format failed')

        if -1 == xioctl(self.fd, VIDIOC_S_FMT, &self.fmt):
            raise CameraError('Setting format failed')

        memset(&self.parm, 0, sizeof(self.parm))
        self.parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        self.parm.parm.output.timeperframe.numerator = 1;
        self.parm.parm.output.timeperframe.denominator = 30;
        if -1 == xioctl(self.fd, VIDIOC_S_PARM, &self.parm):
            raise CameraError('Setting params failed')

        memset(&self.buf_req, 0, sizeof(self.buf_req))
        self.buf_req.count = 4
        self.buf_req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        self.buf_req.memory = V4L2_MEMORY_MMAP

        if -1 == xioctl(self.fd, VIDIOC_REQBUFS, &self.buf_req):
            raise CameraError('Requesting buffer failed')

        self.buffers = <buffer_info *>calloc(self.buf_req.count,
                                             sizeof(self.buffers[0]))
        if self.buffers == NULL:
            raise CameraError('Allocating memory for buffers array failed')
        self.initialize_buffers()

        if -1 == xioctl(self.fd, VIDIOC_STREAMON, &self.buf.type):
            raise CameraError('Starting capture failed')

    cdef inline int initialize_buffers(self) except -1:
        for buf_index in range(self.buf_req.count):
            memset(&self.buf, 0, sizeof(self.buf))
            self.buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
            self.buf.memory = V4L2_MEMORY_MMAP
            self.buf.index = buf_index

            if -1 == xioctl(self.fd, VIDIOC_QUERYBUF, &self.buf):
                raise CameraError('Querying buffer failed')

            bufptr = v4l2_mmap(NULL, self.buf.length,
                               PROT_READ | PROT_WRITE,
                               MAP_SHARED, self.fd, self.buf.m.offset)

            if bufptr == <void *>-1:
                raise CameraError('MMAP failed: {}'.format(
                    strerror(errno).decode())
                )

            self.buffers[buf_index] = buffer_info(bufptr, self.buf.length)

            memset(&self.buf, 0, sizeof(self.buf))
            self.buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
            self.buf.memory = V4L2_MEMORY_MMAP
            self.buf.index = buf_index

            if -1 == xioctl(self.fd, VIDIOC_QBUF, &self.buf):
                raise CameraError('Exchanging buffer with device failed')

        return 0


    cpdef bytes get_frame(self):
        FD_ZERO(&self.fds)
        FD_SET(self.fd, &self.fds)

        self.tv.tv_sec = 2

        r = select(self.fd + 1, &self.fds, NULL, NULL, &self.tv)
        while -1 == r and errno == EINTR:
            FD_ZERO(&self.fds)
            FD_SET(self.fd, &self.fds)

            self.tv.tv_sec = 2

            r = select(self.fd + 1, &self.fds, NULL, NULL, &self.tv)

        if -1 == r:
            raise CameraError('Waiting for frame failed')

        memset(&self.buf, 0, sizeof(self.buf))
        self.buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        self.buf.memory = V4L2_MEMORY_MMAP

        if -1 == xioctl(self.fd, VIDIOC_DQBUF, &self.buf):
            raise CameraError('Retrieving frame failed')

        buf =  self.buffers[self.buf.index].start
        buf_len = self.buf.bytesused

        frame_data = <unsigned char *>malloc(buf_len * sizeof(char))
        try:
            memcpy(frame_data, buf, buf_len)
            if -1 == xioctl(self.fd, VIDIOC_QBUF, &self.buf):
                raise CameraError('Exchanging buffer with device failed')
            return frame_data[:buf_len]
        finally:
            free(frame_data)

    @property
    def fd(self):
        return self.fd

    def close(self):
        xioctl(self.fd, VIDIOC_STREAMOFF, &self.buf.type)

        for i in range(self.buf_req.count):
            v4l2_munmap(self.buffers[i].start, self.buffers[i].length)

        v4l2_close(self.fd)


cdef class Control:

    cdef int fd

    def __cinit__(self, device_path):
        device_path = device_path.encode()

        self.fd = v4l2_open(device_path, O_RDWR)
        if -1 == self.fd:
            raise CameraError('Error opening device {}'.format(device_path))

    def __cdel__(self):
        self.close()
            
    cdef enumerate_menu(self, v4l2_queryctrl queryctrl):
        cdef v4l2_querymenu querymenu
        querymenu.id = queryctrl.id
        querymenu.index = queryctrl.minimum
        menu = {}
        while querymenu.index <= queryctrl.maximum:
            if 0 == xioctl(self.fd, VIDIOC_QUERYMENU, & querymenu):
                menu[querymenu.name] = querymenu.index
            querymenu.index += 1
        return menu

    def get_controls(self):
        cdef v4l2_queryctrl queryctrl
        queryctrl.id = V4L2_CTRL_CLASS_USER | V4L2_CTRL_FLAG_NEXT_CTRL
        controls = []
        control_type = {
            V4L2_CTRL_TYPE_INTEGER: 'int',
            V4L2_CTRL_TYPE_BOOLEAN: 'bool',
            V4L2_CTRL_TYPE_MENU: 'menu'
        }

        while (0 == xioctl(self.fd, VIDIOC_QUERYCTRL, & queryctrl)):
            control = {}
            control['name'] = queryctrl.name.decode("utf-8")
            control['type'] = control_type[queryctrl.type]
            control['id'] = queryctrl.id
            control['min'] = queryctrl.minimum
            control['max'] = queryctrl.maximum
            control['step'] = queryctrl.step
            control['default'] = queryctrl.default_value
            control['value'] = self.get_control_value(queryctrl.id)
            if queryctrl.flags & V4L2_CTRL_FLAG_DISABLED:
                control['disabled'] = True
            else:
                control['disabled'] = False

                if queryctrl.type == V4L2_CTRL_TYPE_MENU:
                    control['menu'] = self.enumerate_menu(queryctrl)

            controls.append(control)

            queryctrl.id |= V4L2_CTRL_FLAG_NEXT_CTRL

        return controls

    cpdef void set_control_value(self, control_id, value):
        cdef v4l2_queryctrl queryctrl
        cdef v4l2_control control

        memset(&queryctrl, 0, sizeof(queryctrl))
        queryctrl.id = control_id

        if -1 == xioctl(self.fd, VIDIOC_QUERYCTRL, &queryctrl):
            if errno != EINVAL:
                raise CameraError('Querying control')
            else:
                raise AttributeError('Control is not supported')
        elif queryctrl.flags & V4L2_CTRL_FLAG_DISABLED:
            raise AttributeError('Control is not supported')
        else:
            memset(&control, 0, sizeof(control))
            control.id = control_id
            control.value = value

            if -1 == xioctl(self.fd, VIDIOC_S_CTRL, &control):
                raise CameraError('Setting control')

    cpdef int get_control_value(self, control_id):
        cdef v4l2_queryctrl queryctrl
        cdef v4l2_control control

        memset(&queryctrl, 0, sizeof(queryctrl))
        queryctrl.id = control_id

        if -1 == xioctl(self.fd, VIDIOC_QUERYCTRL, &queryctrl):
            if errno != EINVAL:
                raise CameraError('Querying control')
            else:
                raise AttributeError('Control is not supported')
        elif queryctrl.flags & V4L2_CTRL_FLAG_DISABLED:
            raise AttributeError('Control is not supported')
        else:
            memset(&control, 0, sizeof(control))
            control.id = control_id

            if 0 == xioctl(self.fd, VIDIOC_G_CTRL, &control):
                return control.value
            else:
                raise CameraError('Getting control')

    def get_formats(self):
        cdef v4l2_fmtdesc fmt
        cdef v4l2_frmsizeenum frmsize
        cdef v4l2_frmivalenum frmival
        cdef char[5] fmtstr
        cdef bytes format
        ret = []

        fmt.index = 0
        fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        while 0 <= xioctl(self.fd, VIDIOC_ENUM_FMT, &fmt):
            frmsize.pixel_format = fmt.pixelformat
            memcpy(fmtstr, &fmt.pixelformat, 4)
            fmtstr[4] = 0;
            format = fmtstr

            frmsize.index = 0
            while 0 <= xioctl(self.fd, VIDIOC_ENUM_FRAMESIZES, &frmsize):
                if V4L2_FRMSIZE_TYPE_DISCRETE == frmsize.type:
                    ret.append({"format": format.decode("utf-8"),
                                "type": "discrete",
                                "width": frmsize.discrete.width,
                                "height": frmsize.discrete.height})
                elif V4L2_FRMSIZE_TYPE_STEPWISE == frmsize.type:
                    ret.append({"format": format.decode("utf-8"),
                                "type": "stepwise",
                                "width": frmsize.stepwise.width,
                                "height": frmsize.stepwise.height})
                frmsize.index += 1
            fmt.index += 1
        return ret

    def close(self):
        if (self.fd > 0):
            v4l2_close(self.fd)
            self.fd = -1

def get_devices():
    devs = sorted(glob.glob("/dev/video*"))
    return devs
