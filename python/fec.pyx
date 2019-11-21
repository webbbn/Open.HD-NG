
import numpy as np
import sys
import math
import struct
import zlib
from libc.string cimport memcpy
from libc.stdlib cimport malloc, free
from libc.stdint cimport uint8_t, uint16_t, uint32_t
from libcpp.map cimport map
from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp.memory cimport shared_ptr

cdef extern from 'fec.h':
    void fec_init()
    void fec_encode(unsigned int blockSize,       # The size of each data/FEC block
		    unsigned char **data_blocks,  # The K data blocks
		    unsigned int nrDataBlocks,    # The number of data blocks (K)
		    unsigned char **fec_blocks,   # Buffers to store he N FEC blocks in
		    unsigned int nrFecBlocks)     # The number of FEC blocks (N)

    void fec_decode(unsigned int blockSize,       # The size of each data/FEC block
		    unsigned char **data_blocks,  # The K data block buffers (some should contain data)
		    unsigned int nr_data_blocks,  # The number of data blocks (K)
		    unsigned char **fec_blocks,   # The (M <= N) FEC blocks
		    unsigned int *fec_block_nos,  # An array of indexes of the FEC blocks passed in
		    unsigned int *erased_blocks,  # An array of indexes of the data blocks that are not valid
		    unsigned short nr_fec_blocks) # The number (M) of FEC blocks passed in.

cdef extern from 'fec.hh':
    enum: FEC_PARTIAL
    enum: FEC_COMPLETE
    enum: FEC_ERROR
    cdef uint16_t m_block_size

    cdef cppclass FECBlock:
        FECBlock(uint8_t seq_num, uint8_t block, uint8_t nblocks, uint8_t nfec_blocks,
	         uint16_t data_length)
        uint8_t *pkt_data()
        uint16_t pkt_length()
        uint8_t seq_num()

    cdef cppclass FECEncoder:
        FECEncoder(uint8_t num_blocks, uint8_t num_fec_blocks, uint16_t block_size)
        FECEncoder()
        void encode(const uint8_t *buf, size_t buf_len)
        shared_ptr[FECBlock] get_block()

    cdef cppclass FECDecoder:
        FECDecoder()
        vector[uint8_t*] get_block()
        int add_block(const uint8_t * buf, uint16_t block_length)

    cdef cppclass FECBufferEncoder:
        FECBufferEncoder()
        FECBufferEncoder(uint32_t maximum_block_size, float fec_ratio)
        vector[shared_ptr[FECBlock]] encode_buffer(const uint8_t* buf, size_t length)

fec_partial = FEC_PARTIAL
fec_complete = FEC_COMPLETE
fec_error = FEC_ERROR

cdef class PyFECDecode:
    cdef FECDecoder m_dec
    cdef uint16_t m_block_size;

    def __cinit__(self):
        self.m_dec = FECDecoder()

    # def add_block(self, buf):
    #     return self.m_dec.add_block(buf, len(buf))

    # def get_blocks(self):
    #     ret = []
    #     while 1:
    #         b = self.m_dec.get_block()
    #         #if not b:
    #         #    break;
    #         #ary = np.asarray(<uint8_t[:self.m_block_size]>b)
    #         #ret.append(ary)
    #     return ret

cdef class PyFECEncoder:
    cdef FECEncoder m_enc

    # def __cinit__(self, uint8_t num_blocks, uint8_t num_fec_blocks, uint16_t max_block_size)
    #               uint8_t start_seq_num):
    #     self.m_enc = FECEncoder(num_blocks, num_fec_blocks, block_size, start_seq_num)

    # def encode(self, msg):
    #     self.m_enc.encode(msg, len(msg))

    # def get_blocks(self):
    #     ret = []
    #     for b in self.m_enc.blocks():
    #         ary = np.asarray(<uint8_t[:self.m_block_size + 4]>b)
    #         ret.append(ary)
    #     return ret

cdef class PyFECBufferEncoder:
    cdef FECBufferEncoder m_enc

    def __cinit__(self, uint32_t maximum_block_size, double fec_ratio):
        self.m_enc = FECBufferEncoder(maximum_block_size, fec_ratio)

    def encode_buffer(self, buf):
        ret = []
        blocks = self.m_enc.encode_buffer(buf, len(buf))
        for b in blocks:
            ary = b.get().pkt_data()[:b.get().pkt_length()]
            ret.append(ary)
        return ret
