from struct import unpack, calcsize
from collections import namedtuple


class BadFormatException(Exception):
    pass

class 

EdfHeader = namedtuple('EdfHeader',
        'ver pid rid sdate stime nbyte reserved ndata duration nsignal'
        )


SignalHeader = namedtuple('SignalHeader',
        'label ttype pdim pmin pmax dmin dmax preflt nsample reserved offset'
        )


class EdfFile(object):

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

        with open(filename, "rb") as f:
            # Try and read the entire header
            hdr_bytes = f.read(hdr_size)

            if len(hdr_bytes) != hdr_size:
                raise BadFormatException

            self.header = EdfHeader._make( bdecode(unpack(hdr_fmt, hdr_bytes)) )

            curpos = f.tell()
            if curpos != hdr_size:
                raise BadFormatException

            # Get signal headers
            def unpack_array(count, size, formatter):
                fmt   = '<' + '{}s'.format(size) * count
                csize = calcsize(fmt)
                b     = f.read(csize)
                if len(b) != csize:
                    raise BadFormatException
                return list( map(formatter, bdecode(unpack(fmt, b))) )
                
            nsig = int(self.header.nsignal)
            sdata = {
                    k:unpack_array(nsig, shdr_size[k], shdr_type[k]) 
                    for k in shdr_order
                    }

            # Check we have read all the header data
            curpos = f.tell()
            if curpos != int(self.header.nbyte):
                raise BadFormatException

            sdata['offset'] = []
            offset = curpos
            for ns in sdata['nsample']:
                sdata['offset'].append(offset)
                offset += calcsize('<{}i'.format(int(ns)))

            for i in range(nsig):
                d = {k:v[i] for k,v in sdata.items()}
                self.signals.append(SignalHeader(**d))


    def read(self, nsample, sigid, record=0):
        """Read nsample samples of data from a signal."""

        if sigid >= len(self.signals) or record > int(self.header.ndata):
            return None
        
        signal = self.signals[sigid]

        # Data is in integers
        fmt = '<{}i'.format(nsample)
        size = calcsize(fmt)

        with open(self.filename, "rb") as f:
            print("Offset", signal.offset)
            f.seek(signal.offset)
            b = f.read(size)

        if len(b) != size:
            raise BadFormatException

        return unpack(fmt, b)

