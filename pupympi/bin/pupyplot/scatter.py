#!/usr/bin/env python
# Copyright 2010 Rune Bromer, Asser Schroeder Femoe, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
#
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.

import sys, os, glob

pupyplotpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
binpath = os.path.dirname(os.path.abspath(pupyplotpath))
mpipath = os.path.dirname(os.path.abspath(binpath))

sys.path.append(mpipath)
sys.path.append(pupyplotpath)
sys.path.append(binpath)

from mpi import constants
from mpi.logger import Logger

from pupyplot.lib.cmdargs import plot_parser, parse
from pupyplot.lib.tagmapper import get_tag_mapping
from pupyplot.parser.handle import Handle, DataSupplier
from pupyplot.gnuplot import ScatterPlot

# This is more generic than a simple line plot. It should be moved. 
FORMAT_CHOICES = {
    'datasize' : 'datasize',
    'total_time'  :'time',
    'avg_time'  : 'time',
    'min_time' : 'time',
    'max_time' : 'time',
    'throughput' :'throughput',
    'nodes' : 'number',
}

if __name__ == "__main__":
    # Receive the parser and groups so we can add further elements 
    # if we want
    parser, groups = plot_parser()
    
    # Parse it. This will setup logging and other things.    
    options, args = parse(parser)
    
    Logger().debug("Command line arguments parsed.")
    
    # Object creation, used to keep, filter, aggregate, validate data.
    handle = Handle(args[0])
    
    tag_mapper = {}
    if options.tag_mapper:
        tag_mapper = get_tag_mapping(options.tag_mapper)
    
    # to extract and filter the data.
    ds = DataSupplier(handle.getdata())
    
    # It should be possible to limit the tests to one single test. how should
    # this be one. 
    all_tests = ds.get_tests()
    for testname in all_tests:
        # Write nice labels
        from pupyplot.lib.cmdargs import DATA_CHOICES
        xlabel = DATA_CHOICES[options.x_data]
        ylabel = DATA_CHOICES[options.y_data]
        
        # Format the axis. 
        axis_x_format = FORMAT_CHOICES[options.x_data]
        axis_y_format = FORMAT_CHOICES[options.y_data]
        
        tags = ds.get_tags()
        
        sp = ScatterPlot(testname, title=testname, xlabel=xlabel, ylabel=ylabel, keep_temp_files=options.keep_temp, axis_x_type=options.axis_x_type, axis_y_type=options.axis_y_type, axis_x_format=axis_x_format, axis_y_format=axis_y_format)
        
        for tag in tags:
            # Extract the data from the data store.
            xdata, ydata = ds.getdata(testname, tag, options.x_data, options.y_data, filters=[])
            
            title = tag_mapper.get(tag, tag)
            sp.add_serie(xdata, ydata, title=title)
                    
        sp.plot()
        sp.close()