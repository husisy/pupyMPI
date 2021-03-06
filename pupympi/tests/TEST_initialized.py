#!/usr/bin/env python
# meta-description: Test establishment of MPI environment
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI

assert not MPI.initialized(), "The mpi environment was initialized before starting mpi.. wrong"

mpi = MPI()
assert MPI.initialized(), "The mpi environment was not initialized after starting mpi.. wrong"

# Close the sockets down nicely
mpi.finalize()

