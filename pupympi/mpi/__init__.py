__version__ = 0.01

from mpi.comm import Communicator
import mpi

def runner(target, rank, size, *args, **kwargs):
    mpi.MPI_COMM_WORLD = Communicator(rank, size)
    target(*args, **kwargs)

def initialize(size, target, *args, **kwargs):
    # Start np procs and go through with it :)
    from multiprocessing import Process
    procs = {}

    for rank in range(size):
        p = Process(target=runner, args=(target, rank, size) + args, kwargs=kwargs)
        p.start()

def rank(COMM=None):
    import mpi
    if COMM:
        return 0
    else:
        return mpi.MPI_COMM_WORLD.rank

def size(COMM=None):
    import mpi
    if COMM:
        return 0
    else:
        return mpi.MPI_COMM_WORLD.size
