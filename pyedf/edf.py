"""
Methods for dealing with EDF+ files.
"""

from struct import unpack, calcsize
from collections import namedtuple

def _scale(v, s, d):
    return ((v-s[0])/(s[1]-s[0])) * (d[1]-d[0]) + d[0]


class BadEdfException(Exception):
    """Raised if the file is not in the correct EDF+ format."""
    pass


# Header containers
_EdfHeader = namedtuple('EdfHeader',
        'ver pid rid sdate stime nbyte reserved ndata duration nsignal'
        )

_SignalHeader = namedtuple('EdfSignalHeader',
        'label ttype pdim pmin pmax dmin dmax preflt nsample reserved offset'
        )

# Useful structures
_Timestamp = namedtuple('EdfTime', 'h m s')


class EdfData(list):
    def __init__(self, s, d):
        list.__init__(self, d)
        self.signal = s
    def __repr__(self):
        return "EdfData(s={}, d=[{} samples])".format(self.signal, len(self))


class EdfFile(object):
    """Represents a single EDF+ datastream."""

    def __init__(self, filename):
        """Reads an EDF+ file from disk and returns an EdfFile object."""

        # Decode bytes to strings
        bdecode = lambda bl: [b.decode("ascii").strip() for b in bl]

        # EDF+ Specifications
        hdr_fmt  = '<8s80s80s8s8s8s44s8s8s4s'
        hdr_size = calcsize(hdr_fmt)

        shdr_size = {
                'label':16, 'ttype':80, 'pdim':8, 'pmin':8, 'pmax':8,
                'dmin':8, 'dmax':8, 'preflt':80, 'nsample':8, 'reserved':32
                }

        shdr_order = [
                'label', 'ttype', 'pdim', 'pmin', 'pmax',
                'dmin', 'dmax', 'preflt', 'nsample', 'reserved'
                ]

        shdr_type = {
                'label':str, 'ttype':str, 'pdim':str, 'pmin':float, 'pmax':float,
                'dmin':int, 'dmax':int, 'preflt':str, 'nsample':int, 'reserved':str
                }

        # Initialise
        self.header = None
        self.signals = []
        self.filename = filename
        self._data_record_size = 0
        self._sigfmt = "<{}h"


        with open(filename, "rb") as f:
            # Try and read the entire header
            hdr_bytes = f.read(hdr_size)

            if len(hdr_bytes) != hdr_size:
                raise BadEdfException

            self.header = _EdfHeader._make( bdecode(unpack(hdr_fmt, hdr_bytes)) )

            curpos = f.tell()
            if curpos != hdr_size:
                raise BadEdfException

            # Get signal headers
            def unpack_array(count, size, formatter):
                fmt   = '<' + '{}s'.format(size) * count
                csize = calcsize(fmt)
                b     = f.read(csize)
                if len(b) != csize:
                    raise BadEdfException
                return list( map(formatter, bdecode(unpack(fmt, b))) )
                
            nsig = int(self.header.nsignal)
            sdata = {
                    k:unpack_array(nsig, shdr_size[k], shdr_type[k]) 
                    for k in shdr_order
                    }

            # Check we have read all the header data
            curpos = f.tell()
            if curpos != int(self.header.nbyte):
                raise BadEdfException

            sdata['offset'] = []
            offset = 0
            for ns in sdata['nsample']:
                sdata['offset'].append(offset)
                offset += calcsize(self._sigfmt.format(int(ns)))
            self._data_record_size = offset

            for i in range(nsig):
                d = {k:v[i] for k,v in sdata.items()}
                self.signals.append(_SignalHeader(**d))

            # Calculate total duration
            seconds = float(self.header.duration) * int(self.header.ndata)
            mins, secs  = divmod(seconds, 60)
            hours, mins = divmod(mins, 60)
            self.duration = _Timestamp._make([hours, mins, secs])

    def read(self):
        """Returns all data records."""

        spos  = int(self.header.nbyte)
        ndata = int(self.header.ndata) 
        nsig  = len(self.signals)
        recs  = []

        with open(self.filename, "rb") as f:
            f.seek(spos)
            while True:
                byt = f.read(self._data_record_size)

                # Keep reading until we run out of stuff to read
                if len(byt) == 0:
                    break
                if len(byt) < self._data_record_size:
                    print("Warning: reached end of file. {}/{} bytes left."
                            .format(len(byt), self._data_record_size)
                            )
                    break

                # byt is nsample * nsignal integers
                nint = sum([s.nsample for s in self.signals])
                fmt  = self._sigfmt.format(nint)
                ints = unpack(fmt, byt)

                dat = []
                i   = 0
                for s in self.signals:
                    dat.append(EdfData(s, ints[i:i+s.nsample]))
                    i += s.nsample

                recs.append(dat)

        return recs

