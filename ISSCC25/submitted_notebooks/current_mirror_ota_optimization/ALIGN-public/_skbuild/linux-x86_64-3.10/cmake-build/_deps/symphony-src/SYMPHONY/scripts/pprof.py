#!/usr/bin/env python
#
# pprof.py, v0.5: Create performance profiles.
# Written by Michael P. Friedlander <michael@mcs.anl.gov>
#
# $Revision: 1.11 $ $Date: 2003-04-24 12:11:21-05 $
#
# I'm still learning Python, so bear with me!
#
# changed by asm4@lehigh.edu
# im also learning ;-)
# added two new options (--x-limit and --max-limit), changed import from MA to
# numpy.ma
# last change: 2009-01-02
# last change: 2010-08-18
import getopt, sys, re
from   string import atoi, atof

try:
   import numpy.ma as ma
except ImportError:
   try:
      import numpy.core.ma as ma
   except ImportError:
      print "numpy.ma not found. Install numpy and add to python-path"
      raise ImportError
import Gnuplot, Gnuplot.funcutils

#import numpy.core.ma as ma
#from   Numeric import *

PROGNAME = "pprof.py"

def usage():
    instructions = """
Usage: %s [OPTION]... [FILE 1] [FILE 2]...[FILE N]
Create a performance profile chart from metrics in FILEs.
Output is an eps file sent to stdout.

Example 1:
  Profile the metrics in column 3 of the files solver1, solver2, and solver3.
  Use a log2 scale for the x-axis.  Redirect the stdout to profile.eps.
  
    %s -l 2 -c 3 solver1 solver2 solver3 > profile.eps

Example 2:
  Specify a title, linestyle and failure threshold.  Pop up an X window.

    %s -c 3 -t "Plot title" --linestyle "linespoints" \\
             --term "x11" solver1 solver2 solver3

See Dolan and More',
   "Benchmarking optimization software with performance profiles",
   available at http://www-unix.mcs.anl.gov/~more/cops/

Options
  -c, --column=COLUMN      get metrics from column COLUMN (default 1)
  -h, --help               get some help
  -l, --log=BASE           logBASE scale for x-axis (default linear)
      --legend             insert a legend
      --linestyle=STYLE    use STYLE as Gnuplot line style (default steps)
      --sep RE             use regexp RE to indicate new column (default space)
      --term=TERM          use TERM  Gnuplot terminal (default postscript)
  -t, --title=LABEL        use LABEL as  title  (default none)
  -x, --xlabel=LABEL       use LABEL for x-axis (default none)
  -y, --ylabel=LABEL       use LABEL for y-axis (default none)
      --max-limit=value    use value above which the problem is deemed
                           unsolved
      --min-limit=value    If all solvers solved instance in time <= value,
			   their times are all set to value.
      --x-limit=value      maximum length of x-axis. if this length is longer
                           than the length required by default, then this is 
                           ignored.

- Use non-positive values to indicate that the algorithm failed.
- Use --sep 'S' to indicate columns are separated by character S.
- Use --sep "r'RE'" to separate instead by a regular expression.
- Any line starting with a %% or a # is ignored.
""" % (PROGNAME,PROGNAME,PROGNAME)

    print instructions
    sys.exit(0)
    

def commandline_err(msg):
    sys.stderr.write("%s: %s\n" % (PROGNAME, msg))
    sys.stderr.write("Try '%s --help' for more information.\n" % PROGNAME)
    sys.exit(1)


class OptionClass:

    def __init__(self):
	self.datacol  = 1
	self.legend   = None
        self.linestyl = 'steps lw 4'
	self.logscale = None
	self.sep      = '\s+'
        # The GnuPlot postscript driver seems most sophisticated.
        # Also, probably the easiest format for LaTeX to deal with.
	self.term     = 'postscript landscape color solid'
	# asm4:
	#self.term     = 'postscript landscape dashed'
	self.title    = None
	self.xlabel   = None
	self.ylabel   = None
	self.maxlimit = 1e50
	self.minlimit = 0.0
	self.xlimit   = 1e50
	self.minpos   = 1e-6 #all zeros are replaced by this minimum positive value


def parse_cmdline(arglist):
    """Parse argument list"""

    if len(arglist) == 0: usage()

    options = OptionClass()
    
    try: optlist, files = getopt.getopt(arglist, 'hl:c:x:y:t:',
					["column=", "help",
                                        "legend", "linestyle=",
                                        "sep=",
                                        "log=", "term=", "title=",
					 "xlabel=", "ylabel=", "max-limit=",
					 "min-limit=", "x-limit="
                                         ])
    except getopt.error, e:
        commandline_err("%s" % str(e))

    if len(files) < 2: usage()

    for opt, arg in optlist:
        if   opt in ("-c", "--column"): options.datacol  = atoi(arg)
        elif opt in ("-h",   "--help"): usage()
	elif opt ==     "--linestyle" : options.linestl  = arg
	elif opt ==        "--legend" : options.legend   = 1
        elif opt in ("-l",    "--log"): options.logscale = atof(arg)
	elif opt ==           "--sep" : options.sep      = arg
	elif opt ==          "--term" : options.term     = arg
	elif opt in ("-t",  "--title"): options.title    = arg
	elif opt in ("-x", "--xlabel"): options.xlabel   = arg
	elif opt in ("-y", "--ylabel"): options.ylabel   = arg
	elif opt == "--max-limit":      options.maxlimit = atof(arg)
	elif opt == "--min-limit":      options.minlimit = atof(arg)
	elif opt == "--x-limit":        options.xlimit   = atof(arg)

    return (options, files)


