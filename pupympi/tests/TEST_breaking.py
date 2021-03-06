#!/usr/bin/env python
# meta-description: Tests if that crashes in MPI program are propagated back to initiator
# meta-expectedresult: 1

# Simple pupympi program to test if horribly broken scripts manage to return their stderr

from mpi import MPI

#print "Threads before initialize %s" % activeCount()
mpi = MPI()
#print "Threads after initialize %s" % activeCount()

raise Exception("Forced error from rank %s" % mpi.MPI_COMM_WORLD.rank())

# This shouldnt run.
mpi.finalize()
