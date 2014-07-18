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
        """Reads a RAW file from disk and returns a RawFile object."""

        with open(filename, 'rb') as f:
            # Read the header
            hdr_fmt = '>i6hi5hih'
            hdr_size = calcsize(hdr_fmt)

            b = f.read(hdr_size)

            if len(b) != hdr_size:
                raise BadRawException
            
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
                raise BadRawException

            # Get the unique event codes (4 characters)
            nchar = 4
            ncodes = self.header.nevent

            code_fmt = '>' + '{}s'.format(nchar) * ncodes
            code_size = calcsize(code_fmt)

            b = f.read(code_size)

            if len(b) != code_size:
                raise BadRawException

            self.codes = unpack(code_fmt, b)

            # Store where the data records begin
            self._data_offset = f.tell()

            # Calculate size of individual data record
            nchan = self.header.nchan
            self._rec_fmt = '>{}{}'.format(nchan+ncodes, self.rep[1])
            self._rec_size = calcsize(self._rec_fmt)
