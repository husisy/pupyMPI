import threading, sys
from mpi import constants
from mpi.logger import Logger
from mpi.topology import tree

class BaseCollectiveRequest(object):
    def __init__(self, *args, **kwargs):
        self.tag = None

        # This object (with the acquire() and release() methods) defined below
        # opens for the pythonic way to lock an object (with-keyword)
        self._lock = threading.Lock()
        self._finished = threading.Event()
        self._dirty = False
        self._overtaken_request = None
        self._parent_request = None
        
        self.init_args = args
        self.init_kwargs = kwargs 

    def acquire(self):
        """
        The central request object. This is an internal locking facility
        for securing atomic access to the object.

        This function acquires the lock.
        """
        self._lock.acquire()

    def release(self):
        """
        This function releases the lock.
        """
        self._lock.release()

    def test(self):
        """
        Test if the collective operation is finished. That is if the :func:`wait`
        function will return right away.
        """
        return self._finished.is_set()
    
    def done(self):
        "Each algorithm must call this method when the internal flow is done."
        if self._parent_request:
            self._parent_request._finished.set()
            
        self._finished.set()

    def wait(self):
        """
        Wait until the collective operation has finished and then return the data.
        """
        self._finished.wait()

        if self._overtaken_request:
            return self._overtaken_request._get_data()
        else:
            return self._get_data()
        
    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        raise NotImplementedError("The accept() method was not implemented by the inheriting class.")

    def accept_msg(self, *args, **kwargs):
        raise NotImplementedError("The accept_msg() method was not implemented by the inheriting class.")

    def start(self):
        raise NotImplementedError("The start() method was not implemented by the inheriting class.")

    # Not all algorithms know enough to select the proper algorithm. For example if a broadcast makes a
    # not standard algorithm choice based on the data only the root will know. Therefore we will change
    # algorithm on the receiver side when this extended information is available. The functions below 
    # are helpers for that.
    def is_dirty(self):
        """
        Return a boolean indicating if the request object has already participated in a receive
        or send. 
        """
        return self._dirty
    
    def mark_dirty(self):
        self._dirty = True
        
    def overtake(self, request_cls):
        #Logger().debug("OVERTAKING  with request_cls:%s init_args:%s init_kwargs:%s" % (request_cls, self.init_args, self.init_kwargs) )
        request = request_cls(*self.init_args, **self.init_kwargs) # Initial args are reused
        
        # There is another request that will take our place. We save a reference to it
        # and handle some function magic
        self._overtaken_request = request
        request._parent_request = self
        request._dirty = True
        
        for method_name in ("acquire", "release", "test", "wait", "accept_msg", "is_dirty", "mark_dirty"):
            setattr(self, method_name, getattr(request, method_name))
            
        # Moving the topology is only a hack. We need to insert it nicer in the first place
        if not hasattr(request, "topology") and hasattr(self, "topology"):
            request.topology = self.topology
         
        request.start()   
        # There is no reason to replace the original request in the system queues as
        # we just pass on all the method calls. 
        
    def multisend(self, *args, **kwargs):
        """
        This is a very thin wrapper around the :func:`_multisend` method from the communicator. This
        wrapper will automaticly add information regarding the request id.
        """
        # Mark the request as dirty
        self.mark_dirty()
        
        # Find the extra header information useful for changing request classes on the fly.
        coll_class_id = self.__class__._coll_class_id
        kwargs["collective_header_information"] = (coll_class_id, )
        
        self.communicator._multisend(*args, **kwargs)
    
    def send(self, *args, **kwargs):
        return self.isend(*args, **kwargs).wait()
    
    def isend(self, *args, **kwargs):
        self.mark_dirty()
        
        # Find the extra header information useful for changing request classes on the fly.
        coll_class_id = self.__class__._coll_class_id

        kwargs["collective_header_information"] = (coll_class_id, )
        return self.communicator._isend(*args, **kwargs)
    
    def direct_send(self, *args, **kwargs):
        self.mark_dirty()
        
        # Find the extra header information useful for changing request classes on the fly.
        coll_class_id = self.__class__._coll_class_id

        kwargs["collective_header_information"] = (coll_class_id, )
        return self.communicator._direct_send(*args, **kwargs)
        
    
def get_accept_range(cls, settings, prefix="BINOMIAL_TREE"):
    # This method will check if there should exist
    # any settings for this particular algorithm and
    # tree type. If so these are used. If not the generic
    # limits will be inspected 
    accept_min = None
    accept_max = None
    class_prefix = getattr(cls, "SETTINGS_PREFIX", "")
    
    # Sanitise the names a bit. 
    if prefix:
        prefix = prefix.strip("_") + "_"
        
    if class_prefix:
        class_prefix = class_prefix.strip("_") + "_"
    
    accept_min = getattr(settings, class_prefix + prefix + "MIN", None)
    accept_max = getattr(settings, class_prefix + prefix + "MAX", None)

    if accept_min is None:
        accept_min = getattr(settings, prefix + "MIN", 0)
    
    if accept_max is None:
        accept_max = getattr(settings, prefix + "MAX", sys.maxint)

    return accept_min, accept_max

class FlatTreeAccepter(object):
    """
    Inherit from this class for objects that needs to accept a
    static tree. This class produces a simple accept method that
    will look into simple setting objects for accepting.
    """
    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        accept_min, accept_max = get_accept_range(cls, settings, prefix="FLAT_TREE")
        
        size = communicator.comm_group.size()
        if size >= accept_min and size <= accept_max:
            obj = cls(communicator, *args, **kwargs)
            
            # Check if the topology is in the cache.
            root = kwargs.get("root", 0) 
            cache_idx = "tree_static_%d" % root
            topology = cache.get(cache_idx, default=None)
            if not topology:
                topology = tree.FlatTree(size=communicator.size(), rank=communicator.rank(), root=root)
                cache.set(cache_idx, topology)
    
            obj.topology = topology
            return obj
 
class BinomialTreeAccepter(object):
    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        accept_min, accept_max = get_accept_range(cls, settings, prefix="BINOMIAL_TREE")

        size = communicator.comm_group.size()
        if size >= accept_min and size <= accept_max:
            obj = cls(communicator, *args, **kwargs)
            
            # Check if the topology is in the cache.
            root = kwargs.get("root", 0) 
            cache_idx = "tree_binomial_%d" % root
            topology = cache.get(cache_idx, default=None)
            if not topology:
                topology = tree.BinomialTree(size=communicator.size(), rank=communicator.rank(), root=root)
                cache.set(cache_idx, topology)
    
            obj.topology = topology
            return obj

class StaticFanoutTreeAccepter(object):
    # Fetch the fanout parameter from settings as well.
    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        accept_min, accept_max = get_accept_range(cls, settings, prefix="STATIC_FANOUT")

        size = communicator.comm_group.size()
        if size >= accept_min and size <= accept_max:
            obj = cls(communicator, *args, **kwargs)
            
            # Check if the topology is in the cache.
            root = kwargs.get("root", 0) 
            cache_idx = "tree_static_%d" % root
            topology = cache.get(cache_idx, default=None)
            if not topology:
                topology = tree.StaticFanoutTree(size=communicator.size(), rank=communicator.rank(), root=root, fanout=communicator.mpi.settings.STATIC_TREE_FANOUT_COUNT)
                cache.set(cache_idx, topology)
    
            obj.topology = topology
            return obj
