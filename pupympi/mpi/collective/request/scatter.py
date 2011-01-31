from mpi.collective.request import BaseCollectiveRequest
from mpi import constants
from mpi import settings

from mpi.logger import Logger

from mpi.topology import tree

class TreeScatter(BaseCollectiveRequest):
    """
    This is a generic broadcast request using different tree structures. It is
    simple to use this as it is a matter of extending, adding the wanted
    topology tree and then implementing the accept() class method. See the below
    defined classes for examples.

    The functionality is also pretty simple. Each request looks at the parent
    in the topology. If there is none, we must be the root, so we sends data
    to each child. If - on the other hand - there is a parent, we wait for
    a message from that rank and send to our own children.
    """
    def __init__(self, communicator, data=None, root=0):
        super(TreeScatter, self).__init__()

        self.data = data
        self.root = root
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        # Slice the data.
        if self.root == self.rank:
            chunk_size = len(data) / self.size
            self.data = [data[r*chunk_size:(r+1)*chunk_size] for r in range(self.size) ]

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant broadcast without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        if self.parent is None:
            # we're the root.. let us send the data to each child
            self.send_to_children()

    def accept_msg(self, rank, data):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if rank == self.parent:
            self.data = data
            self.send_to_children()
            return True

        return False

    def send_to_children(self):
        for child in self.children:
            # Create new data. This will not include a lot of data copies
            # as we are only making references in the new list.
            data = [None] * self.size
            desc = self.topology.descendants()
            for r in range(self.size):
                if r == child or r in desc[child]:
                    data[r] = self.data[r]
                else:
                    data[r] = None
            self.communicator._isend(self.data, child, tag=constants.TAG_SCATTER)

        # We only need our own data
        self.data = self.data[self.rank]

        self._finished.set()

    def _get_data(self):
        return self.data

class FlatTreeScatter(TreeScatter):
    """
    Performs a flat tree broadcast (root sends to all other). This algorithm
    should only be performed when the size is 10 or smaller.
    """
    @classmethod
    def accept(cls, communicator, *args, **kwargs):

        size = communicator.comm_group.size()
        if size >= settings.FLAT_TREE_MIN and size <= settings.FLAT_TREE_MAX:
            obj = cls(communicator, *args, **kwargs)

            topology = tree.FlatTree(communicator, root=kwargs['root'])

            # Insert the toplogy as a smart trick
            obj.topology = topology

            return obj

class BinomialTreeScatter(TreeScatter):
    @classmethod
    def accept(cls, communicator, *args, **kwargs):

        size = communicator.comm_group.size()

        if size >= settings.BINOMIAL_TREE_MIN and size <= settings.BINOMIAL_TREE_MAX:
            obj = cls(communicator, *args, **kwargs)

            topology = tree.BinomialTree(communicator, root=kwargs['root'])

            # Insert the toplogy as a smart trick
            obj.topology = topology

            return obj

class StaticFanoutTreeScatter(TreeScatter):
    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        if size >= settings.STATIC_FANOUT_MIN and size <= settings.STATIC_FANOUT_MAX:
            obj = cls(communicator, *args, **kwargs)
    
            topology = tree.BinomialTree(communicator, root=kwargs['root'])
    
            # Insert the toplogy as a smart trick
            obj.topology = topology
    
            return obj
