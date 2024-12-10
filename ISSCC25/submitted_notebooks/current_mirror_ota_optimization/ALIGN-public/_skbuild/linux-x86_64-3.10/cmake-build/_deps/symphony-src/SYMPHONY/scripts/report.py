#!/usr/bin/python

# search for "Select columns to print"  to select columns for printing.

import array
import os
import commands
import time
import math
import sys
import string
import fileinput
import re

# ---------------------------------------------------------------------------
# IMPORTANT PARAMETERS
# ---------------------------------------------------------------------------
INST_LIST=""
OUTPUT_DIR=""
BEST_FILE=""
INFTY=1e12
ABSTOL=0.01
RELTOL=0.001

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
class Col:
	title = ""
	fmt = "%8s"
	fval = "NF"
	width = 8

	def __init__(self, title, width, fmt):
		self.title = title
		self.fmt = fmt
		self.width = width

	def extract(self):
		self.writeFail()

	def write(self, val):
		print self.fmt%val,

	def writeFail(self):
		s = "%%%ds"%self.width
		print s%"NF",

	def writeTitle(self):
		s = "%%%ds"%self.width
		print s%self.title,


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
class BBound(Col):

	val = INFTY
	def extract(self):
		self.val = INFTY
		find = -1
		lines = open(BEST_FILE).read().split('\n')
		for l in lines:
			n_v_pair = l.split()
			if (len(n_v_pair)>1 and n_v_pair[0]==instance):
				self.val = float(n_v_pair[1])
				break
		self.write(self.val)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
class EChk(Col):

	val = "NO-OUT"
	def extract(self):
		if (claims_opt.val=="ERR"):
			self.val = "NO-OUT"
			errors.append(instance)
		elif (BEST_FILE != "" and 'lb' in globals() and 'ub' in globals()):
			if (claims_opt.val=="INF" and bb.val<INFTY):
				self.val = "W-FEAS"
				errors.append(instance)
			elif (claims_opt.val=="UNB" and bb.val<INFTY):
				self.val = "W-UNB"
				errors.append(instance)
			elif (lb.val-bb.val > ABSTOL and
					(lb.val-bb.val)/(abs(bb.val)+1e-6) > RELTOL):
				self.val = "W-LB"
				errors.append(instance)
			elif (bb.val-ub.val > ABSTOL and
					(bb.val-ub.val)/(abs(bb.val)+1e-6) > RELTOL):
				self.val = "NEWSOL"
				errors.append(instance)
			elif (bb.val >= INFTY and ub.val < INFTY):
				self.val = "NEWSOL"
				errors.append(instance)
			else:
				self.val = "OK"
		else:
			self.val = "OK"
		self.write(self.val)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
class LBound(Col):

	val = INFTY
	def extract(self):
		self.val = INFTY
		if (claims_opt.val=="OPT"):
			self.val = ub.val
			if (self.val==INFTY):
				self.writeFail()
			else:
				self.write(self.val)
		else:
			val = INFTY
			find,val=find_float(outfile,'Current Lower Bound',val)
			if (find<0 or val >= INFTY):
				self.writeFail()
				self.val = INFTY
			else:
				self.write(val)
				self.val = val
			


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
class Nodes(Col):

	val = INFTY
	def extract(self):
		val = INFTY
		find,val=find_int(outfile,'Number of analyzed nodes',
				val)
		if (find<0 or val >= INFTY):
			self.val = INFTY
			self.writeFail()
		else:
			self.val = val
			self.write(self.val)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
class Status(Col):

	val = "ERR"
	def extract(self):
		self.val = "ERR"
		find = find_str(outfile,'Optimal Solution Found')
		if (find>0):
			self.val = "OPT"
		else:
			find = find_str(outfile,'Problem Infeasible')
			if (find>0):
				self.val = "INF"
			else:
				find = find_str(outfile,'Relaxation Unbounded')
				if (find>0):
					self.val = "UNB"
				else:
					find = find_str(outfile,'Now displaying stats')
					if (find>0):
						self.val = "LIM"
						unsolved.append(instance)
		self.write(self.val)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
class UBound(Col):

	val = INFTY
	def extract(self):
		self.val = INFTY
		val = INFTY
		if (claims_opt.val=="OPT"):
			val = INFTY
			find,val=find_float(outfile,'Solution Cost:',val)
			if (find<0 or val >= INFTY):
				self.writeFail()
				self.val = INFTY
			else:
				self.write(val)
				self.val = val
		else:
			val = INFTY
			find,val=find_float(outfile,'Current Upper Bound',val)
			if (find<0 or val >= INFTY):
				self.writeFail()
				self.val = INFTY
			else:
				self.write(val)
				self.val = val


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
class WallTime(Col):

	def extract(self):
		val = INFTY
		find,val=find_float(outfile,'Total Wallclock Time',val)
		if (find<0 or val >= INFTY):
			val = -1.0
		self.write(val)
			



# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def find_str(arr0,st0):
	for line in arr0:
		find = re.search(st0,line)
		if (find >= 0):
			return 1
	return 0

def find_float(arr0,st0,fl0):
	for line in arr0:
		find = re.search(st0,line)
		if (find >= 0):
			fl0 = float(re.search('-*[0-9]+\.[0-9]+',line).group())
			return 1,fl0
	return -1,fl0

def find_float_1(arr0,st0,fl0):
	st0 = st0+" "
	for line in arr0:
		find = re.search(st0,line)
		if (find >= 0):
			find = re.search('-*[0-9]+\.[0-9]+',line)
			if (find>=0):
				l = re.findall('-*[0-9]+\.[0-9]+',line)
				if (len(l)<1):
					return -1,fl0
				else:
					fl0 = float(l[len(l)-1])
					return 1,fl0
			else:
				return -1,fl0
	return -1,fl0

def find_float_e(arr0,st0,fl0):
	for line in arr0:
		find = re.search(st0,line)
		if (find >= 0):
			fl0 = float(re.search('-*[0-9]+\.[0-9]*e*\+*[0-9]*',line).group())
			return 1,fl0
	return -1,fl0

def find_int(arr0,st0,in0):
	in0=0
	for line in arr0:
		find = re.search(st0,line)
		if (find >= 0):
			in0 = int(re.search('-*[0-9]+$',line).group())
			return 1,in0
	return -1,in0

def print_usage():
	print "usage: python report.py -l <file containing instance names>", 
	print "-d <path to dir> [-b <file containing best upper bound>]"

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

if (len(sys.argv)<2):
	print_usage()
	sys.exit(0)

i = 1
while(i<len(sys.argv)):
	if (sys.argv[i]=='-d'):
		if (i==len(sys.argv)-1):
			print "Missing argument to '-d'"
			print_usage()
			sys.exit(0)
		else:
			OUTPUT_DIR=sys.argv[i+1]
			if (os.path.exists(OUTPUT_DIR)):
				print "### Reading output files from directory:", OUTPUT_DIR
				i = i+1
			else:
				print "the specified directory %s is not accessible"%OUTPUT_DIR
				print_usage()
				sys.exit(0)
	elif (sys.argv[i]=='-l'):
		if (i==len(sys.argv)-1):
			print "Missing argument to '-l'"
			print_usage()
			sys.exit(0)
		else:
			INST_LIST=sys.argv[i+1]
			print "### Instances listed in :", INST_LIST
			i = i+1
	elif (sys.argv[i]=='-b'):
		if (i==len(sys.argv)-1):
			print "Missing argument to '-b'"
			print_usage()
			sys.exit(0)
		else:
			BEST_FILE=sys.argv[i+1]
			print "### Best upper bounds listed in :", BEST_FILE
			i = i+1
	else:
		print "invalid option: %s"%sys.argv[i]
		print_usage()
		sys.exit(0)
	i = i+1
		
if (OUTPUT_DIR==""):
	print_usage()
	sys.exit(0)

if (INST_LIST==""):
	print_usage()
	sys.exit(0)


instCol=Col("######### instance", 18, "%18s")

othercols=[]
errors=[]
unsolved=[]

ins_list=[]
flist=open(INST_LIST,'r')
ins_list=flist.read().split()
flist.close()

#############################################################################
# Mandatory columns #########################################################
#############################################################################

wtime = WallTime("time", 10, "%10.2f")
othercols.append(wtime)
claims_opt = Status("opt", 4, "%4s")
othercols.append(claims_opt)


#############################################################################
# Select columns to print ###################################################
#############################################################################

othercols.append(Nodes("nodes", 8, "%8d"))
ub = UBound("ub", 18, "%18.4f")
othercols.append(ub)
lb = LBound("lb", 18, "%18.4f")
othercols.append(lb)

if (BEST_FILE is not ""):
	bb = BBound("best-ub", 18, "%18.4f")
	othercols.append(bb)


othercols.append(EChk("err", 8, "%8s"))

#############################################################################
# End of 'columns to print' #################################################
#############################################################################

instCol.writeTitle()
for c in othercols:
	c.writeTitle()

print

for instance in ins_list:
	instCol.write(instance)

	filename=OUTPUT_DIR+"/"+instance+".out"
	try:
		fil=open(filename,'r')
		outfile=fil.read().split('\n')
		fil.close()
	except IOError:
		errors.append(instance)
		for c in othercols:
			c.writeFail()
		print
		continue

	for c in othercols:
		c.extract()
	
	print

print "### Number of instances = ", len(ins_list)
print "### Number of errors    = ", len(errors)
print "### Number of unsolved  = ", len(unsolved)

print "###"
print "### errors: " 
for iter in errors:
	print "###    ", iter

print "###"
print "### unsolved: " 
for iter in unsolved:
	print "###    ", iter


