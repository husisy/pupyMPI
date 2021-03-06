#!/usr/bin/env python
# meta-description: Cyclic blocking send/receive between two processes. Runs 500 iterations, and verifies that the data received are correct. (at current timeout-bound design, 500 iterations can take about 600 seconds)
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 120

from mpi import MPI
from mpi import constants

mpi = MPI()
world = mpi.MPI_COMM_WORLD
rank = world.rank()

f = open(constants.DEFAULT_LOGDIR+"mpi.stress_sr.rank%s.log" % rank, "w")

#max_iterations = 10
max_iterations = 500

t1 = world.Wtime()    

TAG = 13

def gen_msg(rank, iteration):
    return "rank%s,iterations%s" % (rank, iteration)

if rank <= 1:
    other = 1
    if rank == 1:
        other = 0

    for it in xrange(max_iterations):
        if rank == 0: 
            world.send( gen_msg(rank, it), other, TAG)

        recv = world.recv(other, TAG)

        if rank == 1: 
            world.send(gen_msg(rank, it), other, TAG)

        assert recv == gen_msg(other, it)

        f.write("Iteration %s completed for rank %s\n" % (it, rank))
        f.flush()
f.write( "Done for rank %d\n" % rank)

t2 = world.Wtime()
time = (t2 - t1) 

f.write( "Total time was %s for %i iterations" % (time, max_iterations))
f.flush()
f.close()

mpi.finalize()

