from mpi.exceptions import MPIException
from mpi.logger import Logger
import threading, time

class BaseRequest(object):
    def __init__(self):
        self._metadata = {'status' : 'new' }

        # Start a lock for this request object. The lock should be taken
        # whenever we change the content. It should be legal to read 
        # information without locking (like test()). We implement the release() and
        # acquire function on this class directly so the variable stays private
        self._metadata['lock'] = threading.Lock()
        
        # Start an event for waiting on the request
        self._metadata['waitevent'] = threading.Event()
        

    def release(self, *args, **kwargs):
        """
        Just forwarding method call to the internal lock
        """
        return self._metadata['lock'].release(*args, **kwargs)

    def acquire(self, *args, **kwargs):
        """
        Just forwarding method call to the internal lock
        """
        return self._metadata['lock'].acquire(*args, **kwargs)

class Request(BaseRequest):

    def __init__(self, request_type, communicator, participant, tag, data=None):
        super(Request, self).__init__()
        if request_type not in ('bcast_send', 'send','recv'):
            raise MPIException("Invalid request_type in request creation. This should never happen. ")

        self.request_type = request_type
        self.communicator = communicator
        self.participant = participant
        self.tag = tag
        self.data = data

        # Meta information we use to keep track of what is going on. There are some different
        # status a request object can be in:
        # 'new' ->       The object is newly created. If this is send the lower layer can start to 
        #                do stuff with the data
        # 'cancelled' -> The user cancelled the request. A some later point this will be removed
        # 'ready'     -> Means we have the data (in receive) or pickled the data (send) and can
        #                safely return from a test or wait call.

        Logger().debug("Request object created for communicator %s, tag %s and request_type %s and participant %s" % (self.communicator.name, self.tag, self.request_type, self.participant))

        callbacks = [ self.network_callback, ]
        
        # Start the network layer on a job as well
        # MOVE THIS TO THE MPI THREAD
        self.communicator.network.start_job(self, self.communicator, request_type, self.participant, tag, data, callbacks=callbacks)

        # If we have a request object we might already have received the
        # result. So we look into the internal queue to see. If so, we use the
        # network_callback method to update all the internal structure.
        if request_type == 'recv':
            data = communicator.pop_unhandled_message(participant, tag)
            if data:                
                Logger().debug("Unhandled message had data") # DEBUG: This sometimes happen in TEST_cyclic
                self.network_callback(lock=False, status="ready", data=data['data'], ffrom="Right-away-quick-fast-receive")
                return

    def network_callback(self, lock=True, caller="from-nowhere", *args, **kwargs):
        Logger().debug("Network callback in request called")

        if lock:
            Logger().info("REQUEST LOCKING %s" % caller)
            self.acquire()
            Logger().info("REQUEST LOCKED %s" % caller)

        if "status" in kwargs:
            Logger().info("Updating status in request from %s to %s <-- %s" % (self._m["status"], kwargs["status"], caller))
            self._metadata["status"] = kwargs["status"]

            if kwargs["status"] == "ready":
                self._metadata['waitevent'].set()
            
        if "data" in kwargs:
            Logger().info("Adding data to request object")
            self.data = kwargs["data"]
        
        if lock:
            Logger().info("REQUEST RELEASING %s" % caller)
            self.release()
            Logger().info("REQUEST RELEASED %s" % caller)

    def cancel(self):
        """
        Cancel a request. This can be used to free memory, but the request must be redone
        by all parties involved.
        
        http://www.mpi-forum.org/docs/mpi-11-html/node50.html
        """
        # We just set a status and return right away. What needs to happen can be done
        # at a later point
        self._metadata['status'] = 'cancelled'
        self.communicator.mpi.remove_pending_request( self )
        
    def wait(self):
        """
        Blocks until the request data can be garbage collected. This method can be used
        to create stable methods limiting the memory usage by not creating new send
        requests before the ressources for the current one has been removed.

        When waiting for a receive, the data will be returned to the calling function.

        On successfull completion the ressources occupied by this request object will
        be garbage collected.
               
        FIXME: The C version of wait() returns always a status, but we're returning data
               as it's the best thing in python. Maybe it would make sense to return a
               tuple containing something like (status, data). 
        """
        Logger().info("Starting a %s wait" % self.request_type)
        
        # See the second FIXME note in the docstring
        if self._metadata['status'] == "cancelled":
            Logger().debug("WAIT on cancel illegality")
            raise MPIException("Illegal to wait on a cancelled request object")
        
        self._metadata['waitevent'].wait()
        
        # We're done at this point. Set the request to be completed so it can be removed
        # later.
        self._metadata['status'] = 'finished'

        # Find the MPI object and removes this request object from the queue
        self.communicator.mpi.remove_pending_request( self )

        # Return none or the data
        if self.request_type == 'recv':
            return self.data

    def test(self):
        """
        A non-blocking check to see if the request is ready to complete. If true a 
        following wait() should return very fast.
        """
        return self._metadata['waitevent'].is_set()

    def get_status(self):
        # I think this is a API call? Check into it. 
        return self._metadata['status']
