pyedf
=====

A native python library for dealing with European Data Format (EDF+)

Loading
-------

To start working with an EDF file and load all the data records into ``data``::

    from pyedf import EdfFile

    f = EdfFile("/path/to/file")
    data = f.read()

Metadata
--------

After loading, EDF metadata is stored as a named tuple in ``f.header`` and
signal headers as a list of named tuples in ``f.signals``.


Todo
----

* A streaming interface for live recording and long datafiles.
