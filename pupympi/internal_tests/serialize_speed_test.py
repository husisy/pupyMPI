"""
Helper program to measure the speed of serializing and unserializing

Different serializers are timed with different datatypes

ISSUES:
- The setup could be generated a lot nicer and more programmatically
- We should test the effect of GC
"""

import time
import sys
from contextlib import contextmanager

import cPickle
import pickle
import marshal

import numpy



# sequence sizes
small = 10
smallish = 100
medium = 500
big = 1000
bigger = 2000
large = 10000


# Different objects to serialize
class A():
    def __init__(self):
        self.a = 1
        self.b = 2

d4 = ([A() for x in range(100)], "100 objects")

# Test objects and nice descriptions

i1 = (42, "small.int")
i2 = (sys.maxint, "big.int")

sl1 = (range(small), "%i;int.list" % small)

ml1 = (range(medium), "%i;int.list" % medium)
ml2 = ([ i*1.0/3.0 for i in range(medium) ], "%i;float.list" % medium)

ll1 = (range(large), "%i;int.list" % large)
ll2 = ([ i*1.0/3.0 for i in range(large) ], "%i;float.list" % large)

na1 = (numpy.array(range(small), dtype='int64'), "%i;numpy.int64" % small)
na2 = (numpy.array(range(medium), dtype='int64'), "%i;numpy.int64" % medium)
na3 = (numpy.array(range(medium),dtype='float64'), "%i;numpy.float64" % medium)
na4 = (numpy.array(range(large),dtype='int64'), "%i;numpy.int64" % large)
na5 = (numpy.array(range(large),dtype='float64'), "%i;numpy.float64" % large)

# classify objects
smalldata = [i1, i2, sl1, ml1, ml2]
bigdata = [ll1, ll2]
numpydata = [na1,na2,na3,na4,na5]

# proper repetition factors
manyreps = 1
fewreps = 1
# scale it
smalldata = [(a,b,manyreps) for (a,b) in smalldata]
bigdata = [(a,b,fewreps) for (a,b) in bigdata]

numpydata =  [(a,b,fewreps) for (a,b) in numpydata]

@contextmanager
def timing(printstr="time", repetitions=0, swallow_exception=True):
    start = time.time()
    try:
        yield
    except Exception, e:
        print "ERROR: " + str(e)
        if not swallow_exception:
            raise
    finally:
        total_time = time.time() - start
        if repetitions > 0:
            avg_time = total_time / repetitions
            print "%s;%f;%f" % (printstr, total_time, avg_time)
        else:
            print "%s: %f sec." % (printstr, total_time)


def plainrunner(r = 100, testdata=smalldata+bigdata):
    """
    Works on all types
    """
    # Serializers to try
    pickle_methods = [pickle, cPickle, marshal]
    for serializer in pickle_methods:
        for data, desc, scale in testdata:
            repetitions = r * scale
            with timing("%s;load;reps:%i;%s" % (serializer.__name__, repetitions,desc),repetitions):
                for i in xrange(repetitions):
                    s = serializer.dumps(data)
                    l = serializer.loads(s)


def numpyrunner(r = 100, testdata=numpydata):
    """
    Only works on types supporting bytearray and .tostring (ie. numpy arrays)

    NOTE: With numpy 1.5 where numpy arrays and bytearray are friends the bytearray method is tested also
    """
    # Serializers to try along with call hint and protocol version
    serializer_methods =    [
                            (pickle,'dumpload',pickle.HIGHEST_PROTOCOL),
                            (cPickle,'dumpload',cPickle.HIGHEST_PROTOCOL),
                            (marshal,'dumpload',2),
                            ('.tostring','methodcall',None),
                            ('.tostring b','methodcall',None),
                            ('.view','methodcall',None),
                            (buffer,'funcall',None)
                            ]

    # For numpy versions before 1.5 bytearray cannot take multi-byte numpy arrays so skip that method
    if numpy.__version__ >= '1.5':
        serializer_methods.append( (bytearray,'funcall',None) )

    for (serializer,syntax,version) in serializer_methods:
        for data, desc, scale in testdata:
            repetitions = r * scale
            if syntax == 'dumpload':
                with timing("%s;load;reps:%i;%s" % (serializer.__name__, repetitions,desc),repetitions):
                    for i in xrange(repetitions):
                        s = serializer.dumps(data,version)
                        l = serializer.loads(s)

            elif syntax == 'funcall':
                if type(data) == numpy.ndarray:
                    # The received data will be in the form of a string so we convert beforehand
                    s2 = data.tostring()
                    with timing("%s;frombuffer;reps:%i;%s" % (serializer.__name__, repetitions,desc),repetitions):
                        for i in xrange(repetitions):
                            t = data.dtype
                            s = serializer(data) # serialize to bytearray or buffer
                            l = numpy.frombuffer(s2,dtype=t)
                elif isinstance(data, str):
                    with timing("%s;str;reps:%i;%s" % (serializer.__name__, repetitions,desc),repetitions):
                        for i in xrange(repetitions):
                            t = type(data)
                            s = serializer(data)
                            l = t(s)
                else:
                    print "%s ignoring type %s" % (serializer.__name__, type(data))

            # This case is a bit different
            elif syntax == 'methodcall':
                if type(data) == numpy.ndarray:
                    if serializer == '.tostring':
                        with timing("%s;fromstring;reps:%i;%s" % (serializer, repetitions,desc),repetitions):
                            for i in xrange(repetitions):
                                t = data.dtype
                                s = data.tostring()
                                l = numpy.fromstring(s,dtype=t)
                    elif serializer == '.tostring b':
                        serializer_name = '.tostring'
                        with timing("%s;frombuffer;reps:%i;%s" % (serializer_name, repetitions,desc),repetitions):
                            for i in xrange(repetitions):
                                t = data.dtype
                                s = data.tostring()
                                l = numpy.frombuffer(s,dtype=t)
                    elif serializer == '.view':
                        # The received data will be in the form of a string so we convert beforehand
                        s2 = data.view(numpy.uint8).tostring()
                        with timing("%s;frombuffer;reps:%i;%s" % (serializer, repetitions,desc),repetitions):
                            for i in xrange(repetitions):
                                t = data.dtype
                                s = data.view(numpy.uint8) # serialize to view
                                l = numpy.frombuffer(s2,dtype=t)
                else:
                    print "ignoring type:%s since it has no tostring method" % type(data)

            else:
                print "syntax error!"

# do it
if __name__ == "__main__":
    import sys
    try:
        reps = int(sys.argv[1])
    except:
        reps = 1000
    #plainrunner(reps)
    #plainrunner(1000, testdata=numpydata)

    #numpyrunner(10)
    numpyrunner(reps)
    #numpyrunner(100, testdata=smalldata+bigdata)
    #numpyrunner(100, testdata=numpydata)