class MetricsClass:

    def __init__(self, solvers, opts):
        self.metric  = None
        self.nprobs  = []
        self.perf    = []
        self.solvers = solvers
        self.nsolvs  = len(solvers)
        self.sep     = opts.sep

        map(self.add_solver, solvers)

    def add_solver(self, fname):

        # Reg exp: Any line starting (ignoring white-space)
        # starting with a comment character. Also col sep.
        comment = re.compile(r'^[\s]*[%#]')
        column  = re.compile(self.sep)

        # Grab the column from the file
        metrics = []
        file = open(fname, 'r')
        for line in file.readlines():
            if not comment.match(line):
                line = line.strip()
                cols = column.split( line )
                data = atof(cols[opts.datacol - 1])
		metrics.append(data)
        file.close()

        if self.metric is not None:
	    self.metric = ma.concatenate((self.metric, [metrics]))	    
        else: 
            self.metric = ma.array([metrics])

        # Current num of probs grabbed
        nprobs = len(metrics)
        if not self.nprobs: self.nprobs = nprobs
        elif self.nprobs <> nprobs:
            commandline_error("All files must have same num of problems.")
            
    def prob_mets(self, prob):
       for i in range(0,len(self.metric[:,prob])):
          if (self.metric[i,prob]>=0.0 and self.metric[i,prob]<opts.minpos):
             self.metric[i,prob] = opts.minpos
       return ma.masked_outside(self.metric[:,prob], 0, opts.maxlimit)


class RatioClass:

    def __init__(self, MetricTable):

        # Create empty ratio table
        nprobs = MetricTable.nprobs
        nsolvs = MetricTable.nsolvs
        self.ratios = ma.masked_array(1.0 * ma.zeros((nprobs+1, nsolvs)))

        # Compute best relative performance ratios across
        # solvers for each problem
        for prob in range(nprobs):
            metrics  = MetricTable.prob_mets(prob)
            best_met = ma.minimum(metrics)
	    if (ma.count(metrics)==nsolvs and
                ma.maximum(metrics)<=opts.minlimit):
                self.ratios[prob+1,:] = 1.0;
	    else:
                self.ratios[prob+1,:] = metrics * (1.0 / best_met)

        # Sort each solvers performance ratios
        for solv in range(nsolvs):
            self.ratios[:,solv] = ma.sort(self.ratios[:,solv])

        # Compute largest ratio and use to replace failures entries
        self.maxrat = ma.maximum(self.ratios)
        self.ratios = ma.filled(self.ratios, 1.01 * self.maxrat)

    def solv_ratios(self, solver):
        return self.ratios[:,s]


################
# Main program #
################

opts, solvers = parse_cmdline(sys.argv[1:]) 

metrics = MetricsClass(solvers, opts)
pprofs  = RatioClass(metrics)

nprobs = metrics.nprobs
nsolvs = metrics.nsolvs

# Create a performance profile graph
persist_val = ( opts.term in ('X11', 'x11') )
g = Gnuplot.Gnuplot(persist=persist_val, debug=0)

# Generate the x-axis data
ydata = ma.arange(nprobs+1) * (1.0 / nprobs)

# Set the x-axis ranges
maxrat = pprofs.maxrat + 1.0e-3
if opts.logscale:
    g('set logscale x %f' % opts.logscale)
    minrat = 1
else:
    minrat = 0

# asm4:
if opts.xlimit < maxrat:
	maxrat = opts.xlimit
g('set xrange [%f:%f]' % (minrat, maxrat / 1.00))

# The y-axis range is fixed
g('set yrange [0:1]')

# asm4: make the whole picture smaller so that the font appears larger.
g('set size 0.8,0.8')

# Set graph properties
if opts.legend:
    g('set key bottom right')
else:
    g('set nokey')
if opts.term:
    g('set term ' + opts.term)
if opts.title:
    g.title(opts.title)
if opts.xlabel:
    g.xlabel(opts.xlabel)
if opts.ylabel:
    g.ylabel(opts.ylabel)

# Generate arguments for the gplot command
plotargs = []
for s in range(nsolvs):
    sname = solvers[s]
    srats = pprofs.solv_ratios(s)
    plotargs.append(Gnuplot.Data(srats, ydata, title=sname, inline=0,
                                 with_=opts.linestyl))

# Create the plot
apply(g.plot, plotargs)

# This fixes a Gnuplot bug. (Thanks to Matt Knepley.)
g.gnuplot.gnuplot.close()
