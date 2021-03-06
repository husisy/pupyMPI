from mpi import MPI

import time, random

def solver_it(mpi):
    world = mpi.MPI_COMM_WORLD
    rank = world.rank()
    delta = 1

    # Calc takes times
    time.sleep(0.1)

    # Fake a delta.
    delta = min(delta, random.random())

    # Take the sum of the delta
    world_delta = world.allreduce(delta, sum)

    # Update the user register
    mpi.user_register = {
        'delta' : delta,
        'world_delta' : world_delta,
        'iterations' : i,
    }

if __name__ == "__main__":

    it = 100000
    m = MPI()
    for i in range(it):
        solver_it(m)

