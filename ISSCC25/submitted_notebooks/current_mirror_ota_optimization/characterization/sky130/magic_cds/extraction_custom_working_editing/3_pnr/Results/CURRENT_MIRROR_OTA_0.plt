#Use this file as a script for gnuplot
#(See http://www.gnuplot.info/ for details)

set title" #Blocks= 5, #Terminals= 4, #Nets= 8,Area=5.17816e+09, HPWL= 417820 "

set nokey
#   Uncomment these two lines starting with "set"
#   to save an EPS file for inclusion into a latex document
# set terminal postscript eps color solid 20
# set output "result.eps"

#   Uncomment these two lines starting with "set"
#   to save a PS file for printing
# set terminal postscript portrait color solid 20
# set output "result.ps"


set xrange [-50:96370]

set yrange [-50:53810]

set label "X_M10_M9" at 20640 , 7560 center 

set label "DA" at 19780 , 10080


set label "DB" at 21500 , 13440


set label "S" at 21500 , 7140


set label "X_M3_M8" at 55040 , 34440 center 

set label "DA" at 55900 , 31920


set label "DB" at 55040 , 28560


set label "S" at 54180 , 34860


set label "X_M4_M7" at 82560 , 34440 center 

set label "DA" at 81700 , 31920


set label "DB" at 82560 , 28560


set label "S" at 83420 , 34860


set label "X_M5_M6" at 20640 , 22680 center 

set label "B" at 20640 , 28560


set label "DA" at 19780 , 20160


set label "DB" at 21500 , 16800


set label "S" at 20640 , 17640


set label "X_M1_M2" at 68800 , 7560 center 

set label "B" at 68800 , 1680


set label "DA" at 67940 , 14280


set label "DB" at 69660 , 13440


set label "GA" at 67940 , 5880


set label "GB" at 69660 , 5040


set label "S" at 68800 , 12600


set label "ID" at 19780 , 0 center                

set label "VOUT" at 21500 , 0 center                

set label "VINN" at 67940 , 0 center                

set label "VINP" at 69660 , 0 center                

plot[:][:] '-' with lines linestyle 3, '-' with lines linestyle 7, '-' with lines linestyle 1, '-' with lines linestyle 0

# block X_M10_M9 select 0 bsize 4
	6880	0
	6880	15120
	34400	15120
	34400	0
	6880	0

# block X_M3_M8 select 0 bsize 4
	41280	15120
	41280	53760
	68800	53760
	68800	15120
	41280	15120

# block X_M4_M7 select 0 bsize 4
	68800	15120
	68800	53760
	96320	53760
	96320	15120
	68800	15120

# block X_M5_M6 select 0 bsize 4
	0	15120
	0	30240
	41280	30240
	41280	15120
	0	15120

# block X_M1_M2 select 0 bsize 4
	55040	0
	55040	15120
	82560	15120
	82560	0
	55040	0


EOF
	19500	14600
	19500	5560
	20060	5560
	20060	14600
	19500	14600

	10840	13720
	10840	13160
	32160	13160
	32160	13720
	10840	13720

	21220	12920
	21220	1360
	21780	1360
	21780	12920
	21220	12920

	56180	15640
	56180	48200
	55620	48200
	55620	15640
	56180	15640

	55320	16480
	55320	40640
	54760	40640
	54760	16480
	55320	16480

	54460	17320
	54460	52400
	53900	52400
	53900	17320
	54460	17320

	81420	15640
	81420	48200
	81980	48200
	81980	15640
	81420	15640

	82280	16480
	82280	40640
	82840	40640
	82840	16480
	82280	16480

	83140	17320
	83140	52400
	83700	52400
	83700	17320
	83140	17320

	2240	28280
	2240	28840
	39040	28840
	39040	28280
	2240	28280

	19500	15640
	19500	24680
	20060	24680
	20060	15640
	19500	15640

	3960	16520
	3960	17080
	39040	17080
	39040	16520
	3960	16520

	1380	17360
	1380	17920
	39900	17920
	39900	17360
	1380	17360

	57280	1960
	57280	1400
	80320	1400
	80320	1960
	57280	1960

	57280	14560
	57280	14000
	78600	14000
	78600	14560
	57280	14560

	59000	13720
	59000	13160
	80320	13160
	80320	13720
	59000	13720

	57280	6160
	57280	5600
	78600	5600
	78600	6160
	57280	6160

	59000	5320
	59000	4760
	80320	4760
	80320	5320
	59000	5320

	56420	12880
	56420	12320
	81180	12320
	81180	12880
	56420	12880


EOF

	19780	0
	19780	0
	19780	0
	19780	0
	19780	0

	21500	0
	21500	0
	21500	0
	21500	0
	21500	0

	67940	0
	67940	0
	67940	0
	67940	0
	67940	0

	69660	0
	69660	0
	69660	0
	69660	0
	69660	0

EOF

#Net: ID
	19780	10080
	19780	0
	19780	10080


#Net: SOURCE
	21500	13440
	20640	17640
	21500	13440

	21500	13440
	68800	12600
	21500	13440


#Net: NET7
	55900	31920
	67940	14280
	55900	31920


#Net: VOUT
	55040	28560
	21500	16800
	55040	28560

	55040	28560
	21500	0
	55040	28560


#Net: NET8
	81700	31920
	69660	13440
	81700	31920


#Net: NET9
	82560	28560
	19780	20160
	82560	28560


#Net: VINN
	67940	5880
	67940	0
	67940	5880


#Net: VINP
	69660	5040
	69660	0
	69660	5040


EOF

pause -1 'Press any key'