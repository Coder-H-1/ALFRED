# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
import numpy as np
from libc.math cimport sqrt

cdef void _fwht_inplace(float* data, int n) noexcept nogil:
    cdef int h = 1, i, j
    cdef float u, v
    while h < n:
        i = 0
        while i < n:
            j = i
            while j < i + h:
                u = data[j]
                v = data[j + h]
                data[j] = u + v
                data[j + h] = u - v
                j += 1
            i += h * 2
        h *= 2
    cdef float factor = 1.0 / sqrt(n)
    for i in range(n):
        data[i] *= factor

def fwht_1d_fast(float[:] x):
    cdef int orig_len = x.shape[0]
    cdef int n = 1
    while n < orig_len:
        n <<= 1
    
    cdef object out = np.zeros(n, dtype=np.float32)
    cdef float[:] out_view = out
    cdef int i
    for i in range(orig_len):
        out_view[i] = x[i]
    
    _fwht_inplace(&out_view[0], n)
    return out

def fwht_2d_fast(float[:, :] matrix):
    cdef int batch_size = matrix.shape[0]
    cdef int dim = matrix.shape[1]
    cdef int n = 1
    while n < dim:
        n <<= 1
    
    cdef object out = np.zeros((batch_size, n), dtype=np.float32)
    cdef float[:, :] out_view = out
    cdef int b, j
    for b in range(batch_size):
        for j in range(dim):
            out_view[b, j] = matrix[b, j]
        _fwht_inplace(&out_view[b, 0], n)
    return out
