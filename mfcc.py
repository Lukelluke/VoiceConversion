#!/usr/bin/env python

import numpy
import scipy.fftpack
import scipy.interpolate
import scipy.linalg
import sys

from stf import STF

class MFCC:
    '''
    MFCC computation from spectrum information

    Reference
    ---------
     - http://aidiary.hatenablog.com/entry/20120225/1330179868
    '''

    def __init__(self, nfft, frequency, dimension = 16, channels = 16):
        assert dimension <= channels

        self.nfft = nfft
        self.frequency = frequency
        self.dimension = dimension
        self.channels = channels

        self.fscale = numpy.fft.fftfreq(self.nfft, d = 1.0 / self.frequency)[: self.nfft / 2]
        self.filterbank, self.fcenters = self.melFilterBank()

    def hz2mel(self, f):
        return 1127.01048 * numpy.log(f / 700.0 + 1.0)

    def mel2hz(self, m):
        return 700.0 * (numpy.exp(m / 1127.01048) - 1.0)

    def melFilterBank(self):
        fmax = self.frequency / 2
        melmax = self.hz2mel(fmax)

        nmax = self.nfft / 2
        df = self.frequency / self.nfft

        dmel = melmax / (self.channels + 1)
        melcenters = numpy.arange(1, self.channels + 1) * dmel
        fcenters = self.mel2hz(melcenters)

        indexcenter = numpy.round(fcenters / df)
        indexstart = numpy.hstack(([0], indexcenter[0: self.channels - 1]))
        indexstop = numpy.hstack((indexcenter[1: self.channels], [nmax]))

        filterbank = numpy.zeros((self.channels, nmax))
        for c in numpy.arange(0, self.channels):
            increment = 1.0 / (indexcenter[c] - indexstart[c])
            for i in numpy.arange(indexstart[c], indexcenter[c]):
                filterbank[c, i] = (i - indexstart[c]) * increment
            decrement = 1.0 / (indexstop[c] - indexcenter[c])
            for i in numpy.arange(indexcenter[c], indexstop[c]):
                filterbank[c, i] = 1.0 - ((i - indexcenter[c]) * decrement)
            filterbank[c] /= (indexstop[c] - indexstart[c]) / 2

        return filterbank, fcenters

    def mfcc(self, spectrum):
        spectrum = numpy.maximum(numpy.zeros(spectrum.shape), spectrum)
        mspectrum = numpy.log10(numpy.dot(spectrum, self.filterbank.transpose()))
        return scipy.fftpack.dct(mspectrum, norm = 'ortho')[:self.dimension]

    def delta(self, mfcc):
        mfcc = numpy.concatenate([[mfcc[0]], mfcc, [mfcc[-1]]])

        delta = None
        for i in xrange(1, mfcc.shape[0] - 1):
            slope = (mfcc[i + 1] - mfcc[i - 1]) / 2
            if delta is None:
                delta = slope
            else:
                delta = numpy.vstack([delta, slope])

        return delta

    def imfcc(self, mfcc):
        mfcc = numpy.hstack([mfcc, [0] * (self.channels - self.dimension)])
        mspectrum = scipy.fftpack.idct(mfcc, norm = 'ortho')
        tck = scipy.interpolate.splrep(self.fcenters, numpy.power(10, mspectrum))
        return scipy.interpolate.splev(self.fscale, tck)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage: %s <stf_file>' % sys.argv[0]
        sys.exit()

    stf = STF()
    stf.loadfile(sys.argv[1])

    mfcc = MFCC(stf.SPEC.shape[1] * 2, stf.frequency)
    res = mfcc.mfcc(stf.SPEC[stf.SPEC.shape[0] / 5])
    spec = mfcc.imfcc(res)

    print res

    import pylab

    pylab.subplot(211)
    pylab.plot(stf.SPEC[stf.SPEC.shape[0] / 5])
    pylab.ylim(0, 1.2)
    pylab.subplot(212)
    pylab.plot(spec)
    pylab.ylim(0, 1.2)
    pylab.show()
