from mpi.exceptions import MPIException

class Request:

    def __init__(self, type, communicator):
        if type not in ('send','receive'):
            raise MPIException("Invalid type in request creation. This should never happen. ")

        self.type = type
        self.communicator = communicator

        # FIXME: We also need other stuff here, but we'll wait

    def cancel(self):
        """
        Cancel a request. This can be used to free memory, but the request must be redone
        by all parties involved.
        """
        pass

    def wait(self):
        """
        Blocks until the request data can be garbage collected. This method can be used
        to create stable methods limiting the memory usage by not creating new send
        requets before the ressources for the current one has been removed.

        When waiting for a receive, the data will be returned to the calling function.

        On successfull completing the ressources occupied by this request object will
        be garbage collected.
        """
        if self.type == 'receive':
            return self.data

    def test(self):
        """
        A non-blocking way to see if the requset is ready to complete. If true a 
        following wait() should return very fast.
        """
        pass


