"""
Methods for dealing with RAW (simple binary format) files from NetStation.
Only continuous files are supported.
"""

from struct import unpack, calcsize
from collections import namedtuple

# Header
_RawHeader = namedtuple('RawHeader',
        'version year month day hour min s ms rate nchan gain nconv amprange nsample nevent'
        )

class BadRawException(Exception):
    """Raised if the file is not in the correct EDF+ format."""
    pass

class RawFile(object):
    """Representation of a RAW file."""

    def __init__(self, filename):
        import os

        if not os.path.exists(filename):
            raise BadRawException('File does not exist.')

        self.filename = filename

    def __enter__(self):
        self._fhandle = open(self.filename, 'rb')
        self._read_header()
        return self

    def __exit__(self, extype, exvalue, extraceback):
        self._fhandle.close()
        if extype != None:
            print("Error: "+exvalue)
        return True

    def _read_header(self):
        f = self._fhandle

        # Read the header
        hdr_fmt = '>i6hi5hih'
        hdr_size = calcsize(hdr_fmt)

        b = f.read(hdr_size)

        if len(b) != hdr_size:
            raise BadRawException('Incomplete header.')
        
        self.header = _RawHeader._make(unpack(hdr_fmt, b))

        # Determine filetype first from first four bytes (big-endian)
        # 2 = integer, 4 = single FP, 6 = double FP

        ver = self.header.version

        if ver == 2:
            self.rep = ('int', 'h')
        elif ver == 4:
            self.rep = ('sfp', 'f')
        elif ver == 6:
            self.rep = ('dfp', 'd')
        else:
            self.rep = ('unk', 'x')
            raise BadRawException('Unknown filetype.')

        # Get the unique event codes (4 characters)
        nchar = 4
        ncodes = self.header.nevent

        code_fmt = '>' + '{}s'.format(nchar) * ncodes
        code_size = calcsize(code_fmt)

        b = f.read(code_size)

        if len(b) != code_size:
            raise BadRawException('Incomplete event code listing.')

        self.codes = unpack(code_fmt, b)

        # Store where the data records begin
        self._data_offset = f.tell()

        # Calculate size of individual data record
        nchan = self.header.nchan
        self._rec_fmt = '>{}{}'.format(nchan+ncodes, self.rep[1])
        self._rec_size = calcsize(self._rec_fmt)


    def next(self):
        """
        Return next data record. 
        Returns False,False if at the end of the file or an error was encountered.
        """

        f = self._fhandle

        b = f.read(self._rec_size)

        if len(b) == 0:
            return False, False

        if len(b) < self._rec_size:
            print("Warning: reached end of file {}/{} bytes left."
                    .format(len(b), self._rec_size)
                    )
            return False, False

        # Data record stores Nchan values and then Ncode values which
        # define the event markings at each sample point.
        # Easiest to return a [] of events and [][] of signal values.

        data = unpack(self._rec_fmt, b)
        nc = self.header.nchan
        ev_active = data[nc:]

        if len(ev_active) != self.header.nevent:
            print("Error: Incorrect number of event flags. {}/{}"
                    .format(len(ev_active), self.header.nevent)
                    )
            return False, False

        e = [x[1] for x in zip(ev_active, self.codes) if x[0]==1]

        return e, data[:nc]
