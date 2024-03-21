* Functional test stimulus file for 10ns period

* TT process corner
.lib "/tmp/OpenRAM/sky130A/libs.tech/ngspice/sky130.lib.spice" tt
.include "myconfig.sp"

* Global Power Supplies
Vvdd vdd 0 1.8

*Nodes gnd and 0 are the same global ground node in ngspice/hspice/xa. Otherwise, this source may be needed.
*Vgnd gnd 0 0.0

* Instantiation of the SRAM
Xmyconfig din0_0 din0_1 din0_2 din0_3 din0_4 din0_5 din0_6 din0_7 din1_0 din1_1 din1_2 din1_3 din1_4 din1_5 din1_6 din1_7 a0_0 a0_1 a0_2 a0_3 a0_4 a0_5 a1_0 a1_1 a1_2 a1_3 a1_4 a1_5 CSB0 CSB1 WEB0 WEB1 clk0 clk1 dout0_0 dout0_1 dout0_2 dout0_3 dout0_4 dout0_5 dout0_6 dout0_7 dout1_0 dout1_1 dout1_2 dout1_3 dout1_4 dout1_5 dout1_6 dout1_7 vdd gnd myconfig

* SRAM output loads
CD00 dout0_0  0 27.56f
CD01 dout0_1  0 27.56f
CD02 dout0_2  0 27.56f
CD03 dout0_3  0 27.56f
CD04 dout0_4  0 27.56f
CD05 dout0_5  0 27.56f
CD06 dout0_6  0 27.56f
CD07 dout0_7  0 27.56f
CD10 dout1_0  0 27.56f
CD11 dout1_1  0 27.56f
CD12 dout1_2  0 27.56f
CD13 dout1_3  0 27.56f
CD14 dout1_4  0 27.56f
CD15 dout1_5  0 27.56f
CD16 dout1_6  0 27.56f
CD17 dout1_7  0 27.56f


* Important signals for debug
* bl:	xmyconfig.xbank0.bl_0_0
* br:	xmyconfig.xbank0.br_0_0
* s_en:	xmyconfig.s_en
* q:	xmyconfig.xbank0.xbitcell_array.xreplica_bitcell_array.xbitcell_array.xbit_r0_c0.Q
* qbar:	xmyconfig.xbank0.xbitcell_array.xreplica_bitcell_array.xbitcell_array.xbit_r0_c0.Q_bar


* Sequence of operations
*	Idle during cycle 0 (0ns - 10ns)
*	Writing 01110111  to  address 000001 (from port 0) during cycle 1 (10ns - 20ns)
*	Writing 10011010  to  address 000000 (from port 1) during cycle 1 (10ns - 20ns)
*	Writing 10111111  to  address 000000 (from port 0) during cycle 2 (20ns - 30ns)
*	Writing 11110111  to  address 000001 (from port 1) during cycle 2 (20ns - 30ns)
*	Writing 01110110  to  address 111110 (from port 0) during cycle 3 (30ns - 40ns)
*	Writing 00110111  to  address 000000 (from port 1) during cycle 3 (30ns - 40ns)
*	Reading 00110111 from address 000000 (from port 0) during cycle 4 (40ns - 50ns)
*	Reading 11110111 from address 000001 (from port 1) during cycle 4 (40ns - 50ns)
*	Reading 00110111 from address 000000 (from port 0) during cycle 5 (50ns - 60ns)
*	Writing 01001001  to  address 000001 (from port 1) during cycle 5 (50ns - 60ns)
*	Writing 00001100  to  address 111110 (from port 1) during cycle 6 (60ns - 70ns)
*	Reading 01001001 from address 000001 (from port 0) during cycle 7 (70ns - 80ns)
*	Reading 01001001 from address 000001 (from port 1) during cycle 7 (70ns - 80ns)
*	Reading 01001001 from address 000001 (from port 0) during cycle 9 (90ns - 100ns)
*	Writing 01111001  to  address 111110 (from port 0) during cycle 10 (100ns - 110ns)
*	Writing 11101111  to  address 111101 (from port 0) during cycle 11 (110ns - 120ns)
*	Writing 10010111  to  address 000001 (from port 1) during cycle 11 (110ns - 120ns)
*	Reading 11101111 from address 111101 (from port 1) during cycle 12 (120ns - 130ns)
*	Reading 00110111 from address 000000 (from port 0) during cycle 13 (130ns - 140ns)
*	Writing 11000000  to  address 000000 (from port 1) during cycle 13 (130ns - 140ns)
*	Reading 10010111 from address 000001 (from port 1) during cycle 14 (140ns - 150ns)
*	Reading 01111001 from address 111110 (from port 1) during cycle 15 (150ns - 160ns)
*	Reading 10010111 from address 000001 (from port 1) during cycle 16 (160ns - 170ns)
*	Reading 01111001 from address 111110 (from port 0) during cycle 18 (180ns - 190ns)
*	Writing 10100110  to  address 111101 (from port 0) during cycle 19 (190ns - 200ns)
*	Reading 11000000 from address 000000 (from port 1) during cycle 20 (200ns - 210ns)
*	Reading 10010111 from address 000001 (from port 0) during cycle 21 (210ns - 220ns)
*	Reading 10010111 from address 000001 (from port 1) during cycle 21 (210ns - 220ns)
*	Reading 11000000 from address 000000 (from port 0) during cycle 22 (220ns - 230ns)
*	Writing 11101011  to  address 000001 (from port 1) during cycle 22 (220ns - 230ns)
*	Reading 11101011 from address 000001 (from port 0) during cycle 23 (230ns - 240ns)
*	Writing 10100011  to  address 111110 (from port 0) during cycle 24 (240ns - 250ns)
*	Reading 10100011 from address 111110 (from port 1) during cycle 25 (250ns - 260ns)
*	Reading 10100110 from address 111101 (from port 1) during cycle 26 (260ns - 270ns)
*	Writing 10110001  to  address 111110 (from port 0) during cycle 27 (270ns - 280ns)
*	Reading 10100110 from address 111101 (from port 1) during cycle 27 (270ns - 280ns)
*	Reading 11000000 from address 000000 (from port 1) during cycle 28 (280ns - 290ns)
*	Reading 11000000 from address 000000 (from port 0) during cycle 30 (300ns - 310ns)
*	Writing 01101101  to  address 000001 (from port 1) during cycle 31 (310ns - 320ns)
*	Reading 11000000 from address 000000 (from port 1) during cycle 32 (320ns - 330ns)
*	Reading 10100110 from address 111101 (from port 0) during cycle 33 (330ns - 340ns)
*	Reading 10100110 from address 111101 (from port 0) during cycle 34 (340ns - 350ns)
*	Reading 10110001 from address 111110 (from port 1) during cycle 34 (340ns - 350ns)
*	Reading 10100110 from address 111101 (from port 0) during cycle 35 (350ns - 360ns)
*	Reading 10100110 from address 111101 (from port 1) during cycle 35 (350ns - 360ns)
*	Writing 01011100  to  address 111110 (from port 1) during cycle 36 (360ns - 370ns)
*	Writing 00000100  to  address 000001 (from port 0) during cycle 37 (370ns - 380ns)
*	Writing 11001101  to  address 111101 (from port 1) during cycle 37 (370ns - 380ns)
*	Reading 11001101 from address 111101 (from port 0) during cycle 38 (380ns - 390ns)
*	Writing 00100110  to  address 000000 (from port 0) during cycle 39 (390ns - 400ns)
*	Reading 00100110 from address 000000 (from port 0) during cycle 40 (400ns - 410ns)
*	Reading 11001101 from address 111101 (from port 1) during cycle 40 (400ns - 410ns)
*	Reading 00000100 from address 000001 (from port 0) during cycle 41 (410ns - 420ns)
*	Reading 01011100 from address 111110 (from port 1) during cycle 41 (410ns - 420ns)
*	Writing 10010011  to  address 000000 (from port 0) during cycle 42 (420ns - 430ns)
*	Reading 10010011 from address 000000 (from port 0) during cycle 43 (430ns - 440ns)
*	Writing 00000101  to  address 111110 (from port 1) during cycle 43 (430ns - 440ns)
*	Writing 11100110  to  address 000000 (from port 0) during cycle 44 (440ns - 450ns)
*	Writing 11101100  to  address 111110 (from port 1) during cycle 44 (440ns - 450ns)
*	Writing 00100100  to  address 000000 (from port 0) during cycle 45 (450ns - 460ns)
*	Reading 00000100 from address 000001 (from port 1) during cycle 45 (450ns - 460ns)
*	Reading 11001101 from address 111101 (from port 0) during cycle 46 (460ns - 470ns)
*	Writing 10101110  to  address 111101 (from port 1) during cycle 46 (460ns - 470ns)
*	Reading 10101110 from address 111101 (from port 1) during cycle 47 (470ns - 480ns)
*	Reading 00000100 from address 000001 (from port 0) during cycle 48 (480ns - 490ns)
*	Writing 10111100  to  address 111101 (from port 1) during cycle 48 (480ns - 490ns)
*	Reading 10111100 from address 111101 (from port 1) during cycle 49 (490ns - 500ns)
*	Reading 00100100 from address 000000 (from port 1) during cycle 50 (500ns - 510ns)
*	Reading 00100100 from address 000000 (from port 1) during cycle 51 (510ns - 520ns)
*	Writing 10001100  to  address 000000 (from port 0) during cycle 52 (520ns - 530ns)
*	Writing 11101010  to  address 000001 (from port 1) during cycle 52 (520ns - 530ns)
*	Writing 11111110  to  address 111110 (from port 0) during cycle 53 (530ns - 540ns)
*	Writing 11010010  to  address 111110 (from port 0) during cycle 54 (540ns - 550ns)
*	Reading 11010010 from address 111110 (from port 0) during cycle 55 (550ns - 560ns)
*	Reading 10111100 from address 111101 (from port 0) during cycle 56 (560ns - 570ns)
*	Writing 00011111  to  address 000000 (from port 0) during cycle 57 (570ns - 580ns)
*	Reading 10111100 from address 111101 (from port 1) during cycle 57 (570ns - 580ns)
*	Reading 11010010 from address 111110 (from port 0) during cycle 58 (580ns - 590ns)
*	Writing 11110011  to  address 000000 (from port 1) during cycle 58 (580ns - 590ns)
*	Reading 11010010 from address 111110 (from port 1) during cycle 59 (590ns - 600ns)
*	Reading 11110011 from address 000000 (from port 0) during cycle 60 (600ns - 610ns)
*	Reading 11010010 from address 111110 (from port 0) during cycle 61 (610ns - 620ns)
*	Reading 11110011 from address 000000 (from port 1) during cycle 61 (610ns - 620ns)
*	Reading 10111100 from address 111101 (from port 0) during cycle 62 (620ns - 630ns)
*	Writing 10100000  to  address 000000 (from port 0) during cycle 63 (630ns - 640ns)
*	Writing 11100100  to  address 000001 (from port 1) during cycle 64 (640ns - 650ns)
*	Reading 11100100 from address 000001 (from port 0) during cycle 65 (650ns - 660ns)
*	Reading 11010010 from address 111110 (from port 1) during cycle 65 (650ns - 660ns)
*	Writing 10010001  to  address 000001 (from port 0) during cycle 66 (660ns - 670ns)
*	Writing 11011111  to  address 111101 (from port 1) during cycle 66 (660ns - 670ns)
*	Reading 10010001 from address 000001 (from port 0) during cycle 67 (670ns - 680ns)
*	Reading 11011111 from address 111101 (from port 1) during cycle 67 (670ns - 680ns)
*	Writing 10001010  to  address 111101 (from port 1) during cycle 68 (680ns - 690ns)
*	Reading 10100000 from address 000000 (from port 0) during cycle 69 (690ns - 700ns)
*	Reading 11010010 from address 111110 (from port 1) during cycle 69 (690ns - 700ns)
*	Reading 10100000 from address 000000 (from port 0) during cycle 70 (700ns - 710ns)
*	Reading 10001010 from address 111101 (from port 1) during cycle 71 (710ns - 720ns)
*	Reading 11010010 from address 111110 (from port 0) during cycle 72 (720ns - 730ns)
*	Writing 00101000  to  address 000000 (from port 0) during cycle 73 (730ns - 740ns)
*	Writing 01010111  to  address 000001 (from port 1) during cycle 73 (730ns - 740ns)
*	Reading 01010111 from address 000001 (from port 0) during cycle 74 (740ns - 750ns)
*	Reading 00101000 from address 000000 (from port 1) during cycle 74 (740ns - 750ns)
*	Reading 10001010 from address 111101 (from port 0) during cycle 75 (750ns - 760ns)
*	Writing 10100000  to  address 111101 (from port 0) during cycle 76 (760ns - 770ns)
*	Reading 11010010 from address 111110 (from port 0) during cycle 77 (770ns - 780ns)
*	Reading 11010010 from address 111110 (from port 1) during cycle 77 (770ns - 780ns)
*	Reading 10100000 from address 111101 (from port 1) during cycle 79 (790ns - 800ns)
*	Reading 00101000 from address 000000 (from port 0) during cycle 80 (800ns - 810ns)
*	Reading 01010111 from address 000001 (from port 1) during cycle 80 (800ns - 810ns)
*	Writing 00001100  to  address 000001 (from port 0) during cycle 81 (810ns - 820ns)
*	Reading 00101000 from address 000000 (from port 0) during cycle 82 (820ns - 830ns)
*	Reading 00001100 from address 000001 (from port 1) during cycle 82 (820ns - 830ns)
*	Writing 00001011  to  address 111101 (from port 1) during cycle 83 (830ns - 840ns)
*	Reading 00101000 from address 000000 (from port 0) during cycle 84 (840ns - 850ns)
*	Reading 00001100 from address 000001 (from port 1) during cycle 84 (840ns - 850ns)
*	Writing 01101111  to  address 111110 (from port 1) during cycle 85 (850ns - 860ns)
*	Reading 01101111 from address 111110 (from port 1) during cycle 88 (880ns - 890ns)
*	Reading 01101111 from address 111110 (from port 0) during cycle 90 (900ns - 910ns)
*	Writing 01110011  to  address 000001 (from port 1) during cycle 90 (900ns - 910ns)
*	Writing 00110010  to  address 000001 (from port 0) during cycle 91 (910ns - 920ns)
*	Reading 00101000 from address 000000 (from port 1) during cycle 91 (910ns - 920ns)
*	Writing 01001001  to  address 111110 (from port 0) during cycle 92 (920ns - 930ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 92 (920ns - 930ns)
*	Reading 00001011 from address 111101 (from port 0) during cycle 93 (930ns - 940ns)
*	Writing 10111001  to  address 000000 (from port 1) during cycle 93 (930ns - 940ns)
*	Reading 01001001 from address 111110 (from port 0) during cycle 94 (940ns - 950ns)
*	Writing 11100100  to  address 000000 (from port 0) during cycle 95 (950ns - 960ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 95 (950ns - 960ns)
*	Reading 00001011 from address 111101 (from port 0) during cycle 96 (960ns - 970ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 96 (960ns - 970ns)
*	Reading 00001011 from address 111101 (from port 0) during cycle 97 (970ns - 980ns)
*	Reading 01001001 from address 111110 (from port 1) during cycle 97 (970ns - 980ns)
*	Reading 11100100 from address 000000 (from port 0) during cycle 98 (980ns - 990ns)
*	Writing 00011010  to  address 000001 (from port 0) during cycle 99 (990ns - 1000ns)
*	Reading 11100100 from address 000000 (from port 1) during cycle 99 (990ns - 1000ns)
*	Reading 00011010 from address 000001 (from port 1) during cycle 100 (1000ns - 1010ns)
*	Writing 01010000  to  address 000000 (from port 0) during cycle 101 (1010ns - 1020ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 101 (1010ns - 1020ns)
*	Reading 01001001 from address 111110 (from port 1) during cycle 102 (1020ns - 1030ns)
*	Reading 01001001 from address 111110 (from port 1) during cycle 103 (1030ns - 1040ns)
*	Reading 01010000 from address 000000 (from port 0) during cycle 104 (1040ns - 1050ns)
*	Reading 00011010 from address 000001 (from port 1) during cycle 104 (1040ns - 1050ns)
*	Writing 11010010  to  address 111110 (from port 0) during cycle 105 (1050ns - 1060ns)
*	Writing 01011001  to  address 000001 (from port 1) during cycle 105 (1050ns - 1060ns)
*	Reading 11010010 from address 111110 (from port 0) during cycle 106 (1060ns - 1070ns)
*	Writing 10110111  to  address 000000 (from port 1) during cycle 107 (1070ns - 1080ns)
*	Reading 10110111 from address 000000 (from port 0) during cycle 108 (1080ns - 1090ns)
*	Writing 10001000  to  address 000000 (from port 0) during cycle 109 (1090ns - 1100ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 109 (1090ns - 1100ns)
*	Reading 10001000 from address 000000 (from port 0) during cycle 110 (1100ns - 1110ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 110 (1100ns - 1110ns)
*	Reading 11010010 from address 111110 (from port 1) during cycle 111 (1110ns - 1120ns)
*	Writing 00010001  to  address 000001 (from port 0) during cycle 112 (1120ns - 1130ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 112 (1120ns - 1130ns)
*	Reading 00001011 from address 111101 (from port 0) during cycle 114 (1140ns - 1150ns)
*	Writing 11011101  to  address 111110 (from port 1) during cycle 114 (1140ns - 1150ns)
*	Reading 11011101 from address 111110 (from port 0) during cycle 115 (1150ns - 1160ns)
*	Reading 11011101 from address 111110 (from port 1) during cycle 115 (1150ns - 1160ns)
*	Writing 10000110  to  address 000001 (from port 0) during cycle 116 (1160ns - 1170ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 116 (1160ns - 1170ns)
*	Reading 10000110 from address 000001 (from port 0) during cycle 117 (1170ns - 1180ns)
*	Reading 10001000 from address 000000 (from port 1) during cycle 117 (1170ns - 1180ns)
*	Writing 11001111  to  address 000000 (from port 0) during cycle 118 (1180ns - 1190ns)
*	Reading 11011101 from address 111110 (from port 0) during cycle 119 (1190ns - 1200ns)
*	Writing 11100000  to  address 000000 (from port 1) during cycle 119 (1190ns - 1200ns)
*	Reading 10000110 from address 000001 (from port 1) during cycle 120 (1200ns - 1210ns)
*	Writing 00110100  to  address 111110 (from port 1) during cycle 121 (1210ns - 1220ns)
*	Reading 11100000 from address 000000 (from port 1) during cycle 122 (1220ns - 1230ns)
*	Reading 10000110 from address 000001 (from port 0) during cycle 123 (1230ns - 1240ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 123 (1230ns - 1240ns)
*	Reading 00110100 from address 111110 (from port 0) during cycle 124 (1240ns - 1250ns)
*	Writing 11101100  to  address 111110 (from port 0) during cycle 126 (1260ns - 1270ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 126 (1260ns - 1270ns)
*	Reading 10000110 from address 000001 (from port 0) during cycle 127 (1270ns - 1280ns)
*	Reading 10000110 from address 000001 (from port 1) during cycle 127 (1270ns - 1280ns)
*	Reading 11101100 from address 111110 (from port 0) during cycle 128 (1280ns - 1290ns)
*	Reading 11101100 from address 111110 (from port 1) during cycle 128 (1280ns - 1290ns)
*	Writing 01000000  to  address 000000 (from port 0) during cycle 129 (1290ns - 1300ns)
*	Reading 00001011 from address 111101 (from port 1) during cycle 129 (1290ns - 1300ns)
*	Writing 10011101  to  address 000000 (from port 0) during cycle 130 (1300ns - 1310ns)
*	Reading 11101100 from address 111110 (from port 1) during cycle 130 (1300ns - 1310ns)
*	Reading 11101100 from address 111110 (from port 0) during cycle 131 (1310ns - 1320ns)
*	Writing 10000000  to  address 000000 (from port 1) during cycle 131 (1310ns - 1320ns)
*	Writing 01000101  to  address 111101 (from port 0) during cycle 132 (1320ns - 1330ns)
*	Reading 11101100 from address 111110 (from port 0) during cycle 133 (1330ns - 1340ns)
*	Writing 10101010  to  address 111101 (from port 1) during cycle 133 (1330ns - 1340ns)
*	Reading 10000110 from address 000001 (from port 0) during cycle 135 (1350ns - 1360ns)
*	Reading 10101010 from address 111101 (from port 1) during cycle 135 (1350ns - 1360ns)
*	Writing 00010011  to  address 000001 (from port 0) during cycle 136 (1360ns - 1370ns)
*	Writing 00101111  to  address 111110 (from port 1) during cycle 136 (1360ns - 1370ns)
*	Reading 00101111 from address 111110 (from port 0) during cycle 137 (1370ns - 1380ns)
*	Writing 11000000  to  address 000001 (from port 1) during cycle 137 (1370ns - 1380ns)
*	Reading 10101010 from address 111101 (from port 0) during cycle 138 (1380ns - 1390ns)
*	Writing 00101011  to  address 000000 (from port 1) during cycle 138 (1380ns - 1390ns)
*	Writing 10101111  to  address 000001 (from port 0) during cycle 139 (1390ns - 1400ns)
*	Reading 00101011 from address 000000 (from port 1) during cycle 139 (1390ns - 1400ns)
*	Writing 11101011  to  address 000000 (from port 0) during cycle 140 (1400ns - 1410ns)
*	Reading 10101010 from address 111101 (from port 1) during cycle 140 (1400ns - 1410ns)
*	Writing 11100000  to  address 000001 (from port 0) during cycle 141 (1410ns - 1420ns)
*	Reading 11101011 from address 000000 (from port 1) during cycle 141 (1410ns - 1420ns)
*	Writing 10100001  to  address 111101 (from port 0) during cycle 142 (1420ns - 1430ns)
*	Writing 10011001  to  address 111110 (from port 0) during cycle 143 (1430ns - 1440ns)
*	Writing 11000000  to  address 111110 (from port 0) during cycle 144 (1440ns - 1450ns)
*	Reading 10100001 from address 111101 (from port 1) during cycle 145 (1450ns - 1460ns)
*	Reading 11000000 from address 111110 (from port 0) during cycle 146 (1460ns - 1470ns)
*	Reading 11101011 from address 000000 (from port 1) during cycle 146 (1460ns - 1470ns)
*	Writing 11111101  to  address 000001 (from port 0) during cycle 147 (1470ns - 1480ns)
*	Reading 11000000 from address 111110 (from port 1) during cycle 147 (1470ns - 1480ns)
*	Reading 10100001 from address 111101 (from port 0) during cycle 148 (1480ns - 1490ns)
*	Reading 11111101 from address 000001 (from port 1) during cycle 149 (1490ns - 1500ns)
*	Writing 11010001  to  address 111110 (from port 1) during cycle 150 (1500ns - 1510ns)
*	Writing 10101100  to  address 111110 (from port 0) during cycle 151 (1510ns - 1520ns)
*	Writing 10000101  to  address 000001 (from port 1) during cycle 151 (1510ns - 1520ns)
*	Writing 11100010  to  address 000000 (from port 0) during cycle 152 (1520ns - 1530ns)
*	Writing 10110000  to  address 000001 (from port 1) during cycle 153 (1530ns - 1540ns)
*	Reading 10100001 from address 111101 (from port 0) during cycle 154 (1540ns - 1550ns)
*	Writing 01010001  to  address 000000 (from port 1) during cycle 154 (1540ns - 1550ns)
*	Reading 10100001 from address 111101 (from port 1) during cycle 155 (1550ns - 1560ns)
*	Writing 00101000  to  address 000000 (from port 0) during cycle 158 (1580ns - 1590ns)
*	Reading 10101100 from address 111110 (from port 0) during cycle 159 (1590ns - 1600ns)
*	Reading 10110000 from address 000001 (from port 0) during cycle 160 (1600ns - 1610ns)
*	Writing 01010100  to  address 000000 (from port 1) during cycle 160 (1600ns - 1610ns)
*	Writing 00100001  to  address 111110 (from port 0) during cycle 161 (1610ns - 1620ns)
*	Reading 01010100 from address 000000 (from port 1) during cycle 161 (1610ns - 1620ns)
*	Writing 01011100  to  address 000001 (from port 0) during cycle 162 (1620ns - 1630ns)
*	Reading 00100001 from address 111110 (from port 1) during cycle 162 (1620ns - 1630ns)
*	Reading 10100001 from address 111101 (from port 0) during cycle 163 (1630ns - 1640ns)
*	Reading 01011100 from address 000001 (from port 1) during cycle 163 (1630ns - 1640ns)
*	Reading 01011100 from address 000001 (from port 1) during cycle 164 (1640ns - 1650ns)
*	Reading 00100001 from address 111110 (from port 0) during cycle 165 (1650ns - 1660ns)
*	Reading 00100001 from address 111110 (from port 1) during cycle 166 (1660ns - 1670ns)
*	Writing 00110010  to  address 000000 (from port 0) during cycle 167 (1670ns - 1680ns)
*	Writing 11101100  to  address 000001 (from port 1) during cycle 167 (1670ns - 1680ns)
*	Reading 11101100 from address 000001 (from port 1) during cycle 168 (1680ns - 1690ns)
*	Reading 11101100 from address 000001 (from port 0) during cycle 169 (1690ns - 1700ns)
*	Reading 00100001 from address 111110 (from port 1) during cycle 169 (1690ns - 1700ns)
*	Writing 10000101  to  address 111110 (from port 0) during cycle 170 (1700ns - 1710ns)
*	Reading 11101100 from address 000001 (from port 1) during cycle 170 (1700ns - 1710ns)
*	Writing 10110010  to  address 111101 (from port 0) during cycle 171 (1710ns - 1720ns)
*	Writing 00000110  to  address 111101 (from port 0) during cycle 172 (1720ns - 1730ns)
*	Writing 11001010  to  address 000000 (from port 1) during cycle 172 (1720ns - 1730ns)
*	Reading 11101100 from address 000001 (from port 1) during cycle 173 (1730ns - 1740ns)
*	Reading 10000101 from address 111110 (from port 0) during cycle 174 (1740ns - 1750ns)
*	Reading 11101100 from address 000001 (from port 1) during cycle 174 (1740ns - 1750ns)
*	Reading 10000101 from address 111110 (from port 0) during cycle 175 (1750ns - 1760ns)
*	Reading 11101100 from address 000001 (from port 1) during cycle 175 (1750ns - 1760ns)
*	Reading 00000110 from address 111101 (from port 0) during cycle 176 (1760ns - 1770ns)
*	Reading 00000110 from address 111101 (from port 1) during cycle 176 (1760ns - 1770ns)
*	Reading 11001010 from address 000000 (from port 0) during cycle 177 (1770ns - 1780ns)
*	Reading 11101100 from address 000001 (from port 1) during cycle 177 (1770ns - 1780ns)
*	Writing 11110100  to  address 111101 (from port 1) during cycle 178 (1780ns - 1790ns)
*	Reading 11001010 from address 000000 (from port 0) during cycle 179 (1790ns - 1800ns)
*	Reading 11101100 from address 000001 (from port 1) during cycle 179 (1790ns - 1800ns)
*	Writing 10101110  to  address 000001 (from port 1) during cycle 180 (1800ns - 1810ns)
*	Reading 10000101 from address 111110 (from port 1) during cycle 181 (1810ns - 1820ns)
*	Reading 10101110 from address 000001 (from port 0) during cycle 182 (1820ns - 1830ns)
*	Writing 10111100  to  address 111101 (from port 1) during cycle 182 (1820ns - 1830ns)
*	Reading 10111100 from address 111101 (from port 0) during cycle 183 (1830ns - 1840ns)
*	Reading 10101110 from address 000001 (from port 1) during cycle 183 (1830ns - 1840ns)
*	Reading 10000101 from address 111110 (from port 0) during cycle 184 (1840ns - 1850ns)
*	Reading 11001010 from address 000000 (from port 1) during cycle 185 (1850ns - 1860ns)
*	Writing 10100111  to  address 000000 (from port 1) during cycle 186 (1860ns - 1870ns)
*	Writing 10000011  to  address 000001 (from port 0) during cycle 187 (1870ns - 1880ns)
*	Reading 10111100 from address 111101 (from port 1) during cycle 187 (1870ns - 1880ns)
*	Reading 10111100 from address 111101 (from port 0) during cycle 188 (1880ns - 1890ns)
*	Reading 10100111 from address 000000 (from port 0) during cycle 190 (1900ns - 1910ns)
*	Writing 11101000  to  address 000001 (from port 1) during cycle 190 (1900ns - 1910ns)
*	Reading 10111100 from address 111101 (from port 0) during cycle 191 (1910ns - 1920ns)
*	Reading 10100111 from address 000000 (from port 0) during cycle 192 (1920ns - 1930ns)
*	Writing 00010011  to  address 000001 (from port 1) during cycle 192 (1920ns - 1930ns)
*	Writing 00110101  to  address 000001 (from port 0) during cycle 193 (1930ns - 1940ns)
*	Reading 10000101 from address 111110 (from port 0) during cycle 195 (1950ns - 1960ns)
*	Reading 10000101 from address 111110 (from port 1) during cycle 195 (1950ns - 1960ns)
*	Reading 10111100 from address 111101 (from port 0) during cycle 196 (1960ns - 1970ns)
*	Reading 00110101 from address 000001 (from port 0) during cycle 197 (1970ns - 1980ns)
*	Reading 10000101 from address 111110 (from port 0) during cycle 198 (1980ns - 1990ns)
*	Reading 00110101 from address 000001 (from port 1) during cycle 198 (1980ns - 1990ns)
*	Writing 11100001  to  address 000001 (from port 1) during cycle 199 (1990ns - 2000ns)
*	Reading 11100001 from address 000001 (from port 0) during cycle 200 (2000ns - 2010ns)
*	Reading 10000101 from address 111110 (from port 1) during cycle 200 (2000ns - 2010ns)
*	Reading 11100001 from address 000001 (from port 1) during cycle 201 (2010ns - 2020ns)
*	Writing 11111100  to  address 111110 (from port 0) during cycle 202 (2020ns - 2030ns)
*	Reading 10111100 from address 111101 (from port 0) during cycle 203 (2030ns - 2040ns)
*	Reading 11100001 from address 000001 (from port 1) during cycle 203 (2030ns - 2040ns)
*	Writing 11101011  to  address 111101 (from port 0) during cycle 204 (2040ns - 2050ns)
*	Idle during cycle 205 (2050ns - 2060ns)

* Generation of data and address signals
* (time, data): [(0, 0), (10, 1), (20, 1), (30, 0), (40, 0), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 1), (110, 1), (120, 1), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 1), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 1), (430, 1), (440, 0), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 1), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 0), (640, 0), (650, 0), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 0), (750, 0), (760, 0), (770, 0), (780, 0), (790, 0), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 0), (910, 0), (920, 1), (930, 1), (940, 1), (950, 0), (960, 0), (970, 0), (980, 0), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 0), (1170, 0), (1180, 1), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 1), (1310, 1), (1320, 1), (1330, 1), (1340, 1), (1350, 1), (1360, 1), (1370, 1), (1380, 1), (1390, 1), (1400, 1), (1410, 0), (1420, 1), (1430, 1), (1440, 0), (1450, 0), (1460, 0), (1470, 1), (1480, 1), (1490, 1), (1500, 1), (1510, 0), (1520, 0), (1530, 0), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 0), (1600, 0), (1610, 1), (1620, 0), (1630, 0), (1640, 0), (1650, 0), (1660, 0), (1670, 0), (1680, 0), (1690, 0), (1700, 1), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 1), (1880, 1), (1890, 1), (1900, 1), (1910, 1), (1920, 1), (1930, 1), (1940, 1), (1950, 1), (1960, 1), (1970, 1), (1980, 1), (1990, 1), (2000, 1), (2010, 1), (2020, 0), (2030, 0), (2040, 1), (2050, 1)]
Vdin0_0  din0_0  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 1.8v 29.495n 1.8v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 1.8v 579.495n 1.8v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 1.8v 1909.495n 1.8v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 1.8v 1929.495n 1.8v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 1), (20, 1), (30, 1), (40, 1), (50, 1), (60, 1), (70, 1), (80, 1), (90, 1), (100, 0), (110, 1), (120, 1), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 1), (200, 1), (210, 1), (220, 1), (230, 1), (240, 1), (250, 1), (260, 1), (270, 0), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 0), (350, 0), (360, 0), (370, 0), (380, 0), (390, 1), (400, 1), (410, 1), (420, 1), (430, 1), (440, 1), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 1), (540, 1), (550, 1), (560, 1), (570, 1), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 0), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 0), (740, 0), (750, 0), (760, 0), (770, 0), (780, 0), (790, 0), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 0), (910, 1), (920, 0), (930, 0), (940, 0), (950, 0), (960, 0), (970, 0), (980, 0), (990, 1), (1000, 1), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 1), (1060, 1), (1070, 1), (1080, 1), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 0), (1150, 0), (1160, 1), (1170, 1), (1180, 1), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 0), (1310, 0), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 1), (1370, 1), (1380, 1), (1390, 1), (1400, 1), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 0), (1460, 0), (1470, 0), (1480, 0), (1490, 0), (1500, 0), (1510, 0), (1520, 1), (1530, 1), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 0), (1630, 0), (1640, 0), (1650, 0), (1660, 0), (1670, 1), (1680, 1), (1690, 1), (1700, 0), (1710, 1), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 1), (1780, 1), (1790, 1), (1800, 1), (1810, 1), (1820, 1), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 1), (1880, 1), (1890, 1), (1900, 1), (1910, 1), (1920, 1), (1930, 0), (1940, 0), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 0), (2000, 0), (2010, 0), (2020, 0), (2030, 0), (2040, 1), (2050, 1)]
Vdin0_1  din0_1  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 1.8v 29.495n 1.8v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 1.8v 59.495n 1.8v 59.505n 1.8v 69.495n 1.8v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 0.0v 109.495n 0.0v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 1.8v 219.495n 1.8v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 0.0v 279.495n 0.0v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 0.0v 369.495n 0.0v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 1.8v 449.495n 1.8v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 1.8v 579.495n 1.8v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 0.0v 909.495n 0.0v 909.505n 1.8v 919.495n 1.8v 919.505n 0.0v 929.495n 0.0v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 0.0v 1489.495n 0.0v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 0.0v 1509.495n 0.0v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 1.8v 1679.495n 1.8v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 1.8v 1779.495n 1.8v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 1.8v 1909.495n 1.8v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 1.8v 1929.495n 1.8v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 1), (20, 1), (30, 1), (40, 1), (50, 1), (60, 1), (70, 1), (80, 1), (90, 1), (100, 0), (110, 1), (120, 1), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 1), (200, 1), (210, 1), (220, 1), (230, 1), (240, 0), (250, 0), (260, 0), (270, 0), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 0), (350, 0), (360, 0), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 0), (430, 0), (440, 1), (450, 1), (460, 1), (470, 1), (480, 1), (490, 1), (500, 1), (510, 1), (520, 1), (530, 1), (540, 0), (550, 0), (560, 0), (570, 1), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 0), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 0), (740, 0), (750, 0), (760, 0), (770, 0), (780, 0), (790, 0), (800, 0), (810, 1), (820, 1), (830, 1), (840, 1), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 1), (910, 0), (920, 0), (930, 0), (940, 0), (950, 1), (960, 1), (970, 1), (980, 1), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 0), (1150, 0), (1160, 1), (1170, 1), (1180, 1), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 1), (1280, 1), (1290, 0), (1300, 1), (1310, 1), (1320, 1), (1330, 1), (1340, 1), (1350, 1), (1360, 0), (1370, 0), (1380, 0), (1390, 1), (1400, 0), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 0), (1460, 0), (1470, 1), (1480, 1), (1490, 1), (1500, 1), (1510, 1), (1520, 0), (1530, 0), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 1), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 0), (1690, 0), (1700, 1), (1710, 0), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 1), (1780, 1), (1790, 1), (1800, 1), (1810, 1), (1820, 1), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 0), (1880, 0), (1890, 0), (1900, 0), (1910, 0), (1920, 0), (1930, 1), (1940, 1), (1950, 1), (1960, 1), (1970, 1), (1980, 1), (1990, 1), (2000, 1), (2010, 1), (2020, 1), (2030, 1), (2040, 0), (2050, 0)]
Vdin0_2  din0_2  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 1.8v 29.495n 1.8v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 1.8v 59.495n 1.8v 59.505n 1.8v 69.495n 1.8v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 0.0v 109.495n 0.0v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 1.8v 219.495n 1.8v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 0.0v 249.495n 0.0v 249.505n 0.0v 259.495n 0.0v 259.505n 0.0v 269.495n 0.0v 269.505n 0.0v 279.495n 0.0v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 0.0v 369.495n 0.0v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 1.8v 449.495n 1.8v 449.505n 1.8v 459.495n 1.8v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 1.8v 529.495n 1.8v 529.505n 1.8v 539.495n 1.8v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 1.8v 579.495n 1.8v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 1.8v 819.495n 1.8v 819.505n 1.8v 829.495n 1.8v 829.505n 1.8v 839.495n 1.8v 839.505n 1.8v 849.495n 1.8v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 1.8v 909.495n 1.8v 909.505n 0.0v 919.495n 0.0v 919.505n 0.0v 929.495n 0.0v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 1.8v 1779.495n 1.8v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 0), (20, 1), (30, 0), (40, 0), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 1), (110, 1), (120, 1), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 0), (260, 0), (270, 0), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 0), (350, 0), (360, 0), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 0), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 1), (530, 1), (540, 0), (550, 0), (560, 0), (570, 1), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 0), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 1), (740, 1), (750, 1), (760, 0), (770, 0), (780, 0), (790, 0), (800, 0), (810, 1), (820, 1), (830, 1), (840, 1), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 1), (910, 0), (920, 1), (930, 1), (940, 1), (950, 0), (960, 0), (970, 0), (980, 0), (990, 1), (1000, 1), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 1), (1100, 1), (1110, 1), (1120, 0), (1130, 0), (1140, 0), (1150, 0), (1160, 0), (1170, 0), (1180, 1), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 1), (1280, 1), (1290, 0), (1300, 1), (1310, 1), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 0), (1370, 0), (1380, 0), (1390, 1), (1400, 1), (1410, 0), (1420, 0), (1430, 1), (1440, 0), (1450, 0), (1460, 0), (1470, 1), (1480, 1), (1490, 1), (1500, 1), (1510, 1), (1520, 0), (1530, 0), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 1), (1590, 1), (1600, 1), (1610, 0), (1620, 1), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 0), (1690, 0), (1700, 0), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 0), (1880, 0), (1890, 0), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 0), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 0), (2000, 0), (2010, 0), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Vdin0_3  din0_3  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 1.8v 29.495n 1.8v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 0.0v 259.495n 0.0v 259.505n 0.0v 269.495n 0.0v 269.505n 0.0v 279.495n 0.0v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 0.0v 369.495n 0.0v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 1.8v 529.495n 1.8v 529.505n 1.8v 539.495n 1.8v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 1.8v 579.495n 1.8v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 1.8v 739.495n 1.8v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 1.8v 819.495n 1.8v 819.505n 1.8v 829.495n 1.8v 829.505n 1.8v 839.495n 1.8v 839.505n 1.8v 849.495n 1.8v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 1.8v 909.495n 1.8v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 1.8v 1609.495n 1.8v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 1), (20, 1), (30, 1), (40, 1), (50, 1), (60, 1), (70, 1), (80, 1), (90, 1), (100, 1), (110, 0), (120, 0), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 0), (260, 0), (270, 1), (280, 1), (290, 1), (300, 1), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 1), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 1), (430, 1), (440, 0), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 1), (540, 1), (550, 1), (560, 1), (570, 1), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 0), (640, 0), (650, 0), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 0), (750, 0), (760, 0), (770, 0), (780, 0), (790, 0), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 0), (910, 1), (920, 0), (930, 0), (940, 0), (950, 0), (960, 0), (970, 0), (980, 0), (990, 1), (1000, 1), (1010, 1), (1020, 1), (1030, 1), (1040, 1), (1050, 1), (1060, 1), (1070, 1), (1080, 1), (1090, 0), (1100, 0), (1110, 0), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 0), (1170, 0), (1180, 0), (1190, 0), (1200, 0), (1210, 0), (1220, 0), (1230, 0), (1240, 0), (1250, 0), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 1), (1310, 1), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 1), (1370, 1), (1380, 1), (1390, 0), (1400, 0), (1410, 0), (1420, 0), (1430, 1), (1440, 0), (1450, 0), (1460, 0), (1470, 1), (1480, 1), (1490, 1), (1500, 1), (1510, 0), (1520, 0), (1530, 0), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 1), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 1), (1680, 1), (1690, 1), (1700, 0), (1710, 1), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 0), (1880, 0), (1890, 0), (1900, 0), (1910, 0), (1920, 0), (1930, 1), (1940, 1), (1950, 1), (1960, 1), (1970, 1), (1980, 1), (1990, 1), (2000, 1), (2010, 1), (2020, 1), (2030, 1), (2040, 0), (2050, 0)]
Vdin0_4  din0_4  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 1.8v 29.495n 1.8v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 1.8v 59.495n 1.8v 59.505n 1.8v 69.495n 1.8v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 1.8v 109.495n 1.8v 109.505n 0.0v 119.495n 0.0v 119.505n 0.0v 129.495n 0.0v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 0.0v 259.495n 0.0v 259.505n 0.0v 269.495n 0.0v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 1.8v 579.495n 1.8v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 0.0v 909.495n 0.0v 909.505n 1.8v 919.495n 1.8v 919.505n 0.0v 929.495n 0.0v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 0.0v 1259.495n 0.0v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 1.8v 1679.495n 1.8v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 1), (20, 1), (30, 1), (40, 1), (50, 1), (60, 1), (70, 1), (80, 1), (90, 1), (100, 1), (110, 1), (120, 1), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 1), (200, 1), (210, 1), (220, 1), (230, 1), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 1), (370, 0), (380, 0), (390, 1), (400, 1), (410, 1), (420, 0), (430, 0), (440, 1), (450, 1), (460, 1), (470, 1), (480, 1), (490, 1), (500, 1), (510, 1), (520, 0), (530, 1), (540, 0), (550, 0), (560, 0), (570, 0), (580, 0), (590, 0), (600, 0), (610, 0), (620, 0), (630, 1), (640, 1), (650, 1), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 1), (740, 1), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 1), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 0), (910, 1), (920, 0), (930, 0), (940, 0), (950, 1), (960, 1), (970, 1), (980, 1), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 0), (1150, 0), (1160, 0), (1170, 0), (1180, 0), (1190, 0), (1200, 0), (1210, 0), (1220, 0), (1230, 0), (1240, 0), (1250, 0), (1260, 1), (1270, 1), (1280, 1), (1290, 0), (1300, 0), (1310, 0), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 0), (1370, 0), (1380, 0), (1390, 1), (1400, 1), (1410, 1), (1420, 1), (1430, 0), (1440, 0), (1450, 0), (1460, 0), (1470, 1), (1480, 1), (1490, 1), (1500, 1), (1510, 1), (1520, 1), (1530, 1), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 1), (1610, 1), (1620, 0), (1630, 0), (1640, 0), (1650, 0), (1660, 0), (1670, 1), (1680, 1), (1690, 1), (1700, 0), (1710, 1), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 0), (1880, 0), (1890, 0), (1900, 0), (1910, 0), (1920, 0), (1930, 1), (1940, 1), (1950, 1), (1960, 1), (1970, 1), (1980, 1), (1990, 1), (2000, 1), (2010, 1), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Vdin0_5  din0_5  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 1.8v 29.495n 1.8v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 1.8v 59.495n 1.8v 59.505n 1.8v 69.495n 1.8v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 1.8v 219.495n 1.8v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 1.8v 449.495n 1.8v 449.505n 1.8v 459.495n 1.8v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 0.0v 579.495n 0.0v 579.505n 0.0v 589.495n 0.0v 589.505n 0.0v 599.495n 0.0v 599.505n 0.0v 609.495n 0.0v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 1.8v 639.495n 1.8v 639.505n 1.8v 649.495n 1.8v 649.505n 1.8v 659.495n 1.8v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 1.8v 739.495n 1.8v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 0.0v 909.495n 0.0v 909.505n 1.8v 919.495n 1.8v 919.505n 0.0v 929.495n 0.0v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 0.0v 1259.495n 0.0v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 1.8v 1419.495n 1.8v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 1.8v 1609.495n 1.8v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 1.8v 1679.495n 1.8v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 1), (20, 0), (30, 1), (40, 1), (50, 1), (60, 1), (70, 1), (80, 1), (90, 1), (100, 1), (110, 1), (120, 1), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 0), (260, 0), (270, 0), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 0), (350, 0), (360, 0), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 1), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 1), (540, 1), (550, 1), (560, 1), (570, 0), (580, 0), (590, 0), (600, 0), (610, 0), (620, 0), (630, 0), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 0), (740, 0), (750, 0), (760, 0), (770, 0), (780, 0), (790, 0), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 0), (910, 0), (920, 1), (930, 1), (940, 1), (950, 1), (960, 1), (970, 1), (980, 1), (990, 0), (1000, 0), (1010, 1), (1020, 1), (1030, 1), (1040, 1), (1050, 1), (1060, 1), (1070, 1), (1080, 1), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 0), (1150, 0), (1160, 0), (1170, 0), (1180, 1), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 1), (1280, 1), (1290, 1), (1300, 0), (1310, 0), (1320, 1), (1330, 1), (1340, 1), (1350, 1), (1360, 0), (1370, 0), (1380, 0), (1390, 0), (1400, 1), (1410, 1), (1420, 0), (1430, 0), (1440, 1), (1450, 1), (1460, 1), (1470, 1), (1480, 1), (1490, 1), (1500, 1), (1510, 0), (1520, 1), (1530, 1), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 1), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 0), (1690, 0), (1700, 0), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 0), (1880, 0), (1890, 0), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 0), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 0), (2000, 0), (2010, 0), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Vdin0_6  din0_6  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 0.0v 29.495n 0.0v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 1.8v 59.495n 1.8v 59.505n 1.8v 69.495n 1.8v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 0.0v 259.495n 0.0v 259.505n 0.0v 269.495n 0.0v 269.505n 0.0v 279.495n 0.0v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 0.0v 369.495n 0.0v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 1.8v 449.495n 1.8v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 0.0v 579.495n 0.0v 579.505n 0.0v 589.495n 0.0v 589.505n 0.0v 599.495n 0.0v 599.505n 0.0v 609.495n 0.0v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 1.8v 1419.495n 1.8v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 0), (20, 1), (30, 0), (40, 0), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 0), (110, 1), (120, 1), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 1), (200, 1), (210, 1), (220, 1), (230, 1), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 1), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 1), (430, 1), (440, 1), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 1), (530, 1), (540, 1), (550, 1), (560, 1), (570, 0), (580, 0), (590, 0), (600, 0), (610, 0), (620, 0), (630, 1), (640, 1), (650, 1), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 0), (750, 0), (760, 1), (770, 1), (780, 1), (790, 1), (800, 1), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 0), (910, 0), (920, 0), (930, 0), (940, 0), (950, 1), (960, 1), (970, 1), (980, 1), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 1), (1060, 1), (1070, 1), (1080, 1), (1090, 1), (1100, 1), (1110, 1), (1120, 0), (1130, 0), (1140, 0), (1150, 0), (1160, 1), (1170, 1), (1180, 1), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 1), (1280, 1), (1290, 0), (1300, 1), (1310, 1), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 0), (1370, 0), (1380, 0), (1390, 1), (1400, 1), (1410, 1), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 1), (1480, 1), (1490, 1), (1500, 1), (1510, 1), (1520, 1), (1530, 1), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 0), (1630, 0), (1640, 0), (1650, 0), (1660, 0), (1670, 0), (1680, 0), (1690, 0), (1700, 1), (1710, 1), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 1), (1880, 1), (1890, 1), (1900, 1), (1910, 1), (1920, 1), (1930, 0), (1940, 0), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 0), (2000, 0), (2010, 0), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Vdin0_7  din0_7  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 1.8v 29.495n 1.8v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 1.8v 219.495n 1.8v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 1.8v 449.495n 1.8v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 1.8v 529.495n 1.8v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 0.0v 579.495n 0.0v 579.505n 0.0v 589.495n 0.0v 589.505n 0.0v 599.495n 0.0v 599.505n 0.0v 609.495n 0.0v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 1.8v 639.495n 1.8v 639.505n 1.8v 649.495n 1.8v 649.505n 1.8v 659.495n 1.8v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 0.0v 929.495n 0.0v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 1.8v 1419.495n 1.8v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 1.8v 1909.495n 1.8v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 1.8v 1929.495n 1.8v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 0), (20, 1), (30, 1), (40, 1), (50, 1), (60, 0), (70, 0), (80, 0), (90, 0), (100, 0), (110, 1), (120, 1), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 1), (230, 1), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 0), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 1), (440, 0), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 0), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 1), (640, 0), (650, 0), (660, 1), (670, 1), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 1), (740, 1), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 1), (810, 1), (820, 1), (830, 1), (840, 1), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 1), (910, 1), (920, 1), (930, 1), (940, 1), (950, 1), (960, 1), (970, 1), (980, 1), (990, 1), (1000, 1), (1010, 1), (1020, 1), (1030, 1), (1040, 1), (1050, 1), (1060, 1), (1070, 1), (1080, 1), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 1), (1170, 1), (1180, 1), (1190, 0), (1200, 0), (1210, 0), (1220, 0), (1230, 0), (1240, 0), (1250, 0), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 0), (1310, 0), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 1), (1370, 0), (1380, 1), (1390, 1), (1400, 1), (1410, 1), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 1), (1480, 1), (1490, 1), (1500, 1), (1510, 1), (1520, 1), (1530, 0), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 0), (1610, 0), (1620, 0), (1630, 0), (1640, 0), (1650, 0), (1660, 0), (1670, 0), (1680, 0), (1690, 0), (1700, 0), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 1), (1870, 1), (1880, 1), (1890, 1), (1900, 0), (1910, 0), (1920, 1), (1930, 1), (1940, 1), (1950, 1), (1960, 1), (1970, 1), (1980, 1), (1990, 1), (2000, 1), (2010, 1), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Vdin1_0  din1_0  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 1.8v 29.495n 1.8v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 1.8v 59.495n 1.8v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 0.0v 369.495n 0.0v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 0.0v 579.495n 0.0v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 1.8v 639.495n 1.8v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 1.8v 739.495n 1.8v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 1.8v 819.495n 1.8v 819.505n 1.8v 829.495n 1.8v 829.505n 1.8v 839.495n 1.8v 839.505n 1.8v 849.495n 1.8v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 1.8v 909.495n 1.8v 909.505n 1.8v 919.495n 1.8v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 0.0v 1259.495n 0.0v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 1.8v 1419.495n 1.8v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 1.8v 1929.495n 1.8v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 1), (20, 1), (30, 1), (40, 1), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 0), (110, 1), (120, 1), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 1), (230, 1), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 0), (320, 0), (330, 0), (340, 0), (350, 0), (360, 0), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 0), (450, 0), (460, 1), (470, 1), (480, 0), (490, 0), (500, 0), (510, 0), (520, 1), (530, 1), (540, 1), (550, 1), (560, 1), (570, 1), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 1), (640, 0), (650, 0), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 1), (740, 1), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 1), (810, 1), (820, 1), (830, 1), (840, 1), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 1), (910, 1), (920, 1), (930, 0), (940, 0), (950, 0), (960, 0), (970, 0), (980, 0), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 0), (1060, 0), (1070, 1), (1080, 1), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 0), (1150, 0), (1160, 0), (1170, 0), (1180, 0), (1190, 0), (1200, 0), (1210, 0), (1220, 0), (1230, 0), (1240, 0), (1250, 0), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 0), (1310, 0), (1320, 0), (1330, 1), (1340, 1), (1350, 1), (1360, 1), (1370, 0), (1380, 1), (1390, 1), (1400, 1), (1410, 1), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 1), (1480, 1), (1490, 1), (1500, 0), (1510, 0), (1520, 0), (1530, 0), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 0), (1630, 0), (1640, 0), (1650, 0), (1660, 0), (1670, 0), (1680, 0), (1690, 0), (1700, 0), (1710, 0), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 1), (1780, 0), (1790, 0), (1800, 1), (1810, 1), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 1), (1870, 1), (1880, 1), (1890, 1), (1900, 0), (1910, 0), (1920, 1), (1930, 1), (1940, 1), (1950, 1), (1960, 1), (1970, 1), (1980, 1), (1990, 0), (2000, 0), (2010, 0), (2020, 0), (2030, 0), (2040, 0), (2050, 0)]
Vdin1_1  din1_1  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 1.8v 29.495n 1.8v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 0.0v 369.495n 0.0v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 1.8v 529.495n 1.8v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 1.8v 579.495n 1.8v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 1.8v 639.495n 1.8v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 1.8v 739.495n 1.8v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 1.8v 819.495n 1.8v 819.505n 1.8v 829.495n 1.8v 829.505n 1.8v 839.495n 1.8v 839.505n 1.8v 849.495n 1.8v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 1.8v 909.495n 1.8v 909.505n 1.8v 919.495n 1.8v 919.505n 1.8v 929.495n 1.8v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 0.0v 1259.495n 0.0v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 1.8v 1419.495n 1.8v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 0.0v 1509.495n 0.0v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 1.8v 1779.495n 1.8v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 1.8v 1929.495n 1.8v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 0), (20, 1), (30, 1), (40, 1), (50, 0), (60, 1), (70, 1), (80, 1), (90, 1), (100, 1), (110, 1), (120, 1), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 0), (260, 0), (270, 0), (280, 0), (290, 0), (300, 0), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 1), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 1), (440, 1), (450, 1), (460, 1), (470, 1), (480, 1), (490, 1), (500, 1), (510, 1), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 0), (580, 0), (590, 0), (600, 0), (610, 0), (620, 0), (630, 0), (640, 1), (650, 1), (660, 1), (670, 1), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 1), (740, 1), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 1), (810, 1), (820, 1), (830, 0), (840, 0), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 0), (910, 0), (920, 0), (930, 0), (940, 0), (950, 0), (960, 0), (970, 0), (980, 0), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 0), (1060, 0), (1070, 1), (1080, 1), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 1), (1170, 1), (1180, 1), (1190, 0), (1200, 0), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 1), (1280, 1), (1290, 1), (1300, 1), (1310, 0), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 1), (1370, 0), (1380, 0), (1390, 0), (1400, 0), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 0), (1460, 0), (1470, 0), (1480, 0), (1490, 0), (1500, 0), (1510, 1), (1520, 1), (1530, 0), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 0), (1600, 1), (1610, 1), (1620, 1), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 1), (1680, 1), (1690, 1), (1700, 1), (1710, 1), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 1), (1790, 1), (1800, 1), (1810, 1), (1820, 1), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 1), (1880, 1), (1890, 1), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 0), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 0), (2000, 0), (2010, 0), (2020, 0), (2030, 0), (2040, 0), (2050, 0)]
Vdin1_2  din1_2  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 1.8v 29.495n 1.8v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 0.0v 59.495n 0.0v 59.505n 1.8v 69.495n 1.8v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 0.0v 259.495n 0.0v 259.505n 0.0v 269.495n 0.0v 269.505n 0.0v 279.495n 0.0v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 1.8v 449.495n 1.8v 449.505n 1.8v 459.495n 1.8v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 0.0v 579.495n 0.0v 579.505n 0.0v 589.495n 0.0v 589.505n 0.0v 599.495n 0.0v 599.505n 0.0v 609.495n 0.0v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 1.8v 649.495n 1.8v 649.505n 1.8v 659.495n 1.8v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 1.8v 739.495n 1.8v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 1.8v 819.495n 1.8v 819.505n 1.8v 829.495n 1.8v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 0.0v 929.495n 0.0v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 0.0v 1489.495n 0.0v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 0.0v 1509.495n 0.0v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 1.8v 1609.495n 1.8v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 1.8v 1679.495n 1.8v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 1), (20, 0), (30, 0), (40, 0), (50, 1), (60, 1), (70, 1), (80, 1), (90, 1), (100, 1), (110, 0), (120, 0), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 1), (230, 1), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 1), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 0), (440, 1), (450, 1), (460, 1), (470, 1), (480, 1), (490, 1), (500, 1), (510, 1), (520, 1), (530, 1), (540, 1), (550, 1), (560, 1), (570, 1), (580, 0), (590, 0), (600, 0), (610, 0), (620, 0), (630, 0), (640, 0), (650, 0), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 0), (750, 0), (760, 0), (770, 0), (780, 0), (790, 0), (800, 0), (810, 0), (820, 0), (830, 1), (840, 1), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 0), (910, 0), (920, 0), (930, 1), (940, 1), (950, 1), (960, 1), (970, 1), (980, 1), (990, 1), (1000, 1), (1010, 1), (1020, 1), (1030, 1), (1040, 1), (1050, 1), (1060, 1), (1070, 0), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 1), (1150, 1), (1160, 1), (1170, 1), (1180, 1), (1190, 0), (1200, 0), (1210, 0), (1220, 0), (1230, 0), (1240, 0), (1250, 0), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 0), (1310, 0), (1320, 0), (1330, 1), (1340, 1), (1350, 1), (1360, 1), (1370, 0), (1380, 1), (1390, 1), (1400, 1), (1410, 1), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 1), (1480, 1), (1490, 1), (1500, 0), (1510, 0), (1520, 0), (1530, 0), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 0), (1630, 0), (1640, 0), (1650, 0), (1660, 0), (1670, 1), (1680, 1), (1690, 1), (1700, 1), (1710, 1), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 1), (1780, 0), (1790, 0), (1800, 1), (1810, 1), (1820, 1), (1830, 1), (1840, 1), (1850, 1), (1860, 0), (1870, 0), (1880, 0), (1890, 0), (1900, 1), (1910, 1), (1920, 0), (1930, 0), (1940, 0), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 0), (2000, 0), (2010, 0), (2020, 0), (2030, 0), (2040, 0), (2050, 0)]
Vdin1_3  din1_3  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 1.8v 59.495n 1.8v 59.505n 1.8v 69.495n 1.8v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 1.8v 109.495n 1.8v 109.505n 0.0v 119.495n 0.0v 119.505n 0.0v 129.495n 0.0v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 0.0v 439.495n 0.0v 439.505n 1.8v 449.495n 1.8v 449.505n 1.8v 459.495n 1.8v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 1.8v 529.495n 1.8v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 1.8v 579.495n 1.8v 579.505n 0.0v 589.495n 0.0v 589.505n 0.0v 599.495n 0.0v 599.505n 0.0v 609.495n 0.0v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 1.8v 839.495n 1.8v 839.505n 1.8v 849.495n 1.8v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 0.0v 929.495n 0.0v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 0.0v 1259.495n 0.0v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 1.8v 1419.495n 1.8v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 0.0v 1509.495n 0.0v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 1.8v 1679.495n 1.8v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 1.8v 1779.495n 1.8v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 1.8v 1909.495n 1.8v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 1), (20, 1), (30, 1), (40, 1), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 0), (110, 1), (120, 1), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 0), (260, 0), (270, 0), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 0), (350, 0), (360, 1), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 0), (450, 0), (460, 0), (470, 0), (480, 1), (490, 1), (500, 1), (510, 1), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 0), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 1), (640, 0), (650, 0), (660, 1), (670, 1), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 1), (740, 1), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 1), (810, 1), (820, 1), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 1), (910, 1), (920, 1), (930, 1), (940, 1), (950, 1), (960, 1), (970, 1), (980, 1), (990, 1), (1000, 1), (1010, 1), (1020, 1), (1030, 1), (1040, 1), (1050, 1), (1060, 1), (1070, 1), (1080, 1), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 1), (1170, 1), (1180, 1), (1190, 0), (1200, 0), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 1), (1280, 1), (1290, 1), (1300, 1), (1310, 0), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 0), (1370, 0), (1380, 0), (1390, 0), (1400, 0), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 0), (1460, 0), (1470, 0), (1480, 0), (1490, 0), (1500, 1), (1510, 0), (1520, 0), (1530, 1), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 1), (1610, 1), (1620, 1), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 0), (1690, 0), (1700, 0), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 1), (1790, 1), (1800, 0), (1810, 0), (1820, 1), (1830, 1), (1840, 1), (1850, 1), (1860, 0), (1870, 0), (1880, 0), (1890, 0), (1900, 0), (1910, 0), (1920, 1), (1930, 1), (1940, 1), (1950, 1), (1960, 1), (1970, 1), (1980, 1), (1990, 0), (2000, 0), (2010, 0), (2020, 0), (2030, 0), (2040, 0), (2050, 0)]
Vdin1_4  din1_4  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 1.8v 29.495n 1.8v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 0.0v 259.495n 0.0v 259.505n 0.0v 269.495n 0.0v 269.505n 0.0v 279.495n 0.0v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 0.0v 579.495n 0.0v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 1.8v 639.495n 1.8v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 1.8v 739.495n 1.8v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 1.8v 819.495n 1.8v 819.505n 1.8v 829.495n 1.8v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 1.8v 909.495n 1.8v 909.505n 1.8v 919.495n 1.8v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 0.0v 1489.495n 0.0v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 1.8v 1609.495n 1.8v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 1.8v 1929.495n 1.8v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 0), (20, 1), (30, 1), (40, 1), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 0), (110, 0), (120, 0), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 1), (230, 1), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 0), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 1), (450, 1), (460, 1), (470, 1), (480, 1), (490, 1), (500, 1), (510, 1), (520, 1), (530, 1), (540, 1), (550, 1), (560, 1), (570, 1), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 1), (640, 1), (650, 1), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 0), (740, 0), (750, 0), (760, 0), (770, 0), (780, 0), (790, 0), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 1), (910, 1), (920, 1), (930, 1), (940, 1), (950, 1), (960, 1), (970, 1), (980, 1), (990, 1), (1000, 1), (1010, 1), (1020, 1), (1030, 1), (1040, 1), (1050, 0), (1060, 0), (1070, 1), (1080, 1), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 0), (1150, 0), (1160, 0), (1170, 0), (1180, 0), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 1), (1280, 1), (1290, 1), (1300, 1), (1310, 0), (1320, 0), (1330, 1), (1340, 1), (1350, 1), (1360, 1), (1370, 0), (1380, 1), (1390, 1), (1400, 1), (1410, 1), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 1), (1480, 1), (1490, 1), (1500, 0), (1510, 0), (1520, 0), (1530, 1), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 0), (1630, 0), (1640, 0), (1650, 0), (1660, 0), (1670, 1), (1680, 1), (1690, 1), (1700, 1), (1710, 1), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 1), (1790, 1), (1800, 1), (1810, 1), (1820, 1), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 1), (1880, 1), (1890, 1), (1900, 1), (1910, 1), (1920, 0), (1930, 0), (1940, 0), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 1), (2000, 1), (2010, 1), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Vdin1_5  din1_5  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 1.8v 29.495n 1.8v 29.505n 1.8v 39.495n 1.8v 39.505n 1.8v 49.495n 1.8v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 0.0v 119.495n 0.0v 119.505n 0.0v 129.495n 0.0v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 0.0v 369.495n 0.0v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 1.8v 449.495n 1.8v 449.505n 1.8v 459.495n 1.8v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 1.8v 529.495n 1.8v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 1.8v 579.495n 1.8v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 1.8v 639.495n 1.8v 639.505n 1.8v 649.495n 1.8v 649.505n 1.8v 659.495n 1.8v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 1.8v 909.495n 1.8v 909.505n 1.8v 919.495n 1.8v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 1.8v 1419.495n 1.8v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 0.0v 1509.495n 0.0v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 1.8v 1679.495n 1.8v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 1.8v 1909.495n 1.8v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 0), (20, 1), (30, 0), (40, 0), (50, 1), (60, 0), (70, 0), (80, 0), (90, 0), (100, 0), (110, 0), (120, 0), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 1), (200, 1), (210, 1), (220, 1), (230, 1), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 1), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 0), (440, 1), (450, 1), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 1), (530, 1), (540, 1), (550, 1), (560, 1), (570, 1), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 1), (640, 1), (650, 1), (660, 1), (670, 1), (680, 0), (690, 0), (700, 0), (710, 0), (720, 0), (730, 1), (740, 1), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 1), (810, 1), (820, 1), (830, 0), (840, 0), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 1), (910, 1), (920, 1), (930, 0), (940, 0), (950, 0), (960, 0), (970, 0), (980, 0), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 1), (1060, 1), (1070, 0), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 1), (1150, 1), (1160, 1), (1170, 1), (1180, 1), (1190, 1), (1200, 1), (1210, 0), (1220, 0), (1230, 0), (1240, 0), (1250, 0), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 0), (1310, 0), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 0), (1370, 1), (1380, 0), (1390, 0), (1400, 0), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 0), (1460, 0), (1470, 0), (1480, 0), (1490, 0), (1500, 1), (1510, 0), (1520, 0), (1530, 0), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 1), (1610, 1), (1620, 1), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 1), (1680, 1), (1690, 1), (1700, 1), (1710, 1), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 1), (1780, 1), (1790, 1), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 0), (1880, 0), (1890, 0), (1900, 1), (1910, 1), (1920, 0), (1930, 0), (1940, 0), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 1), (2000, 1), (2010, 1), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Vdin1_6  din1_6  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 1.8v 29.495n 1.8v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 1.8v 59.495n 1.8v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 0.0v 119.495n 0.0v 119.505n 0.0v 129.495n 0.0v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 1.8v 219.495n 1.8v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 0.0v 439.495n 0.0v 439.505n 1.8v 449.495n 1.8v 449.505n 1.8v 459.495n 1.8v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 1.8v 529.495n 1.8v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 1.8v 579.495n 1.8v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 1.8v 639.495n 1.8v 639.505n 1.8v 649.495n 1.8v 649.505n 1.8v 659.495n 1.8v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 1.8v 739.495n 1.8v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 1.8v 819.495n 1.8v 819.505n 1.8v 829.495n 1.8v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 1.8v 909.495n 1.8v 909.505n 1.8v 919.495n 1.8v 919.505n 1.8v 929.495n 1.8v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 0.0v 1259.495n 0.0v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 0.0v 1489.495n 0.0v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 1.8v 1609.495n 1.8v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 1.8v 1679.495n 1.8v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 1.8v 1779.495n 1.8v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 1.8v 1909.495n 1.8v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 1), (20, 1), (30, 0), (40, 0), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 0), (110, 1), (120, 1), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 1), (200, 1), (210, 1), (220, 1), (230, 1), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 0), (320, 0), (330, 0), (340, 0), (350, 0), (360, 0), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 0), (440, 1), (450, 1), (460, 1), (470, 1), (480, 1), (490, 1), (500, 1), (510, 1), (520, 1), (530, 1), (540, 1), (550, 1), (560, 1), (570, 1), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 1), (640, 1), (650, 1), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 0), (750, 0), (760, 0), (770, 0), (780, 0), (790, 0), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 0), (910, 0), (920, 0), (930, 1), (940, 1), (950, 1), (960, 1), (970, 1), (980, 1), (990, 1), (1000, 1), (1010, 1), (1020, 1), (1030, 1), (1040, 1), (1050, 0), (1060, 0), (1070, 1), (1080, 1), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 1), (1170, 1), (1180, 1), (1190, 1), (1200, 1), (1210, 0), (1220, 0), (1230, 0), (1240, 0), (1250, 0), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 0), (1310, 1), (1320, 1), (1330, 1), (1340, 1), (1350, 1), (1360, 0), (1370, 1), (1380, 0), (1390, 0), (1400, 0), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 0), (1460, 0), (1470, 0), (1480, 0), (1490, 0), (1500, 1), (1510, 1), (1520, 1), (1530, 1), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 0), (1630, 0), (1640, 0), (1650, 0), (1660, 0), (1670, 1), (1680, 1), (1690, 1), (1700, 1), (1710, 1), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 1), (1780, 1), (1790, 1), (1800, 1), (1810, 1), (1820, 1), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 1), (1880, 1), (1890, 1), (1900, 1), (1910, 1), (1920, 0), (1930, 0), (1940, 0), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 1), (2000, 1), (2010, 1), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Vdin1_7  din1_7  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 1.8v 29.495n 1.8v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 1.8v 219.495n 1.8v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 0.0v 369.495n 0.0v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 0.0v 439.495n 0.0v 439.505n 1.8v 449.495n 1.8v 449.505n 1.8v 459.495n 1.8v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 1.8v 529.495n 1.8v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 1.8v 579.495n 1.8v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 1.8v 639.495n 1.8v 639.505n 1.8v 649.495n 1.8v 649.505n 1.8v 659.495n 1.8v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 0.0v 929.495n 0.0v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 0.0v 1259.495n 0.0v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 0.0v 1489.495n 0.0v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 1.8v 1679.495n 1.8v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 1.8v 1779.495n 1.8v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 1.8v 1909.495n 1.8v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 1), (20, 0), (30, 0), (40, 0), (50, 0), (60, 0), (70, 1), (80, 1), (90, 1), (100, 0), (110, 1), (120, 1), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 0), (190, 1), (200, 1), (210, 1), (220, 0), (230, 1), (240, 0), (250, 0), (260, 0), (270, 0), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 1), (340, 1), (350, 1), (360, 1), (370, 1), (380, 1), (390, 0), (400, 0), (410, 1), (420, 0), (430, 0), (440, 0), (450, 0), (460, 1), (470, 1), (480, 1), (490, 1), (500, 1), (510, 1), (520, 0), (530, 0), (540, 0), (550, 0), (560, 1), (570, 0), (580, 0), (590, 0), (600, 0), (610, 0), (620, 1), (630, 0), (640, 0), (650, 1), (660, 1), (670, 1), (680, 1), (690, 0), (700, 0), (710, 0), (720, 0), (730, 0), (740, 1), (750, 1), (760, 1), (770, 0), (780, 0), (790, 0), (800, 0), (810, 1), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 0), (910, 1), (920, 0), (930, 1), (940, 0), (950, 0), (960, 1), (970, 1), (980, 0), (990, 1), (1000, 1), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 1), (1130, 1), (1140, 1), (1150, 0), (1160, 1), (1170, 1), (1180, 0), (1190, 0), (1200, 0), (1210, 0), (1220, 0), (1230, 1), (1240, 0), (1250, 0), (1260, 0), (1270, 1), (1280, 0), (1290, 0), (1300, 0), (1310, 0), (1320, 1), (1330, 0), (1340, 0), (1350, 1), (1360, 1), (1370, 0), (1380, 1), (1390, 1), (1400, 0), (1410, 1), (1420, 1), (1430, 0), (1440, 0), (1450, 0), (1460, 0), (1470, 1), (1480, 1), (1490, 1), (1500, 1), (1510, 0), (1520, 0), (1530, 0), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 0), (1600, 1), (1610, 0), (1620, 1), (1630, 1), (1640, 1), (1650, 0), (1660, 0), (1670, 0), (1680, 0), (1690, 1), (1700, 0), (1710, 1), (1720, 1), (1730, 1), (1740, 0), (1750, 0), (1760, 1), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 1), (1830, 1), (1840, 0), (1850, 0), (1860, 0), (1870, 1), (1880, 1), (1890, 1), (1900, 0), (1910, 1), (1920, 0), (1930, 1), (1940, 1), (1950, 0), (1960, 1), (1970, 1), (1980, 0), (1990, 0), (2000, 1), (2010, 1), (2020, 0), (2030, 1), (2040, 1), (2050, 1)]
Va0_0  a0_0  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 1.8v 19.495n 1.8v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 0.0v 109.495n 0.0v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 1.8v 219.495n 1.8v 219.505n 0.0v 229.495n 0.0v 229.505n 1.8v 239.495n 1.8v 239.505n 0.0v 249.495n 0.0v 249.505n 0.0v 259.495n 0.0v 259.505n 0.0v 269.495n 0.0v 269.505n 0.0v 279.495n 0.0v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 1.8v 419.495n 1.8v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 1.8v 569.495n 1.8v 569.505n 0.0v 579.495n 0.0v 579.505n 0.0v 589.495n 0.0v 589.505n 0.0v 599.495n 0.0v 599.505n 0.0v 609.495n 0.0v 609.505n 0.0v 619.495n 0.0v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 1.8v 659.495n 1.8v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 0.0v 739.495n 0.0v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 1.8v 819.495n 1.8v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 0.0v 909.495n 0.0v 909.505n 1.8v 919.495n 1.8v 919.505n 0.0v 929.495n 0.0v 929.505n 1.8v 939.495n 1.8v 939.505n 0.0v 949.495n 0.0v 949.505n 0.0v 959.495n 0.0v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 0.0v 989.495n 0.0v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 0.0v 1259.495n 0.0v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 1.8v 1419.495n 1.8v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 1.8v 1609.495n 1.8v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 1), (40, 0), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 1), (110, 0), (120, 0), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 1), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 0), (310, 0), (320, 0), (330, 0), (340, 0), (350, 0), (360, 0), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 0), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 1), (540, 1), (550, 1), (560, 0), (570, 0), (580, 1), (590, 1), (600, 0), (610, 1), (620, 0), (630, 0), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 1), (730, 0), (740, 0), (750, 0), (760, 0), (770, 1), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 1), (910, 0), (920, 1), (930, 0), (940, 1), (950, 0), (960, 0), (970, 0), (980, 0), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 1), (1060, 1), (1070, 1), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 0), (1150, 1), (1160, 0), (1170, 0), (1180, 0), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 0), (1240, 1), (1250, 1), (1260, 1), (1270, 0), (1280, 1), (1290, 0), (1300, 0), (1310, 1), (1320, 0), (1330, 1), (1340, 1), (1350, 0), (1360, 0), (1370, 1), (1380, 0), (1390, 0), (1400, 0), (1410, 0), (1420, 0), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 0), (1480, 0), (1490, 0), (1500, 0), (1510, 1), (1520, 0), (1530, 0), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 1), (1600, 0), (1610, 1), (1620, 0), (1630, 0), (1640, 0), (1650, 1), (1660, 1), (1670, 0), (1680, 0), (1690, 0), (1700, 1), (1710, 0), (1720, 0), (1730, 0), (1740, 1), (1750, 1), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 1), (1850, 1), (1860, 1), (1870, 0), (1880, 0), (1890, 0), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 0), (1970, 0), (1980, 1), (1990, 1), (2000, 0), (2010, 0), (2020, 1), (2030, 0), (2040, 0), (2050, 0)]
Va0_1  a0_1  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 1.8v 39.495n 1.8v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 1.8v 109.495n 1.8v 109.505n 0.0v 119.495n 0.0v 119.505n 0.0v 129.495n 0.0v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 1.8v 189.495n 1.8v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 0.0v 369.495n 0.0v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 0.0v 569.495n 0.0v 569.505n 0.0v 579.495n 0.0v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 0.0v 609.495n 0.0v 609.505n 1.8v 619.495n 1.8v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 1.8v 909.495n 1.8v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 0.0v 939.495n 0.0v 939.505n 1.8v 949.495n 1.8v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 0.0v 1489.495n 0.0v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 0.0v 1509.495n 0.0v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 1), (40, 0), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 1), (110, 1), (120, 1), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 1), (190, 1), (200, 1), (210, 0), (220, 0), (230, 0), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 0), (310, 0), (320, 0), (330, 1), (340, 1), (350, 1), (360, 1), (370, 0), (380, 1), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 0), (450, 0), (460, 1), (470, 1), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 1), (540, 1), (550, 1), (560, 1), (570, 0), (580, 1), (590, 1), (600, 0), (610, 1), (620, 1), (630, 0), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 1), (730, 0), (740, 0), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 1), (910, 0), (920, 1), (930, 1), (940, 1), (950, 0), (960, 1), (970, 1), (980, 0), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 1), (1060, 1), (1070, 1), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 1), (1150, 1), (1160, 0), (1170, 0), (1180, 0), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 0), (1240, 1), (1250, 1), (1260, 1), (1270, 0), (1280, 1), (1290, 0), (1300, 0), (1310, 1), (1320, 1), (1330, 1), (1340, 1), (1350, 0), (1360, 0), (1370, 1), (1380, 1), (1390, 0), (1400, 0), (1410, 0), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 0), (1480, 1), (1490, 1), (1500, 1), (1510, 1), (1520, 0), (1530, 0), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 1), (1600, 0), (1610, 1), (1620, 0), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 0), (1690, 0), (1700, 1), (1710, 1), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 0), (1880, 1), (1890, 1), (1900, 0), (1910, 1), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 1), (1970, 0), (1980, 1), (1990, 1), (2000, 0), (2010, 0), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Va0_2  a0_2  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 1.8v 39.495n 1.8v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 1.8v 389.495n 1.8v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 0.0v 579.495n 0.0v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 0.0v 609.495n 0.0v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 1.8v 909.495n 1.8v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 0.0v 959.495n 0.0v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 1), (40, 0), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 1), (110, 1), (120, 1), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 1), (190, 1), (200, 1), (210, 0), (220, 0), (230, 0), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 0), (310, 0), (320, 0), (330, 1), (340, 1), (350, 1), (360, 1), (370, 0), (380, 1), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 0), (450, 0), (460, 1), (470, 1), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 1), (540, 1), (550, 1), (560, 1), (570, 0), (580, 1), (590, 1), (600, 0), (610, 1), (620, 1), (630, 0), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 1), (730, 0), (740, 0), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 1), (910, 0), (920, 1), (930, 1), (940, 1), (950, 0), (960, 1), (970, 1), (980, 0), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 1), (1060, 1), (1070, 1), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 1), (1150, 1), (1160, 0), (1170, 0), (1180, 0), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 0), (1240, 1), (1250, 1), (1260, 1), (1270, 0), (1280, 1), (1290, 0), (1300, 0), (1310, 1), (1320, 1), (1330, 1), (1340, 1), (1350, 0), (1360, 0), (1370, 1), (1380, 1), (1390, 0), (1400, 0), (1410, 0), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 0), (1480, 1), (1490, 1), (1500, 1), (1510, 1), (1520, 0), (1530, 0), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 1), (1600, 0), (1610, 1), (1620, 0), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 0), (1690, 0), (1700, 1), (1710, 1), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 0), (1880, 1), (1890, 1), (1900, 0), (1910, 1), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 1), (1970, 0), (1980, 1), (1990, 1), (2000, 0), (2010, 0), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Va0_3  a0_3  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 1.8v 39.495n 1.8v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 1.8v 389.495n 1.8v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 0.0v 579.495n 0.0v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 0.0v 609.495n 0.0v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 1.8v 909.495n 1.8v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 0.0v 959.495n 0.0v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 1), (40, 0), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 1), (110, 1), (120, 1), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 1), (190, 1), (200, 1), (210, 0), (220, 0), (230, 0), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 0), (310, 0), (320, 0), (330, 1), (340, 1), (350, 1), (360, 1), (370, 0), (380, 1), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 0), (450, 0), (460, 1), (470, 1), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 1), (540, 1), (550, 1), (560, 1), (570, 0), (580, 1), (590, 1), (600, 0), (610, 1), (620, 1), (630, 0), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 1), (730, 0), (740, 0), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 1), (910, 0), (920, 1), (930, 1), (940, 1), (950, 0), (960, 1), (970, 1), (980, 0), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 1), (1060, 1), (1070, 1), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 1), (1150, 1), (1160, 0), (1170, 0), (1180, 0), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 0), (1240, 1), (1250, 1), (1260, 1), (1270, 0), (1280, 1), (1290, 0), (1300, 0), (1310, 1), (1320, 1), (1330, 1), (1340, 1), (1350, 0), (1360, 0), (1370, 1), (1380, 1), (1390, 0), (1400, 0), (1410, 0), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 0), (1480, 1), (1490, 1), (1500, 1), (1510, 1), (1520, 0), (1530, 0), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 1), (1600, 0), (1610, 1), (1620, 0), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 0), (1690, 0), (1700, 1), (1710, 1), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 0), (1880, 1), (1890, 1), (1900, 0), (1910, 1), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 1), (1970, 0), (1980, 1), (1990, 1), (2000, 0), (2010, 0), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Va0_4  a0_4  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 1.8v 39.495n 1.8v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 1.8v 389.495n 1.8v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 0.0v 579.495n 0.0v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 0.0v 609.495n 0.0v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 1.8v 909.495n 1.8v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 0.0v 959.495n 0.0v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 1), (40, 0), (50, 0), (60, 0), (70, 0), (80, 0), (90, 0), (100, 1), (110, 1), (120, 1), (130, 0), (140, 0), (150, 0), (160, 0), (170, 0), (180, 1), (190, 1), (200, 1), (210, 0), (220, 0), (230, 0), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 0), (310, 0), (320, 0), (330, 1), (340, 1), (350, 1), (360, 1), (370, 0), (380, 1), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 0), (450, 0), (460, 1), (470, 1), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 1), (540, 1), (550, 1), (560, 1), (570, 0), (580, 1), (590, 1), (600, 0), (610, 1), (620, 1), (630, 0), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 0), (710, 0), (720, 1), (730, 0), (740, 0), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 1), (910, 0), (920, 1), (930, 1), (940, 1), (950, 0), (960, 1), (970, 1), (980, 0), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 1), (1060, 1), (1070, 1), (1080, 0), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 0), (1140, 1), (1150, 1), (1160, 0), (1170, 0), (1180, 0), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 0), (1240, 1), (1250, 1), (1260, 1), (1270, 0), (1280, 1), (1290, 0), (1300, 0), (1310, 1), (1320, 1), (1330, 1), (1340, 1), (1350, 0), (1360, 0), (1370, 1), (1380, 1), (1390, 0), (1400, 0), (1410, 0), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 0), (1480, 1), (1490, 1), (1500, 1), (1510, 1), (1520, 0), (1530, 0), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 1), (1600, 0), (1610, 1), (1620, 0), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 0), (1690, 0), (1700, 1), (1710, 1), (1720, 1), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 0), (1880, 1), (1890, 1), (1900, 0), (1910, 1), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 1), (1970, 0), (1980, 1), (1990, 1), (2000, 0), (2010, 0), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Va0_5  a0_5  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 1.8v 39.495n 1.8v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 1.8v 389.495n 1.8v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 0.0v 579.495n 0.0v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 0.0v 609.495n 0.0v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 0.0v 719.495n 0.0v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 1.8v 909.495n 1.8v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 0.0v 959.495n 0.0v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 1.8v 1729.495n 1.8v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 0), (20, 1), (30, 0), (40, 1), (50, 1), (60, 0), (70, 1), (80, 1), (90, 1), (100, 1), (110, 1), (120, 1), (130, 0), (140, 1), (150, 0), (160, 1), (170, 1), (180, 1), (190, 1), (200, 0), (210, 1), (220, 1), (230, 1), (240, 1), (250, 0), (260, 1), (270, 1), (280, 0), (290, 0), (300, 0), (310, 1), (320, 0), (330, 0), (340, 0), (350, 1), (360, 0), (370, 1), (380, 1), (390, 1), (400, 1), (410, 0), (420, 0), (430, 0), (440, 0), (450, 1), (460, 1), (470, 1), (480, 1), (490, 1), (500, 0), (510, 0), (520, 1), (530, 1), (540, 1), (550, 1), (560, 1), (570, 1), (580, 0), (590, 0), (600, 0), (610, 0), (620, 0), (630, 0), (640, 1), (650, 0), (660, 1), (670, 1), (680, 1), (690, 0), (700, 0), (710, 1), (720, 1), (730, 1), (740, 0), (750, 0), (760, 0), (770, 0), (780, 0), (790, 1), (800, 1), (810, 1), (820, 1), (830, 1), (840, 1), (850, 0), (860, 0), (870, 0), (880, 0), (890, 0), (900, 1), (910, 0), (920, 1), (930, 0), (940, 0), (950, 1), (960, 1), (970, 0), (980, 0), (990, 0), (1000, 1), (1010, 1), (1020, 0), (1030, 0), (1040, 1), (1050, 1), (1060, 1), (1070, 0), (1080, 0), (1090, 1), (1100, 1), (1110, 0), (1120, 1), (1130, 1), (1140, 0), (1150, 0), (1160, 1), (1170, 0), (1180, 0), (1190, 0), (1200, 1), (1210, 0), (1220, 0), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 1), (1280, 0), (1290, 1), (1300, 0), (1310, 0), (1320, 0), (1330, 1), (1340, 1), (1350, 1), (1360, 0), (1370, 1), (1380, 0), (1390, 0), (1400, 1), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 1), (1460, 0), (1470, 0), (1480, 0), (1490, 1), (1500, 0), (1510, 1), (1520, 1), (1530, 1), (1540, 0), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 0), (1610, 0), (1620, 0), (1630, 1), (1640, 1), (1650, 1), (1660, 0), (1670, 1), (1680, 1), (1690, 0), (1700, 1), (1710, 1), (1720, 0), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 1), (1780, 1), (1790, 1), (1800, 1), (1810, 0), (1820, 1), (1830, 1), (1840, 1), (1850, 0), (1860, 0), (1870, 1), (1880, 1), (1890, 1), (1900, 1), (1910, 1), (1920, 1), (1930, 1), (1940, 1), (1950, 0), (1960, 0), (1970, 0), (1980, 1), (1990, 1), (2000, 0), (2010, 1), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
Va1_0  a1_0  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 1.8v 29.495n 1.8v 29.505n 0.0v 39.495n 0.0v 39.505n 1.8v 49.495n 1.8v 49.505n 1.8v 59.495n 1.8v 59.505n 0.0v 69.495n 0.0v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 1.8v 109.495n 1.8v 109.505n 1.8v 119.495n 1.8v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 1.8v 149.495n 1.8v 149.505n 0.0v 159.495n 0.0v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 0.0v 209.495n 0.0v 209.505n 1.8v 219.495n 1.8v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 0.0v 259.495n 0.0v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 1.8v 319.495n 1.8v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 1.8v 359.495n 1.8v 359.505n 0.0v 369.495n 0.0v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 1.8v 459.495n 1.8v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 1.8v 529.495n 1.8v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 1.8v 579.495n 1.8v 579.505n 0.0v 589.495n 0.0v 589.505n 0.0v 599.495n 0.0v 599.505n 0.0v 609.495n 0.0v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 1.8v 649.495n 1.8v 649.505n 0.0v 659.495n 0.0v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 1.8v 739.495n 1.8v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 0.0v 789.495n 0.0v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 1.8v 819.495n 1.8v 819.505n 1.8v 829.495n 1.8v 829.505n 1.8v 839.495n 1.8v 839.505n 1.8v 849.495n 1.8v 849.505n 0.0v 859.495n 0.0v 859.505n 0.0v 869.495n 0.0v 869.505n 0.0v 879.495n 0.0v 879.505n 0.0v 889.495n 0.0v 889.505n 0.0v 899.495n 0.0v 899.505n 1.8v 909.495n 1.8v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 1.8v 1009.495n 1.8v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 1.8v 1059.495n 1.8v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 0.0v 1489.495n 0.0v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 0.0v 1509.495n 0.0v 1509.505n 1.8v 1519.495n 1.8v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 1.8v 1679.495n 1.8v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 1.8v 1779.495n 1.8v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 1.8v 1909.495n 1.8v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 1.8v 1929.495n 1.8v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 0), (40, 0), (50, 0), (60, 1), (70, 0), (80, 0), (90, 0), (100, 0), (110, 0), (120, 0), (130, 0), (140, 0), (150, 1), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 1), (260, 0), (270, 0), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 1), (350, 0), (360, 1), (370, 0), (380, 0), (390, 0), (400, 0), (410, 1), (420, 1), (430, 1), (440, 1), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 0), (580, 0), (590, 1), (600, 1), (610, 0), (620, 0), (630, 0), (640, 0), (650, 1), (660, 0), (670, 0), (680, 0), (690, 1), (700, 1), (710, 0), (720, 0), (730, 0), (740, 0), (750, 0), (760, 0), (770, 1), (780, 1), (790, 0), (800, 0), (810, 0), (820, 0), (830, 0), (840, 0), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 0), (910, 0), (920, 0), (930, 0), (940, 0), (950, 0), (960, 0), (970, 1), (980, 1), (990, 0), (1000, 0), (1010, 0), (1020, 1), (1030, 1), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 0), (1100, 0), (1110, 1), (1120, 0), (1130, 0), (1140, 1), (1150, 1), (1160, 0), (1170, 0), (1180, 0), (1190, 0), (1200, 0), (1210, 1), (1220, 0), (1230, 0), (1240, 0), (1250, 0), (1260, 0), (1270, 0), (1280, 1), (1290, 0), (1300, 1), (1310, 0), (1320, 0), (1330, 0), (1340, 0), (1350, 0), (1360, 1), (1370, 0), (1380, 0), (1390, 0), (1400, 0), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 0), (1460, 0), (1470, 1), (1480, 1), (1490, 0), (1500, 1), (1510, 0), (1520, 0), (1530, 0), (1540, 0), (1550, 0), (1560, 0), (1570, 0), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 1), (1630, 0), (1640, 0), (1650, 0), (1660, 1), (1670, 0), (1680, 0), (1690, 1), (1700, 0), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 1), (1820, 0), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 0), (1880, 0), (1890, 0), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 1), (1970, 1), (1980, 0), (1990, 0), (2000, 1), (2010, 0), (2020, 0), (2030, 0), (2040, 0), (2050, 0)]
Va1_1  a1_1  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 1.8v 69.495n 1.8v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 0.0v 119.495n 0.0v 119.505n 0.0v 129.495n 0.0v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 1.8v 159.495n 1.8v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 1.8v 259.495n 1.8v 259.505n 0.0v 269.495n 0.0v 269.505n 0.0v 279.495n 0.0v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 1.8v 349.495n 1.8v 349.505n 0.0v 359.495n 0.0v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 1.8v 449.495n 1.8v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 0.0v 579.495n 0.0v 579.505n 0.0v 589.495n 0.0v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 1.8v 659.495n 1.8v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 0.0v 719.495n 0.0v 719.505n 0.0v 729.495n 0.0v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 0.0v 929.495n 0.0v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 0.0v 1139.495n 0.0v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 0.0v 1259.495n 0.0v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 0.0v 1349.495n 0.0v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 0.0v 1569.495n 0.0v 1569.505n 0.0v 1579.495n 0.0v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 0.0v 1899.495n 0.0v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 0), (40, 0), (50, 0), (60, 1), (70, 0), (80, 0), (90, 0), (100, 0), (110, 0), (120, 1), (130, 0), (140, 0), (150, 1), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 1), (260, 1), (270, 1), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 1), (350, 1), (360, 1), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 1), (440, 1), (450, 0), (460, 1), (470, 1), (480, 1), (490, 1), (500, 0), (510, 0), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 1), (580, 0), (590, 1), (600, 1), (610, 0), (620, 0), (630, 0), (640, 0), (650, 1), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 0), (750, 0), (760, 0), (770, 1), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 1), (840, 0), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 0), (910, 0), (920, 1), (930, 0), (940, 0), (950, 1), (960, 1), (970, 1), (980, 1), (990, 0), (1000, 0), (1010, 1), (1020, 1), (1030, 1), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 1), (1170, 0), (1180, 0), (1190, 0), (1200, 0), (1210, 1), (1220, 0), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 0), (1280, 1), (1290, 1), (1300, 1), (1310, 0), (1320, 0), (1330, 1), (1340, 1), (1350, 1), (1360, 1), (1370, 0), (1380, 0), (1390, 0), (1400, 1), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 1), (1460, 0), (1470, 1), (1480, 1), (1490, 0), (1500, 1), (1510, 0), (1520, 0), (1530, 0), (1540, 0), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 0), (1610, 0), (1620, 1), (1630, 0), (1640, 0), (1650, 0), (1660, 1), (1670, 0), (1680, 0), (1690, 1), (1700, 0), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 1), (1770, 0), (1780, 1), (1790, 0), (1800, 0), (1810, 1), (1820, 1), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 1), (1880, 1), (1890, 1), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 1), (1970, 1), (1980, 0), (1990, 0), (2000, 1), (2010, 0), (2020, 0), (2030, 0), (2040, 0), (2050, 0)]
Va1_2  a1_2  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 1.8v 69.495n 1.8v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 0.0v 119.495n 0.0v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 1.8v 159.495n 1.8v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 1.8v 449.495n 1.8v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 1.8v 579.495n 1.8v 579.505n 0.0v 589.495n 0.0v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 1.8v 659.495n 1.8v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 1.8v 839.495n 1.8v 839.505n 0.0v 849.495n 0.0v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 0), (40, 0), (50, 0), (60, 1), (70, 0), (80, 0), (90, 0), (100, 0), (110, 0), (120, 1), (130, 0), (140, 0), (150, 1), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 1), (260, 1), (270, 1), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 1), (350, 1), (360, 1), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 1), (440, 1), (450, 0), (460, 1), (470, 1), (480, 1), (490, 1), (500, 0), (510, 0), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 1), (580, 0), (590, 1), (600, 1), (610, 0), (620, 0), (630, 0), (640, 0), (650, 1), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 0), (750, 0), (760, 0), (770, 1), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 1), (840, 0), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 0), (910, 0), (920, 1), (930, 0), (940, 0), (950, 1), (960, 1), (970, 1), (980, 1), (990, 0), (1000, 0), (1010, 1), (1020, 1), (1030, 1), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 1), (1170, 0), (1180, 0), (1190, 0), (1200, 0), (1210, 1), (1220, 0), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 0), (1280, 1), (1290, 1), (1300, 1), (1310, 0), (1320, 0), (1330, 1), (1340, 1), (1350, 1), (1360, 1), (1370, 0), (1380, 0), (1390, 0), (1400, 1), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 1), (1460, 0), (1470, 1), (1480, 1), (1490, 0), (1500, 1), (1510, 0), (1520, 0), (1530, 0), (1540, 0), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 0), (1610, 0), (1620, 1), (1630, 0), (1640, 0), (1650, 0), (1660, 1), (1670, 0), (1680, 0), (1690, 1), (1700, 0), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 1), (1770, 0), (1780, 1), (1790, 0), (1800, 0), (1810, 1), (1820, 1), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 1), (1880, 1), (1890, 1), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 1), (1970, 1), (1980, 0), (1990, 0), (2000, 1), (2010, 0), (2020, 0), (2030, 0), (2040, 0), (2050, 0)]
Va1_3  a1_3  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 1.8v 69.495n 1.8v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 0.0v 119.495n 0.0v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 1.8v 159.495n 1.8v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 1.8v 449.495n 1.8v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 1.8v 579.495n 1.8v 579.505n 0.0v 589.495n 0.0v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 1.8v 659.495n 1.8v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 1.8v 839.495n 1.8v 839.505n 0.0v 849.495n 0.0v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 0), (40, 0), (50, 0), (60, 1), (70, 0), (80, 0), (90, 0), (100, 0), (110, 0), (120, 1), (130, 0), (140, 0), (150, 1), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 1), (260, 1), (270, 1), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 1), (350, 1), (360, 1), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 1), (440, 1), (450, 0), (460, 1), (470, 1), (480, 1), (490, 1), (500, 0), (510, 0), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 1), (580, 0), (590, 1), (600, 1), (610, 0), (620, 0), (630, 0), (640, 0), (650, 1), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 0), (750, 0), (760, 0), (770, 1), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 1), (840, 0), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 0), (910, 0), (920, 1), (930, 0), (940, 0), (950, 1), (960, 1), (970, 1), (980, 1), (990, 0), (1000, 0), (1010, 1), (1020, 1), (1030, 1), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 1), (1170, 0), (1180, 0), (1190, 0), (1200, 0), (1210, 1), (1220, 0), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 0), (1280, 1), (1290, 1), (1300, 1), (1310, 0), (1320, 0), (1330, 1), (1340, 1), (1350, 1), (1360, 1), (1370, 0), (1380, 0), (1390, 0), (1400, 1), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 1), (1460, 0), (1470, 1), (1480, 1), (1490, 0), (1500, 1), (1510, 0), (1520, 0), (1530, 0), (1540, 0), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 0), (1610, 0), (1620, 1), (1630, 0), (1640, 0), (1650, 0), (1660, 1), (1670, 0), (1680, 0), (1690, 1), (1700, 0), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 1), (1770, 0), (1780, 1), (1790, 0), (1800, 0), (1810, 1), (1820, 1), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 1), (1880, 1), (1890, 1), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 1), (1970, 1), (1980, 0), (1990, 0), (2000, 1), (2010, 0), (2020, 0), (2030, 0), (2040, 0), (2050, 0)]
Va1_4  a1_4  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 1.8v 69.495n 1.8v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 0.0v 119.495n 0.0v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 1.8v 159.495n 1.8v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 1.8v 449.495n 1.8v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 1.8v 579.495n 1.8v 579.505n 0.0v 589.495n 0.0v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 1.8v 659.495n 1.8v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 1.8v 839.495n 1.8v 839.505n 0.0v 849.495n 0.0v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )
* (time, data): [(0, 0), (10, 0), (20, 0), (30, 0), (40, 0), (50, 0), (60, 1), (70, 0), (80, 0), (90, 0), (100, 0), (110, 0), (120, 1), (130, 0), (140, 0), (150, 1), (160, 0), (170, 0), (180, 0), (190, 0), (200, 0), (210, 0), (220, 0), (230, 0), (240, 0), (250, 1), (260, 1), (270, 1), (280, 0), (290, 0), (300, 0), (310, 0), (320, 0), (330, 0), (340, 1), (350, 1), (360, 1), (370, 1), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 1), (440, 1), (450, 0), (460, 1), (470, 1), (480, 1), (490, 1), (500, 0), (510, 0), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 1), (580, 0), (590, 1), (600, 1), (610, 0), (620, 0), (630, 0), (640, 0), (650, 1), (660, 1), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 0), (750, 0), (760, 0), (770, 1), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 1), (840, 0), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 0), (910, 0), (920, 1), (930, 0), (940, 0), (950, 1), (960, 1), (970, 1), (980, 1), (990, 0), (1000, 0), (1010, 1), (1020, 1), (1030, 1), (1040, 0), (1050, 0), (1060, 0), (1070, 0), (1080, 0), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 1), (1150, 1), (1160, 1), (1170, 0), (1180, 0), (1190, 0), (1200, 0), (1210, 1), (1220, 0), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 0), (1280, 1), (1290, 1), (1300, 1), (1310, 0), (1320, 0), (1330, 1), (1340, 1), (1350, 1), (1360, 1), (1370, 0), (1380, 0), (1390, 0), (1400, 1), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 1), (1460, 0), (1470, 1), (1480, 1), (1490, 0), (1500, 1), (1510, 0), (1520, 0), (1530, 0), (1540, 0), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 0), (1610, 0), (1620, 1), (1630, 0), (1640, 0), (1650, 0), (1660, 1), (1670, 0), (1680, 0), (1690, 1), (1700, 0), (1710, 0), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 1), (1770, 0), (1780, 1), (1790, 0), (1800, 0), (1810, 1), (1820, 1), (1830, 0), (1840, 0), (1850, 0), (1860, 0), (1870, 1), (1880, 1), (1890, 1), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 0), (1950, 1), (1960, 1), (1970, 1), (1980, 0), (1990, 0), (2000, 1), (2010, 0), (2020, 0), (2030, 0), (2040, 0), (2050, 0)]
Va1_5  a1_5  0 PWL (0n 0.0v 9.495n 0.0v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 1.8v 69.495n 1.8v 69.505n 0.0v 79.495n 0.0v 79.505n 0.0v 89.495n 0.0v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 0.0v 119.495n 0.0v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 1.8v 159.495n 1.8v 159.505n 0.0v 169.495n 0.0v 169.505n 0.0v 179.495n 0.0v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 0.0v 289.495n 0.0v 289.505n 0.0v 299.495n 0.0v 299.505n 0.0v 309.495n 0.0v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 0.0v 339.495n 0.0v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 1.8v 379.495n 1.8v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 1.8v 439.495n 1.8v 439.505n 1.8v 449.495n 1.8v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 1.8v 579.495n 1.8v 579.505n 0.0v 589.495n 0.0v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 0.0v 649.495n 0.0v 649.505n 1.8v 659.495n 1.8v 659.505n 1.8v 669.495n 1.8v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 1.8v 839.495n 1.8v 839.505n 0.0v 849.495n 0.0v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 1.8v 929.495n 1.8v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 1.8v 1369.495n 1.8v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 0.0v 1949.495n 0.0v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 0.0v )

 * Generation of control signals
* (time, data): [(0, 1), (10, 0), (20, 0), (30, 0), (40, 0), (50, 0), (60, 1), (70, 0), (80, 1), (90, 0), (100, 0), (110, 0), (120, 1), (130, 0), (140, 1), (150, 1), (160, 1), (170, 1), (180, 0), (190, 0), (200, 1), (210, 0), (220, 0), (230, 0), (240, 0), (250, 1), (260, 1), (270, 0), (280, 1), (290, 1), (300, 0), (310, 1), (320, 1), (330, 0), (340, 0), (350, 0), (360, 1), (370, 0), (380, 0), (390, 0), (400, 0), (410, 0), (420, 0), (430, 0), (440, 0), (450, 0), (460, 0), (470, 1), (480, 0), (490, 1), (500, 1), (510, 1), (520, 0), (530, 0), (540, 0), (550, 0), (560, 0), (570, 0), (580, 0), (590, 1), (600, 0), (610, 0), (620, 0), (630, 0), (640, 1), (650, 0), (660, 0), (670, 0), (680, 1), (690, 0), (700, 0), (710, 1), (720, 0), (730, 0), (740, 0), (750, 0), (760, 0), (770, 0), (780, 1), (790, 1), (800, 0), (810, 0), (820, 0), (830, 1), (840, 0), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 0), (910, 0), (920, 0), (930, 0), (940, 0), (950, 0), (960, 0), (970, 0), (980, 0), (990, 0), (1000, 1), (1010, 0), (1020, 1), (1030, 1), (1040, 0), (1050, 0), (1060, 0), (1070, 1), (1080, 0), (1090, 0), (1100, 0), (1110, 1), (1120, 0), (1130, 1), (1140, 0), (1150, 0), (1160, 0), (1170, 0), (1180, 0), (1190, 0), (1200, 1), (1210, 1), (1220, 1), (1230, 0), (1240, 0), (1250, 1), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 0), (1310, 0), (1320, 0), (1330, 0), (1340, 1), (1350, 0), (1360, 0), (1370, 0), (1380, 0), (1390, 0), (1400, 0), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 1), (1460, 0), (1470, 0), (1480, 0), (1490, 1), (1500, 1), (1510, 0), (1520, 0), (1530, 1), (1540, 0), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 0), (1600, 0), (1610, 0), (1620, 0), (1630, 0), (1640, 1), (1650, 0), (1660, 1), (1670, 0), (1680, 1), (1690, 0), (1700, 0), (1710, 0), (1720, 0), (1730, 1), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 1), (1790, 0), (1800, 1), (1810, 1), (1820, 0), (1830, 0), (1840, 0), (1850, 1), (1860, 1), (1870, 0), (1880, 0), (1890, 1), (1900, 0), (1910, 0), (1920, 0), (1930, 0), (1940, 1), (1950, 0), (1960, 0), (1970, 0), (1980, 0), (1990, 1), (2000, 0), (2010, 1), (2020, 0), (2030, 0), (2040, 0), (2050, 1)]
VCSB0 CSB0 0 PWL (0n 1.8v 9.495n 1.8v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 1.8v 69.495n 1.8v 69.505n 0.0v 79.495n 0.0v 79.505n 1.8v 89.495n 1.8v 89.505n 0.0v 99.495n 0.0v 99.505n 0.0v 109.495n 0.0v 109.505n 0.0v 119.495n 0.0v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 0.0v 189.495n 0.0v 189.505n 0.0v 199.495n 0.0v 199.505n 1.8v 209.495n 1.8v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 0.0v 239.495n 0.0v 239.505n 0.0v 249.495n 0.0v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 0.0v 279.495n 0.0v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 0.0v 309.495n 0.0v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 0.0v 339.495n 0.0v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 0.0v 389.495n 0.0v 389.505n 0.0v 399.495n 0.0v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 0.0v 429.495n 0.0v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 1.8v 479.495n 1.8v 479.505n 0.0v 489.495n 0.0v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 0.0v 559.495n 0.0v 559.505n 0.0v 569.495n 0.0v 569.505n 0.0v 579.495n 0.0v 579.505n 0.0v 589.495n 0.0v 589.505n 1.8v 599.495n 1.8v 599.505n 0.0v 609.495n 0.0v 609.505n 0.0v 619.495n 0.0v 619.505n 0.0v 629.495n 0.0v 629.505n 0.0v 639.495n 0.0v 639.505n 1.8v 649.495n 1.8v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 1.8v 689.495n 1.8v 689.505n 0.0v 699.495n 0.0v 699.505n 0.0v 709.495n 0.0v 709.505n 1.8v 719.495n 1.8v 719.505n 0.0v 729.495n 0.0v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 0.0v 759.495n 0.0v 759.505n 0.0v 769.495n 0.0v 769.505n 0.0v 779.495n 0.0v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 0.0v 809.495n 0.0v 809.505n 0.0v 819.495n 0.0v 819.505n 0.0v 829.495n 0.0v 829.505n 1.8v 839.495n 1.8v 839.505n 0.0v 849.495n 0.0v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 0.0v 929.495n 0.0v 929.505n 0.0v 939.495n 0.0v 939.505n 0.0v 949.495n 0.0v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 0.0v 989.495n 0.0v 989.505n 0.0v 999.495n 0.0v 999.505n 1.8v 1009.495n 1.8v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 0.0v 1069.495n 0.0v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 0.0v 1089.495n 0.0v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 0.0v 1249.495n 0.0v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 0.0v 1489.495n 0.0v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 0.0v 1599.495n 0.0v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 0.0v 1659.495n 0.0v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 0.0v 1849.495n 0.0v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 0.0v 1889.495n 0.0v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 0.0v 1919.495n 0.0v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 0.0v 1969.495n 0.0v 1969.505n 0.0v 1979.495n 0.0v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 1.8v )
* (time, data): [(0, 1), (10, 0), (20, 0), (30, 0), (40, 0), (50, 0), (60, 0), (70, 0), (80, 1), (90, 1), (100, 1), (110, 0), (120, 0), (130, 0), (140, 0), (150, 0), (160, 0), (170, 1), (180, 1), (190, 1), (200, 0), (210, 0), (220, 0), (230, 1), (240, 1), (250, 0), (260, 0), (270, 0), (280, 0), (290, 1), (300, 1), (310, 0), (320, 0), (330, 1), (340, 0), (350, 0), (360, 0), (370, 0), (380, 1), (390, 1), (400, 0), (410, 0), (420, 1), (430, 0), (440, 0), (450, 0), (460, 0), (470, 0), (480, 0), (490, 0), (500, 0), (510, 0), (520, 0), (530, 1), (540, 1), (550, 1), (560, 1), (570, 0), (580, 0), (590, 0), (600, 1), (610, 0), (620, 1), (630, 1), (640, 0), (650, 0), (660, 0), (670, 0), (680, 0), (690, 0), (700, 1), (710, 0), (720, 1), (730, 0), (740, 0), (750, 1), (760, 1), (770, 0), (780, 1), (790, 0), (800, 0), (810, 1), (820, 0), (830, 0), (840, 0), (850, 0), (860, 1), (870, 1), (880, 0), (890, 1), (900, 0), (910, 0), (920, 0), (930, 0), (940, 1), (950, 0), (960, 0), (970, 0), (980, 1), (990, 0), (1000, 0), (1010, 0), (1020, 0), (1030, 0), (1040, 0), (1050, 0), (1060, 1), (1070, 0), (1080, 1), (1090, 0), (1100, 0), (1110, 0), (1120, 0), (1130, 1), (1140, 0), (1150, 0), (1160, 0), (1170, 0), (1180, 1), (1190, 0), (1200, 0), (1210, 0), (1220, 0), (1230, 0), (1240, 1), (1250, 1), (1260, 0), (1270, 0), (1280, 0), (1290, 0), (1300, 0), (1310, 0), (1320, 1), (1330, 0), (1340, 1), (1350, 0), (1360, 0), (1370, 0), (1380, 0), (1390, 0), (1400, 0), (1410, 0), (1420, 1), (1430, 1), (1440, 1), (1450, 0), (1460, 0), (1470, 0), (1480, 1), (1490, 0), (1500, 0), (1510, 0), (1520, 1), (1530, 0), (1540, 0), (1550, 0), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 0), (1610, 0), (1620, 0), (1630, 0), (1640, 0), (1650, 1), (1660, 0), (1670, 0), (1680, 0), (1690, 0), (1700, 0), (1710, 1), (1720, 0), (1730, 0), (1740, 0), (1750, 0), (1760, 0), (1770, 0), (1780, 0), (1790, 0), (1800, 0), (1810, 0), (1820, 0), (1830, 0), (1840, 1), (1850, 0), (1860, 0), (1870, 0), (1880, 1), (1890, 1), (1900, 0), (1910, 1), (1920, 0), (1930, 1), (1940, 1), (1950, 0), (1960, 1), (1970, 1), (1980, 0), (1990, 0), (2000, 0), (2010, 0), (2020, 1), (2030, 0), (2040, 1), (2050, 1)]
VCSB1 CSB1 0 PWL (0n 1.8v 9.495n 1.8v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 0.0v 49.495n 0.0v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 0.0v 79.495n 0.0v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 1.8v 109.495n 1.8v 109.505n 0.0v 119.495n 0.0v 119.505n 0.0v 129.495n 0.0v 129.505n 0.0v 139.495n 0.0v 139.505n 0.0v 149.495n 0.0v 149.505n 0.0v 159.495n 0.0v 159.505n 0.0v 169.495n 0.0v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 0.0v 209.495n 0.0v 209.505n 0.0v 219.495n 0.0v 219.505n 0.0v 229.495n 0.0v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 0.0v 259.495n 0.0v 259.505n 0.0v 269.495n 0.0v 269.505n 0.0v 279.495n 0.0v 279.505n 0.0v 289.495n 0.0v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 0.0v 319.495n 0.0v 319.505n 0.0v 329.495n 0.0v 329.505n 1.8v 339.495n 1.8v 339.505n 0.0v 349.495n 0.0v 349.505n 0.0v 359.495n 0.0v 359.505n 0.0v 369.495n 0.0v 369.505n 0.0v 379.495n 0.0v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 0.0v 409.495n 0.0v 409.505n 0.0v 419.495n 0.0v 419.505n 1.8v 429.495n 1.8v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 0.0v 469.495n 0.0v 469.505n 0.0v 479.495n 0.0v 479.505n 0.0v 489.495n 0.0v 489.505n 0.0v 499.495n 0.0v 499.505n 0.0v 509.495n 0.0v 509.505n 0.0v 519.495n 0.0v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 0.0v 579.495n 0.0v 579.505n 0.0v 589.495n 0.0v 589.505n 0.0v 599.495n 0.0v 599.505n 1.8v 609.495n 1.8v 609.505n 0.0v 619.495n 0.0v 619.505n 1.8v 629.495n 1.8v 629.505n 1.8v 639.495n 1.8v 639.505n 0.0v 649.495n 0.0v 649.505n 0.0v 659.495n 0.0v 659.505n 0.0v 669.495n 0.0v 669.505n 0.0v 679.495n 0.0v 679.505n 0.0v 689.495n 0.0v 689.505n 0.0v 699.495n 0.0v 699.505n 1.8v 709.495n 1.8v 709.505n 0.0v 719.495n 0.0v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 0.0v 749.495n 0.0v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 0.0v 779.495n 0.0v 779.505n 1.8v 789.495n 1.8v 789.505n 0.0v 799.495n 0.0v 799.505n 0.0v 809.495n 0.0v 809.505n 1.8v 819.495n 1.8v 819.505n 0.0v 829.495n 0.0v 829.505n 0.0v 839.495n 0.0v 839.505n 0.0v 849.495n 0.0v 849.505n 0.0v 859.495n 0.0v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 0.0v 889.495n 0.0v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 0.0v 919.495n 0.0v 919.505n 0.0v 929.495n 0.0v 929.505n 0.0v 939.495n 0.0v 939.505n 1.8v 949.495n 1.8v 949.505n 0.0v 959.495n 0.0v 959.505n 0.0v 969.495n 0.0v 969.505n 0.0v 979.495n 0.0v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 0.0v 1009.495n 0.0v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 0.0v 1029.495n 0.0v 1029.505n 0.0v 1039.495n 0.0v 1039.505n 0.0v 1049.495n 0.0v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 0.0v 1109.495n 0.0v 1109.505n 0.0v 1119.495n 0.0v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 0.0v 1159.495n 0.0v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 0.0v 1179.495n 0.0v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 0.0v 1209.495n 0.0v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 0.0v 1229.495n 0.0v 1229.505n 0.0v 1239.495n 0.0v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 0.0v 1279.495n 0.0v 1279.505n 0.0v 1289.495n 0.0v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 0.0v 1359.495n 0.0v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 0.0v 1459.495n 0.0v 1459.505n 0.0v 1469.495n 0.0v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 0.0v 1499.495n 0.0v 1499.505n 0.0v 1509.495n 0.0v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 0.0v 1559.495n 0.0v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 0.0v 1639.495n 0.0v 1639.505n 0.0v 1649.495n 0.0v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 0.0v 1669.495n 0.0v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 0.0v 1689.495n 0.0v 1689.505n 0.0v 1699.495n 0.0v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 0.0v 1739.495n 0.0v 1739.505n 0.0v 1749.495n 0.0v 1749.505n 0.0v 1759.495n 0.0v 1759.505n 0.0v 1769.495n 0.0v 1769.505n 0.0v 1779.495n 0.0v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 0.0v 1799.495n 0.0v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 0.0v 1819.495n 0.0v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 0.0v 1839.495n 0.0v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 0.0v 1859.495n 0.0v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 0.0v 1959.495n 0.0v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 0.0v 1989.495n 0.0v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 0.0v 2009.495n 0.0v 2009.505n 0.0v 2019.495n 0.0v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 0.0v 2039.495n 0.0v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* (time, data): [(0, 1), (10, 0), (20, 0), (30, 0), (40, 1), (50, 1), (60, 1), (70, 1), (80, 1), (90, 1), (100, 0), (110, 0), (120, 1), (130, 1), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 0), (200, 1), (210, 1), (220, 1), (230, 1), (240, 0), (250, 1), (260, 1), (270, 0), (280, 1), (290, 1), (300, 1), (310, 1), (320, 1), (330, 1), (340, 1), (350, 1), (360, 1), (370, 0), (380, 1), (390, 0), (400, 1), (410, 1), (420, 0), (430, 1), (440, 0), (450, 0), (460, 1), (470, 1), (480, 1), (490, 1), (500, 1), (510, 1), (520, 0), (530, 0), (540, 0), (550, 1), (560, 1), (570, 0), (580, 1), (590, 1), (600, 1), (610, 1), (620, 1), (630, 0), (640, 1), (650, 1), (660, 0), (670, 1), (680, 1), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 1), (750, 1), (760, 0), (770, 1), (780, 1), (790, 1), (800, 1), (810, 0), (820, 1), (830, 1), (840, 1), (850, 1), (860, 1), (870, 1), (880, 1), (890, 1), (900, 1), (910, 0), (920, 0), (930, 1), (940, 1), (950, 0), (960, 1), (970, 1), (980, 1), (990, 0), (1000, 1), (1010, 0), (1020, 1), (1030, 1), (1040, 1), (1050, 0), (1060, 1), (1070, 1), (1080, 1), (1090, 0), (1100, 1), (1110, 1), (1120, 0), (1130, 1), (1140, 1), (1150, 1), (1160, 0), (1170, 1), (1180, 0), (1190, 1), (1200, 1), (1210, 1), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 0), (1270, 1), (1280, 1), (1290, 0), (1300, 0), (1310, 1), (1320, 0), (1330, 1), (1340, 1), (1350, 1), (1360, 0), (1370, 1), (1380, 1), (1390, 0), (1400, 0), (1410, 0), (1420, 0), (1430, 0), (1440, 0), (1450, 1), (1460, 1), (1470, 0), (1480, 1), (1490, 1), (1500, 1), (1510, 0), (1520, 0), (1530, 1), (1540, 1), (1550, 1), (1560, 1), (1570, 1), (1580, 0), (1590, 1), (1600, 1), (1610, 0), (1620, 0), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 1), (1690, 1), (1700, 0), (1710, 0), (1720, 0), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 1), (1780, 1), (1790, 1), (1800, 1), (1810, 1), (1820, 1), (1830, 1), (1840, 1), (1850, 1), (1860, 1), (1870, 0), (1880, 1), (1890, 1), (1900, 1), (1910, 1), (1920, 1), (1930, 0), (1940, 1), (1950, 1), (1960, 1), (1970, 1), (1980, 1), (1990, 1), (2000, 1), (2010, 1), (2020, 0), (2030, 1), (2040, 0), (2050, 1)]
VWEB0 WEB0 0 PWL (0n 1.8v 9.495n 1.8v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 1.8v 49.495n 1.8v 49.505n 1.8v 59.495n 1.8v 59.505n 1.8v 69.495n 1.8v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 0.0v 109.495n 0.0v 109.505n 0.0v 119.495n 0.0v 119.505n 1.8v 129.495n 1.8v 129.505n 1.8v 139.495n 1.8v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 0.0v 199.495n 0.0v 199.505n 1.8v 209.495n 1.8v 209.505n 1.8v 219.495n 1.8v 219.505n 1.8v 229.495n 1.8v 229.505n 1.8v 239.495n 1.8v 239.505n 0.0v 249.495n 0.0v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 0.0v 279.495n 0.0v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 1.8v 319.495n 1.8v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 1.8v 369.495n 1.8v 369.505n 0.0v 379.495n 0.0v 379.505n 1.8v 389.495n 1.8v 389.505n 0.0v 399.495n 0.0v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 0.0v 429.495n 0.0v 429.505n 1.8v 439.495n 1.8v 439.505n 0.0v 449.495n 0.0v 449.505n 0.0v 459.495n 0.0v 459.505n 1.8v 469.495n 1.8v 469.505n 1.8v 479.495n 1.8v 479.505n 1.8v 489.495n 1.8v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 0.0v 529.495n 0.0v 529.505n 0.0v 539.495n 0.0v 539.505n 0.0v 549.495n 0.0v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 0.0v 579.495n 0.0v 579.505n 1.8v 589.495n 1.8v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 0.0v 639.495n 0.0v 639.505n 1.8v 649.495n 1.8v 649.505n 1.8v 659.495n 1.8v 659.505n 0.0v 669.495n 0.0v 669.505n 1.8v 679.495n 1.8v 679.505n 1.8v 689.495n 1.8v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 0.0v 769.495n 0.0v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 0.0v 819.495n 0.0v 819.505n 1.8v 829.495n 1.8v 829.505n 1.8v 839.495n 1.8v 839.505n 1.8v 849.495n 1.8v 849.505n 1.8v 859.495n 1.8v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 1.8v 909.495n 1.8v 909.505n 0.0v 919.495n 0.0v 919.505n 0.0v 929.495n 0.0v 929.505n 1.8v 939.495n 1.8v 939.505n 1.8v 949.495n 1.8v 949.505n 0.0v 959.495n 0.0v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 0.0v 999.495n 0.0v 999.505n 1.8v 1009.495n 1.8v 1009.505n 0.0v 1019.495n 0.0v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 1.8v 1079.495n 1.8v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 0.0v 1099.495n 0.0v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 0.0v 1129.495n 0.0v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 1.8v 1149.495n 1.8v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 0.0v 1169.495n 0.0v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 0.0v 1189.495n 0.0v 1189.505n 1.8v 1199.495n 1.8v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 1.8v 1219.495n 1.8v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 0.0v 1269.495n 0.0v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 0.0v 1299.495n 0.0v 1299.505n 0.0v 1309.495n 0.0v 1309.505n 1.8v 1319.495n 1.8v 1319.505n 0.0v 1329.495n 0.0v 1329.505n 1.8v 1339.495n 1.8v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 1.8v 1379.495n 1.8v 1379.505n 1.8v 1389.495n 1.8v 1389.505n 0.0v 1399.495n 0.0v 1399.505n 0.0v 1409.495n 0.0v 1409.505n 0.0v 1419.495n 0.0v 1419.505n 0.0v 1429.495n 0.0v 1429.505n 0.0v 1439.495n 0.0v 1439.505n 0.0v 1449.495n 0.0v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 0.0v 1479.495n 0.0v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 1.8v 1509.495n 1.8v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 0.0v 1529.495n 0.0v 1529.505n 1.8v 1539.495n 1.8v 1539.505n 1.8v 1549.495n 1.8v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 0.0v 1589.495n 0.0v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 1.8v 1609.495n 1.8v 1609.505n 0.0v 1619.495n 0.0v 1619.505n 0.0v 1629.495n 0.0v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 0.0v 1709.495n 0.0v 1709.505n 0.0v 1719.495n 0.0v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 1.8v 1779.495n 1.8v 1779.505n 1.8v 1789.495n 1.8v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 1.8v 1809.495n 1.8v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 1.8v 1829.495n 1.8v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 1.8v 1869.495n 1.8v 1869.505n 0.0v 1879.495n 0.0v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 1.8v 1909.495n 1.8v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 1.8v 1929.495n 1.8v 1929.505n 0.0v 1939.495n 0.0v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 1.8v 1999.495n 1.8v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 0.0v 2029.495n 0.0v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 0.0v 2049.495n 0.0v 2049.505n 1.8v )
* (time, data): [(0, 1), (10, 0), (20, 0), (30, 0), (40, 1), (50, 0), (60, 0), (70, 1), (80, 1), (90, 1), (100, 1), (110, 0), (120, 1), (130, 0), (140, 1), (150, 1), (160, 1), (170, 1), (180, 1), (190, 1), (200, 1), (210, 1), (220, 0), (230, 1), (240, 1), (250, 1), (260, 1), (270, 1), (280, 1), (290, 1), (300, 1), (310, 0), (320, 1), (330, 1), (340, 1), (350, 1), (360, 0), (370, 0), (380, 1), (390, 1), (400, 1), (410, 1), (420, 1), (430, 0), (440, 0), (450, 1), (460, 0), (470, 1), (480, 0), (490, 1), (500, 1), (510, 1), (520, 0), (530, 1), (540, 1), (550, 1), (560, 1), (570, 1), (580, 0), (590, 1), (600, 1), (610, 1), (620, 1), (630, 1), (640, 0), (650, 1), (660, 0), (670, 1), (680, 0), (690, 1), (700, 1), (710, 1), (720, 1), (730, 0), (740, 1), (750, 1), (760, 1), (770, 1), (780, 1), (790, 1), (800, 1), (810, 1), (820, 1), (830, 0), (840, 1), (850, 0), (860, 1), (870, 1), (880, 1), (890, 1), (900, 0), (910, 1), (920, 1), (930, 0), (940, 1), (950, 1), (960, 1), (970, 1), (980, 1), (990, 1), (1000, 1), (1010, 1), (1020, 1), (1030, 1), (1040, 1), (1050, 0), (1060, 1), (1070, 0), (1080, 1), (1090, 1), (1100, 1), (1110, 1), (1120, 1), (1130, 1), (1140, 0), (1150, 1), (1160, 1), (1170, 1), (1180, 1), (1190, 0), (1200, 1), (1210, 0), (1220, 1), (1230, 1), (1240, 1), (1250, 1), (1260, 1), (1270, 1), (1280, 1), (1290, 1), (1300, 1), (1310, 0), (1320, 1), (1330, 0), (1340, 1), (1350, 1), (1360, 0), (1370, 0), (1380, 0), (1390, 1), (1400, 1), (1410, 1), (1420, 1), (1430, 1), (1440, 1), (1450, 1), (1460, 1), (1470, 1), (1480, 1), (1490, 1), (1500, 0), (1510, 0), (1520, 1), (1530, 0), (1540, 0), (1550, 1), (1560, 1), (1570, 1), (1580, 1), (1590, 1), (1600, 0), (1610, 1), (1620, 1), (1630, 1), (1640, 1), (1650, 1), (1660, 1), (1670, 0), (1680, 1), (1690, 1), (1700, 1), (1710, 1), (1720, 0), (1730, 1), (1740, 1), (1750, 1), (1760, 1), (1770, 1), (1780, 0), (1790, 1), (1800, 0), (1810, 1), (1820, 0), (1830, 1), (1840, 1), (1850, 1), (1860, 0), (1870, 1), (1880, 1), (1890, 1), (1900, 0), (1910, 1), (1920, 0), (1930, 1), (1940, 1), (1950, 1), (1960, 1), (1970, 1), (1980, 1), (1990, 0), (2000, 1), (2010, 1), (2020, 1), (2030, 1), (2040, 1), (2050, 1)]
VWEB1 WEB1 0 PWL (0n 1.8v 9.495n 1.8v 9.505n 0.0v 19.495n 0.0v 19.505n 0.0v 29.495n 0.0v 29.505n 0.0v 39.495n 0.0v 39.505n 1.8v 49.495n 1.8v 49.505n 0.0v 59.495n 0.0v 59.505n 0.0v 69.495n 0.0v 69.505n 1.8v 79.495n 1.8v 79.505n 1.8v 89.495n 1.8v 89.505n 1.8v 99.495n 1.8v 99.505n 1.8v 109.495n 1.8v 109.505n 0.0v 119.495n 0.0v 119.505n 1.8v 129.495n 1.8v 129.505n 0.0v 139.495n 0.0v 139.505n 1.8v 149.495n 1.8v 149.505n 1.8v 159.495n 1.8v 159.505n 1.8v 169.495n 1.8v 169.505n 1.8v 179.495n 1.8v 179.505n 1.8v 189.495n 1.8v 189.505n 1.8v 199.495n 1.8v 199.505n 1.8v 209.495n 1.8v 209.505n 1.8v 219.495n 1.8v 219.505n 0.0v 229.495n 0.0v 229.505n 1.8v 239.495n 1.8v 239.505n 1.8v 249.495n 1.8v 249.505n 1.8v 259.495n 1.8v 259.505n 1.8v 269.495n 1.8v 269.505n 1.8v 279.495n 1.8v 279.505n 1.8v 289.495n 1.8v 289.505n 1.8v 299.495n 1.8v 299.505n 1.8v 309.495n 1.8v 309.505n 0.0v 319.495n 0.0v 319.505n 1.8v 329.495n 1.8v 329.505n 1.8v 339.495n 1.8v 339.505n 1.8v 349.495n 1.8v 349.505n 1.8v 359.495n 1.8v 359.505n 0.0v 369.495n 0.0v 369.505n 0.0v 379.495n 0.0v 379.505n 1.8v 389.495n 1.8v 389.505n 1.8v 399.495n 1.8v 399.505n 1.8v 409.495n 1.8v 409.505n 1.8v 419.495n 1.8v 419.505n 1.8v 429.495n 1.8v 429.505n 0.0v 439.495n 0.0v 439.505n 0.0v 449.495n 0.0v 449.505n 1.8v 459.495n 1.8v 459.505n 0.0v 469.495n 0.0v 469.505n 1.8v 479.495n 1.8v 479.505n 0.0v 489.495n 0.0v 489.505n 1.8v 499.495n 1.8v 499.505n 1.8v 509.495n 1.8v 509.505n 1.8v 519.495n 1.8v 519.505n 0.0v 529.495n 0.0v 529.505n 1.8v 539.495n 1.8v 539.505n 1.8v 549.495n 1.8v 549.505n 1.8v 559.495n 1.8v 559.505n 1.8v 569.495n 1.8v 569.505n 1.8v 579.495n 1.8v 579.505n 0.0v 589.495n 0.0v 589.505n 1.8v 599.495n 1.8v 599.505n 1.8v 609.495n 1.8v 609.505n 1.8v 619.495n 1.8v 619.505n 1.8v 629.495n 1.8v 629.505n 1.8v 639.495n 1.8v 639.505n 0.0v 649.495n 0.0v 649.505n 1.8v 659.495n 1.8v 659.505n 0.0v 669.495n 0.0v 669.505n 1.8v 679.495n 1.8v 679.505n 0.0v 689.495n 0.0v 689.505n 1.8v 699.495n 1.8v 699.505n 1.8v 709.495n 1.8v 709.505n 1.8v 719.495n 1.8v 719.505n 1.8v 729.495n 1.8v 729.505n 0.0v 739.495n 0.0v 739.505n 1.8v 749.495n 1.8v 749.505n 1.8v 759.495n 1.8v 759.505n 1.8v 769.495n 1.8v 769.505n 1.8v 779.495n 1.8v 779.505n 1.8v 789.495n 1.8v 789.505n 1.8v 799.495n 1.8v 799.505n 1.8v 809.495n 1.8v 809.505n 1.8v 819.495n 1.8v 819.505n 1.8v 829.495n 1.8v 829.505n 0.0v 839.495n 0.0v 839.505n 1.8v 849.495n 1.8v 849.505n 0.0v 859.495n 0.0v 859.505n 1.8v 869.495n 1.8v 869.505n 1.8v 879.495n 1.8v 879.505n 1.8v 889.495n 1.8v 889.505n 1.8v 899.495n 1.8v 899.505n 0.0v 909.495n 0.0v 909.505n 1.8v 919.495n 1.8v 919.505n 1.8v 929.495n 1.8v 929.505n 0.0v 939.495n 0.0v 939.505n 1.8v 949.495n 1.8v 949.505n 1.8v 959.495n 1.8v 959.505n 1.8v 969.495n 1.8v 969.505n 1.8v 979.495n 1.8v 979.505n 1.8v 989.495n 1.8v 989.505n 1.8v 999.495n 1.8v 999.505n 1.8v 1009.495n 1.8v 1009.505n 1.8v 1019.495n 1.8v 1019.505n 1.8v 1029.495n 1.8v 1029.505n 1.8v 1039.495n 1.8v 1039.505n 1.8v 1049.495n 1.8v 1049.505n 0.0v 1059.495n 0.0v 1059.505n 1.8v 1069.495n 1.8v 1069.505n 0.0v 1079.495n 0.0v 1079.505n 1.8v 1089.495n 1.8v 1089.505n 1.8v 1099.495n 1.8v 1099.505n 1.8v 1109.495n 1.8v 1109.505n 1.8v 1119.495n 1.8v 1119.505n 1.8v 1129.495n 1.8v 1129.505n 1.8v 1139.495n 1.8v 1139.505n 0.0v 1149.495n 0.0v 1149.505n 1.8v 1159.495n 1.8v 1159.505n 1.8v 1169.495n 1.8v 1169.505n 1.8v 1179.495n 1.8v 1179.505n 1.8v 1189.495n 1.8v 1189.505n 0.0v 1199.495n 0.0v 1199.505n 1.8v 1209.495n 1.8v 1209.505n 0.0v 1219.495n 0.0v 1219.505n 1.8v 1229.495n 1.8v 1229.505n 1.8v 1239.495n 1.8v 1239.505n 1.8v 1249.495n 1.8v 1249.505n 1.8v 1259.495n 1.8v 1259.505n 1.8v 1269.495n 1.8v 1269.505n 1.8v 1279.495n 1.8v 1279.505n 1.8v 1289.495n 1.8v 1289.505n 1.8v 1299.495n 1.8v 1299.505n 1.8v 1309.495n 1.8v 1309.505n 0.0v 1319.495n 0.0v 1319.505n 1.8v 1329.495n 1.8v 1329.505n 0.0v 1339.495n 0.0v 1339.505n 1.8v 1349.495n 1.8v 1349.505n 1.8v 1359.495n 1.8v 1359.505n 0.0v 1369.495n 0.0v 1369.505n 0.0v 1379.495n 0.0v 1379.505n 0.0v 1389.495n 0.0v 1389.505n 1.8v 1399.495n 1.8v 1399.505n 1.8v 1409.495n 1.8v 1409.505n 1.8v 1419.495n 1.8v 1419.505n 1.8v 1429.495n 1.8v 1429.505n 1.8v 1439.495n 1.8v 1439.505n 1.8v 1449.495n 1.8v 1449.505n 1.8v 1459.495n 1.8v 1459.505n 1.8v 1469.495n 1.8v 1469.505n 1.8v 1479.495n 1.8v 1479.505n 1.8v 1489.495n 1.8v 1489.505n 1.8v 1499.495n 1.8v 1499.505n 0.0v 1509.495n 0.0v 1509.505n 0.0v 1519.495n 0.0v 1519.505n 1.8v 1529.495n 1.8v 1529.505n 0.0v 1539.495n 0.0v 1539.505n 0.0v 1549.495n 0.0v 1549.505n 1.8v 1559.495n 1.8v 1559.505n 1.8v 1569.495n 1.8v 1569.505n 1.8v 1579.495n 1.8v 1579.505n 1.8v 1589.495n 1.8v 1589.505n 1.8v 1599.495n 1.8v 1599.505n 0.0v 1609.495n 0.0v 1609.505n 1.8v 1619.495n 1.8v 1619.505n 1.8v 1629.495n 1.8v 1629.505n 1.8v 1639.495n 1.8v 1639.505n 1.8v 1649.495n 1.8v 1649.505n 1.8v 1659.495n 1.8v 1659.505n 1.8v 1669.495n 1.8v 1669.505n 0.0v 1679.495n 0.0v 1679.505n 1.8v 1689.495n 1.8v 1689.505n 1.8v 1699.495n 1.8v 1699.505n 1.8v 1709.495n 1.8v 1709.505n 1.8v 1719.495n 1.8v 1719.505n 0.0v 1729.495n 0.0v 1729.505n 1.8v 1739.495n 1.8v 1739.505n 1.8v 1749.495n 1.8v 1749.505n 1.8v 1759.495n 1.8v 1759.505n 1.8v 1769.495n 1.8v 1769.505n 1.8v 1779.495n 1.8v 1779.505n 0.0v 1789.495n 0.0v 1789.505n 1.8v 1799.495n 1.8v 1799.505n 0.0v 1809.495n 0.0v 1809.505n 1.8v 1819.495n 1.8v 1819.505n 0.0v 1829.495n 0.0v 1829.505n 1.8v 1839.495n 1.8v 1839.505n 1.8v 1849.495n 1.8v 1849.505n 1.8v 1859.495n 1.8v 1859.505n 0.0v 1869.495n 0.0v 1869.505n 1.8v 1879.495n 1.8v 1879.505n 1.8v 1889.495n 1.8v 1889.505n 1.8v 1899.495n 1.8v 1899.505n 0.0v 1909.495n 0.0v 1909.505n 1.8v 1919.495n 1.8v 1919.505n 0.0v 1929.495n 0.0v 1929.505n 1.8v 1939.495n 1.8v 1939.505n 1.8v 1949.495n 1.8v 1949.505n 1.8v 1959.495n 1.8v 1959.505n 1.8v 1969.495n 1.8v 1969.505n 1.8v 1979.495n 1.8v 1979.505n 1.8v 1989.495n 1.8v 1989.505n 0.0v 1999.495n 0.0v 1999.505n 1.8v 2009.495n 1.8v 2009.505n 1.8v 2019.495n 1.8v 2019.505n 1.8v 2029.495n 1.8v 2029.505n 1.8v 2039.495n 1.8v 2039.505n 1.8v 2049.495n 1.8v 2049.505n 1.8v )
* PULSE: period=10
Vclk0 clk0 0 PULSE (0 1.8 9.995n 0.01n 0.01n 4.99n 10n)
* PULSE: period=10
Vclk1 clk1 0 PULSE (0 1.8 9.995n 0.01n 0.01n 4.99n 10n)

 * Generation of dout measurements
* CHECK dout0_0 Vdout0_0ck4 = 1.8 time = 50
.meas tran vdout0_0ck4 FIND v(dout0_0) AT=50.05n

* CHECK dout0_1 Vdout0_1ck4 = 1.8 time = 50
.meas tran vdout0_1ck4 FIND v(dout0_1) AT=50.05n

* CHECK dout0_2 Vdout0_2ck4 = 1.8 time = 50
.meas tran vdout0_2ck4 FIND v(dout0_2) AT=50.05n

* CHECK dout0_3 Vdout0_3ck4 = 0 time = 50
.meas tran vdout0_3ck4 FIND v(dout0_3) AT=50.05n

* CHECK dout0_4 Vdout0_4ck4 = 1.8 time = 50
.meas tran vdout0_4ck4 FIND v(dout0_4) AT=50.05n

* CHECK dout0_5 Vdout0_5ck4 = 1.8 time = 50
.meas tran vdout0_5ck4 FIND v(dout0_5) AT=50.05n

* CHECK dout0_6 Vdout0_6ck4 = 0 time = 50
.meas tran vdout0_6ck4 FIND v(dout0_6) AT=50.05n

* CHECK dout0_7 Vdout0_7ck4 = 0 time = 50
.meas tran vdout0_7ck4 FIND v(dout0_7) AT=50.05n

* CHECK dout1_0 Vdout1_0ck4 = 1.8 time = 50
.meas tran vdout1_0ck4 FIND v(dout1_0) AT=50.05n

* CHECK dout1_1 Vdout1_1ck4 = 1.8 time = 50
.meas tran vdout1_1ck4 FIND v(dout1_1) AT=50.05n

* CHECK dout1_2 Vdout1_2ck4 = 1.8 time = 50
.meas tran vdout1_2ck4 FIND v(dout1_2) AT=50.05n

* CHECK dout1_3 Vdout1_3ck4 = 0 time = 50
.meas tran vdout1_3ck4 FIND v(dout1_3) AT=50.05n

* CHECK dout1_4 Vdout1_4ck4 = 1.8 time = 50
.meas tran vdout1_4ck4 FIND v(dout1_4) AT=50.05n

* CHECK dout1_5 Vdout1_5ck4 = 1.8 time = 50
.meas tran vdout1_5ck4 FIND v(dout1_5) AT=50.05n

* CHECK dout1_6 Vdout1_6ck4 = 1.8 time = 50
.meas tran vdout1_6ck4 FIND v(dout1_6) AT=50.05n

* CHECK dout1_7 Vdout1_7ck4 = 1.8 time = 50
.meas tran vdout1_7ck4 FIND v(dout1_7) AT=50.05n

* CHECK dout0_0 Vdout0_0ck5 = 1.8 time = 60
.meas tran vdout0_0ck5 FIND v(dout0_0) AT=60.05n

* CHECK dout0_1 Vdout0_1ck5 = 1.8 time = 60
.meas tran vdout0_1ck5 FIND v(dout0_1) AT=60.05n

* CHECK dout0_2 Vdout0_2ck5 = 1.8 time = 60
.meas tran vdout0_2ck5 FIND v(dout0_2) AT=60.05n

* CHECK dout0_3 Vdout0_3ck5 = 0 time = 60
.meas tran vdout0_3ck5 FIND v(dout0_3) AT=60.05n

* CHECK dout0_4 Vdout0_4ck5 = 1.8 time = 60
.meas tran vdout0_4ck5 FIND v(dout0_4) AT=60.05n

* CHECK dout0_5 Vdout0_5ck5 = 1.8 time = 60
.meas tran vdout0_5ck5 FIND v(dout0_5) AT=60.05n

* CHECK dout0_6 Vdout0_6ck5 = 0 time = 60
.meas tran vdout0_6ck5 FIND v(dout0_6) AT=60.05n

* CHECK dout0_7 Vdout0_7ck5 = 0 time = 60
.meas tran vdout0_7ck5 FIND v(dout0_7) AT=60.05n

* CHECK dout0_0 Vdout0_0ck7 = 1.8 time = 80
.meas tran vdout0_0ck7 FIND v(dout0_0) AT=80.05n

* CHECK dout0_1 Vdout0_1ck7 = 0 time = 80
.meas tran vdout0_1ck7 FIND v(dout0_1) AT=80.05n

* CHECK dout0_2 Vdout0_2ck7 = 0 time = 80
.meas tran vdout0_2ck7 FIND v(dout0_2) AT=80.05n

* CHECK dout0_3 Vdout0_3ck7 = 1.8 time = 80
.meas tran vdout0_3ck7 FIND v(dout0_3) AT=80.05n

* CHECK dout0_4 Vdout0_4ck7 = 0 time = 80
.meas tran vdout0_4ck7 FIND v(dout0_4) AT=80.05n

* CHECK dout0_5 Vdout0_5ck7 = 0 time = 80
.meas tran vdout0_5ck7 FIND v(dout0_5) AT=80.05n

* CHECK dout0_6 Vdout0_6ck7 = 1.8 time = 80
.meas tran vdout0_6ck7 FIND v(dout0_6) AT=80.05n

* CHECK dout0_7 Vdout0_7ck7 = 0 time = 80
.meas tran vdout0_7ck7 FIND v(dout0_7) AT=80.05n

* CHECK dout1_0 Vdout1_0ck7 = 1.8 time = 80
.meas tran vdout1_0ck7 FIND v(dout1_0) AT=80.05n

* CHECK dout1_1 Vdout1_1ck7 = 0 time = 80
.meas tran vdout1_1ck7 FIND v(dout1_1) AT=80.05n

* CHECK dout1_2 Vdout1_2ck7 = 0 time = 80
.meas tran vdout1_2ck7 FIND v(dout1_2) AT=80.05n

* CHECK dout1_3 Vdout1_3ck7 = 1.8 time = 80
.meas tran vdout1_3ck7 FIND v(dout1_3) AT=80.05n

* CHECK dout1_4 Vdout1_4ck7 = 0 time = 80
.meas tran vdout1_4ck7 FIND v(dout1_4) AT=80.05n

* CHECK dout1_5 Vdout1_5ck7 = 0 time = 80
.meas tran vdout1_5ck7 FIND v(dout1_5) AT=80.05n

* CHECK dout1_6 Vdout1_6ck7 = 1.8 time = 80
.meas tran vdout1_6ck7 FIND v(dout1_6) AT=80.05n

* CHECK dout1_7 Vdout1_7ck7 = 0 time = 80
.meas tran vdout1_7ck7 FIND v(dout1_7) AT=80.05n

* CHECK dout0_0 Vdout0_0ck9 = 1.8 time = 100
.meas tran vdout0_0ck9 FIND v(dout0_0) AT=100.05n

* CHECK dout0_1 Vdout0_1ck9 = 0 time = 100
.meas tran vdout0_1ck9 FIND v(dout0_1) AT=100.05n

* CHECK dout0_2 Vdout0_2ck9 = 0 time = 100
.meas tran vdout0_2ck9 FIND v(dout0_2) AT=100.05n

* CHECK dout0_3 Vdout0_3ck9 = 1.8 time = 100
.meas tran vdout0_3ck9 FIND v(dout0_3) AT=100.05n

* CHECK dout0_4 Vdout0_4ck9 = 0 time = 100
.meas tran vdout0_4ck9 FIND v(dout0_4) AT=100.05n

* CHECK dout0_5 Vdout0_5ck9 = 0 time = 100
.meas tran vdout0_5ck9 FIND v(dout0_5) AT=100.05n

* CHECK dout0_6 Vdout0_6ck9 = 1.8 time = 100
.meas tran vdout0_6ck9 FIND v(dout0_6) AT=100.05n

* CHECK dout0_7 Vdout0_7ck9 = 0 time = 100
.meas tran vdout0_7ck9 FIND v(dout0_7) AT=100.05n

* CHECK dout1_0 Vdout1_0ck12 = 1.8 time = 130
.meas tran vdout1_0ck12 FIND v(dout1_0) AT=130.05n

* CHECK dout1_1 Vdout1_1ck12 = 1.8 time = 130
.meas tran vdout1_1ck12 FIND v(dout1_1) AT=130.05n

* CHECK dout1_2 Vdout1_2ck12 = 1.8 time = 130
.meas tran vdout1_2ck12 FIND v(dout1_2) AT=130.05n

* CHECK dout1_3 Vdout1_3ck12 = 1.8 time = 130
.meas tran vdout1_3ck12 FIND v(dout1_3) AT=130.05n

* CHECK dout1_4 Vdout1_4ck12 = 0 time = 130
.meas tran vdout1_4ck12 FIND v(dout1_4) AT=130.05n

* CHECK dout1_5 Vdout1_5ck12 = 1.8 time = 130
.meas tran vdout1_5ck12 FIND v(dout1_5) AT=130.05n

* CHECK dout1_6 Vdout1_6ck12 = 1.8 time = 130
.meas tran vdout1_6ck12 FIND v(dout1_6) AT=130.05n

* CHECK dout1_7 Vdout1_7ck12 = 1.8 time = 130
.meas tran vdout1_7ck12 FIND v(dout1_7) AT=130.05n

* CHECK dout0_0 Vdout0_0ck13 = 1.8 time = 140
.meas tran vdout0_0ck13 FIND v(dout0_0) AT=140.05n

* CHECK dout0_1 Vdout0_1ck13 = 1.8 time = 140
.meas tran vdout0_1ck13 FIND v(dout0_1) AT=140.05n

* CHECK dout0_2 Vdout0_2ck13 = 1.8 time = 140
.meas tran vdout0_2ck13 FIND v(dout0_2) AT=140.05n

* CHECK dout0_3 Vdout0_3ck13 = 0 time = 140
.meas tran vdout0_3ck13 FIND v(dout0_3) AT=140.05n

* CHECK dout0_4 Vdout0_4ck13 = 1.8 time = 140
.meas tran vdout0_4ck13 FIND v(dout0_4) AT=140.05n

* CHECK dout0_5 Vdout0_5ck13 = 1.8 time = 140
.meas tran vdout0_5ck13 FIND v(dout0_5) AT=140.05n

* CHECK dout0_6 Vdout0_6ck13 = 0 time = 140
.meas tran vdout0_6ck13 FIND v(dout0_6) AT=140.05n

* CHECK dout0_7 Vdout0_7ck13 = 0 time = 140
.meas tran vdout0_7ck13 FIND v(dout0_7) AT=140.05n

* CHECK dout1_0 Vdout1_0ck14 = 1.8 time = 150
.meas tran vdout1_0ck14 FIND v(dout1_0) AT=150.05n

* CHECK dout1_1 Vdout1_1ck14 = 1.8 time = 150
.meas tran vdout1_1ck14 FIND v(dout1_1) AT=150.05n

* CHECK dout1_2 Vdout1_2ck14 = 1.8 time = 150
.meas tran vdout1_2ck14 FIND v(dout1_2) AT=150.05n

* CHECK dout1_3 Vdout1_3ck14 = 0 time = 150
.meas tran vdout1_3ck14 FIND v(dout1_3) AT=150.05n

* CHECK dout1_4 Vdout1_4ck14 = 1.8 time = 150
.meas tran vdout1_4ck14 FIND v(dout1_4) AT=150.05n

* CHECK dout1_5 Vdout1_5ck14 = 0 time = 150
.meas tran vdout1_5ck14 FIND v(dout1_5) AT=150.05n

* CHECK dout1_6 Vdout1_6ck14 = 0 time = 150
.meas tran vdout1_6ck14 FIND v(dout1_6) AT=150.05n

* CHECK dout1_7 Vdout1_7ck14 = 1.8 time = 150
.meas tran vdout1_7ck14 FIND v(dout1_7) AT=150.05n

* CHECK dout1_0 Vdout1_0ck15 = 1.8 time = 160
.meas tran vdout1_0ck15 FIND v(dout1_0) AT=160.05n

* CHECK dout1_1 Vdout1_1ck15 = 0 time = 160
.meas tran vdout1_1ck15 FIND v(dout1_1) AT=160.05n

* CHECK dout1_2 Vdout1_2ck15 = 0 time = 160
.meas tran vdout1_2ck15 FIND v(dout1_2) AT=160.05n

* CHECK dout1_3 Vdout1_3ck15 = 1.8 time = 160
.meas tran vdout1_3ck15 FIND v(dout1_3) AT=160.05n

* CHECK dout1_4 Vdout1_4ck15 = 1.8 time = 160
.meas tran vdout1_4ck15 FIND v(dout1_4) AT=160.05n

* CHECK dout1_5 Vdout1_5ck15 = 1.8 time = 160
.meas tran vdout1_5ck15 FIND v(dout1_5) AT=160.05n

* CHECK dout1_6 Vdout1_6ck15 = 1.8 time = 160
.meas tran vdout1_6ck15 FIND v(dout1_6) AT=160.05n

* CHECK dout1_7 Vdout1_7ck15 = 0 time = 160
.meas tran vdout1_7ck15 FIND v(dout1_7) AT=160.05n

* CHECK dout1_0 Vdout1_0ck16 = 1.8 time = 170
.meas tran vdout1_0ck16 FIND v(dout1_0) AT=170.05n

* CHECK dout1_1 Vdout1_1ck16 = 1.8 time = 170
.meas tran vdout1_1ck16 FIND v(dout1_1) AT=170.05n

* CHECK dout1_2 Vdout1_2ck16 = 1.8 time = 170
.meas tran vdout1_2ck16 FIND v(dout1_2) AT=170.05n

* CHECK dout1_3 Vdout1_3ck16 = 0 time = 170
.meas tran vdout1_3ck16 FIND v(dout1_3) AT=170.05n

* CHECK dout1_4 Vdout1_4ck16 = 1.8 time = 170
.meas tran vdout1_4ck16 FIND v(dout1_4) AT=170.05n

* CHECK dout1_5 Vdout1_5ck16 = 0 time = 170
.meas tran vdout1_5ck16 FIND v(dout1_5) AT=170.05n

* CHECK dout1_6 Vdout1_6ck16 = 0 time = 170
.meas tran vdout1_6ck16 FIND v(dout1_6) AT=170.05n

* CHECK dout1_7 Vdout1_7ck16 = 1.8 time = 170
.meas tran vdout1_7ck16 FIND v(dout1_7) AT=170.05n

* CHECK dout0_0 Vdout0_0ck18 = 1.8 time = 190
.meas tran vdout0_0ck18 FIND v(dout0_0) AT=190.05n

* CHECK dout0_1 Vdout0_1ck18 = 0 time = 190
.meas tran vdout0_1ck18 FIND v(dout0_1) AT=190.05n

* CHECK dout0_2 Vdout0_2ck18 = 0 time = 190
.meas tran vdout0_2ck18 FIND v(dout0_2) AT=190.05n

* CHECK dout0_3 Vdout0_3ck18 = 1.8 time = 190
.meas tran vdout0_3ck18 FIND v(dout0_3) AT=190.05n

* CHECK dout0_4 Vdout0_4ck18 = 1.8 time = 190
.meas tran vdout0_4ck18 FIND v(dout0_4) AT=190.05n

* CHECK dout0_5 Vdout0_5ck18 = 1.8 time = 190
.meas tran vdout0_5ck18 FIND v(dout0_5) AT=190.05n

* CHECK dout0_6 Vdout0_6ck18 = 1.8 time = 190
.meas tran vdout0_6ck18 FIND v(dout0_6) AT=190.05n

* CHECK dout0_7 Vdout0_7ck18 = 0 time = 190
.meas tran vdout0_7ck18 FIND v(dout0_7) AT=190.05n

* CHECK dout1_0 Vdout1_0ck20 = 0 time = 210
.meas tran vdout1_0ck20 FIND v(dout1_0) AT=210.05n

* CHECK dout1_1 Vdout1_1ck20 = 0 time = 210
.meas tran vdout1_1ck20 FIND v(dout1_1) AT=210.05n

* CHECK dout1_2 Vdout1_2ck20 = 0 time = 210
.meas tran vdout1_2ck20 FIND v(dout1_2) AT=210.05n

* CHECK dout1_3 Vdout1_3ck20 = 0 time = 210
.meas tran vdout1_3ck20 FIND v(dout1_3) AT=210.05n

* CHECK dout1_4 Vdout1_4ck20 = 0 time = 210
.meas tran vdout1_4ck20 FIND v(dout1_4) AT=210.05n

* CHECK dout1_5 Vdout1_5ck20 = 0 time = 210
.meas tran vdout1_5ck20 FIND v(dout1_5) AT=210.05n

* CHECK dout1_6 Vdout1_6ck20 = 1.8 time = 210
.meas tran vdout1_6ck20 FIND v(dout1_6) AT=210.05n

* CHECK dout1_7 Vdout1_7ck20 = 1.8 time = 210
.meas tran vdout1_7ck20 FIND v(dout1_7) AT=210.05n

* CHECK dout0_0 Vdout0_0ck21 = 1.8 time = 220
.meas tran vdout0_0ck21 FIND v(dout0_0) AT=220.05n

* CHECK dout0_1 Vdout0_1ck21 = 1.8 time = 220
.meas tran vdout0_1ck21 FIND v(dout0_1) AT=220.05n

* CHECK dout0_2 Vdout0_2ck21 = 1.8 time = 220
.meas tran vdout0_2ck21 FIND v(dout0_2) AT=220.05n

* CHECK dout0_3 Vdout0_3ck21 = 0 time = 220
.meas tran vdout0_3ck21 FIND v(dout0_3) AT=220.05n

* CHECK dout0_4 Vdout0_4ck21 = 1.8 time = 220
.meas tran vdout0_4ck21 FIND v(dout0_4) AT=220.05n

* CHECK dout0_5 Vdout0_5ck21 = 0 time = 220
.meas tran vdout0_5ck21 FIND v(dout0_5) AT=220.05n

* CHECK dout0_6 Vdout0_6ck21 = 0 time = 220
.meas tran vdout0_6ck21 FIND v(dout0_6) AT=220.05n

* CHECK dout0_7 Vdout0_7ck21 = 1.8 time = 220
.meas tran vdout0_7ck21 FIND v(dout0_7) AT=220.05n

* CHECK dout1_0 Vdout1_0ck21 = 1.8 time = 220
.meas tran vdout1_0ck21 FIND v(dout1_0) AT=220.05n

* CHECK dout1_1 Vdout1_1ck21 = 1.8 time = 220
.meas tran vdout1_1ck21 FIND v(dout1_1) AT=220.05n

* CHECK dout1_2 Vdout1_2ck21 = 1.8 time = 220
.meas tran vdout1_2ck21 FIND v(dout1_2) AT=220.05n

* CHECK dout1_3 Vdout1_3ck21 = 0 time = 220
.meas tran vdout1_3ck21 FIND v(dout1_3) AT=220.05n

* CHECK dout1_4 Vdout1_4ck21 = 1.8 time = 220
.meas tran vdout1_4ck21 FIND v(dout1_4) AT=220.05n

* CHECK dout1_5 Vdout1_5ck21 = 0 time = 220
.meas tran vdout1_5ck21 FIND v(dout1_5) AT=220.05n

* CHECK dout1_6 Vdout1_6ck21 = 0 time = 220
.meas tran vdout1_6ck21 FIND v(dout1_6) AT=220.05n

* CHECK dout1_7 Vdout1_7ck21 = 1.8 time = 220
.meas tran vdout1_7ck21 FIND v(dout1_7) AT=220.05n

* CHECK dout0_0 Vdout0_0ck22 = 0 time = 230
.meas tran vdout0_0ck22 FIND v(dout0_0) AT=230.05n

* CHECK dout0_1 Vdout0_1ck22 = 0 time = 230
.meas tran vdout0_1ck22 FIND v(dout0_1) AT=230.05n

* CHECK dout0_2 Vdout0_2ck22 = 0 time = 230
.meas tran vdout0_2ck22 FIND v(dout0_2) AT=230.05n

* CHECK dout0_3 Vdout0_3ck22 = 0 time = 230
.meas tran vdout0_3ck22 FIND v(dout0_3) AT=230.05n

* CHECK dout0_4 Vdout0_4ck22 = 0 time = 230
.meas tran vdout0_4ck22 FIND v(dout0_4) AT=230.05n

* CHECK dout0_5 Vdout0_5ck22 = 0 time = 230
.meas tran vdout0_5ck22 FIND v(dout0_5) AT=230.05n

* CHECK dout0_6 Vdout0_6ck22 = 1.8 time = 230
.meas tran vdout0_6ck22 FIND v(dout0_6) AT=230.05n

* CHECK dout0_7 Vdout0_7ck22 = 1.8 time = 230
.meas tran vdout0_7ck22 FIND v(dout0_7) AT=230.05n

* CHECK dout0_0 Vdout0_0ck23 = 1.8 time = 240
.meas tran vdout0_0ck23 FIND v(dout0_0) AT=240.05n

* CHECK dout0_1 Vdout0_1ck23 = 1.8 time = 240
.meas tran vdout0_1ck23 FIND v(dout0_1) AT=240.05n

* CHECK dout0_2 Vdout0_2ck23 = 0 time = 240
.meas tran vdout0_2ck23 FIND v(dout0_2) AT=240.05n

* CHECK dout0_3 Vdout0_3ck23 = 1.8 time = 240
.meas tran vdout0_3ck23 FIND v(dout0_3) AT=240.05n

* CHECK dout0_4 Vdout0_4ck23 = 0 time = 240
.meas tran vdout0_4ck23 FIND v(dout0_4) AT=240.05n

* CHECK dout0_5 Vdout0_5ck23 = 1.8 time = 240
.meas tran vdout0_5ck23 FIND v(dout0_5) AT=240.05n

* CHECK dout0_6 Vdout0_6ck23 = 1.8 time = 240
.meas tran vdout0_6ck23 FIND v(dout0_6) AT=240.05n

* CHECK dout0_7 Vdout0_7ck23 = 1.8 time = 240
.meas tran vdout0_7ck23 FIND v(dout0_7) AT=240.05n

* CHECK dout1_0 Vdout1_0ck25 = 1.8 time = 260
.meas tran vdout1_0ck25 FIND v(dout1_0) AT=260.05n

* CHECK dout1_1 Vdout1_1ck25 = 1.8 time = 260
.meas tran vdout1_1ck25 FIND v(dout1_1) AT=260.05n

* CHECK dout1_2 Vdout1_2ck25 = 0 time = 260
.meas tran vdout1_2ck25 FIND v(dout1_2) AT=260.05n

* CHECK dout1_3 Vdout1_3ck25 = 0 time = 260
.meas tran vdout1_3ck25 FIND v(dout1_3) AT=260.05n

* CHECK dout1_4 Vdout1_4ck25 = 0 time = 260
.meas tran vdout1_4ck25 FIND v(dout1_4) AT=260.05n

* CHECK dout1_5 Vdout1_5ck25 = 1.8 time = 260
.meas tran vdout1_5ck25 FIND v(dout1_5) AT=260.05n

* CHECK dout1_6 Vdout1_6ck25 = 0 time = 260
.meas tran vdout1_6ck25 FIND v(dout1_6) AT=260.05n

* CHECK dout1_7 Vdout1_7ck25 = 1.8 time = 260
.meas tran vdout1_7ck25 FIND v(dout1_7) AT=260.05n

* CHECK dout1_0 Vdout1_0ck26 = 0 time = 270
.meas tran vdout1_0ck26 FIND v(dout1_0) AT=270.05n

* CHECK dout1_1 Vdout1_1ck26 = 1.8 time = 270
.meas tran vdout1_1ck26 FIND v(dout1_1) AT=270.05n

* CHECK dout1_2 Vdout1_2ck26 = 1.8 time = 270
.meas tran vdout1_2ck26 FIND v(dout1_2) AT=270.05n

* CHECK dout1_3 Vdout1_3ck26 = 0 time = 270
.meas tran vdout1_3ck26 FIND v(dout1_3) AT=270.05n

* CHECK dout1_4 Vdout1_4ck26 = 0 time = 270
.meas tran vdout1_4ck26 FIND v(dout1_4) AT=270.05n

* CHECK dout1_5 Vdout1_5ck26 = 1.8 time = 270
.meas tran vdout1_5ck26 FIND v(dout1_5) AT=270.05n

* CHECK dout1_6 Vdout1_6ck26 = 0 time = 270
.meas tran vdout1_6ck26 FIND v(dout1_6) AT=270.05n

* CHECK dout1_7 Vdout1_7ck26 = 1.8 time = 270
.meas tran vdout1_7ck26 FIND v(dout1_7) AT=270.05n

* CHECK dout1_0 Vdout1_0ck27 = 0 time = 280
.meas tran vdout1_0ck27 FIND v(dout1_0) AT=280.05n

* CHECK dout1_1 Vdout1_1ck27 = 1.8 time = 280
.meas tran vdout1_1ck27 FIND v(dout1_1) AT=280.05n

* CHECK dout1_2 Vdout1_2ck27 = 1.8 time = 280
.meas tran vdout1_2ck27 FIND v(dout1_2) AT=280.05n

* CHECK dout1_3 Vdout1_3ck27 = 0 time = 280
.meas tran vdout1_3ck27 FIND v(dout1_3) AT=280.05n

* CHECK dout1_4 Vdout1_4ck27 = 0 time = 280
.meas tran vdout1_4ck27 FIND v(dout1_4) AT=280.05n

* CHECK dout1_5 Vdout1_5ck27 = 1.8 time = 280
.meas tran vdout1_5ck27 FIND v(dout1_5) AT=280.05n

* CHECK dout1_6 Vdout1_6ck27 = 0 time = 280
.meas tran vdout1_6ck27 FIND v(dout1_6) AT=280.05n

* CHECK dout1_7 Vdout1_7ck27 = 1.8 time = 280
.meas tran vdout1_7ck27 FIND v(dout1_7) AT=280.05n

* CHECK dout1_0 Vdout1_0ck28 = 0 time = 290
.meas tran vdout1_0ck28 FIND v(dout1_0) AT=290.05n

* CHECK dout1_1 Vdout1_1ck28 = 0 time = 290
.meas tran vdout1_1ck28 FIND v(dout1_1) AT=290.05n

* CHECK dout1_2 Vdout1_2ck28 = 0 time = 290
.meas tran vdout1_2ck28 FIND v(dout1_2) AT=290.05n

* CHECK dout1_3 Vdout1_3ck28 = 0 time = 290
.meas tran vdout1_3ck28 FIND v(dout1_3) AT=290.05n

* CHECK dout1_4 Vdout1_4ck28 = 0 time = 290
.meas tran vdout1_4ck28 FIND v(dout1_4) AT=290.05n

* CHECK dout1_5 Vdout1_5ck28 = 0 time = 290
.meas tran vdout1_5ck28 FIND v(dout1_5) AT=290.05n

* CHECK dout1_6 Vdout1_6ck28 = 1.8 time = 290
.meas tran vdout1_6ck28 FIND v(dout1_6) AT=290.05n

* CHECK dout1_7 Vdout1_7ck28 = 1.8 time = 290
.meas tran vdout1_7ck28 FIND v(dout1_7) AT=290.05n

* CHECK dout0_0 Vdout0_0ck30 = 0 time = 310
.meas tran vdout0_0ck30 FIND v(dout0_0) AT=310.05n

* CHECK dout0_1 Vdout0_1ck30 = 0 time = 310
.meas tran vdout0_1ck30 FIND v(dout0_1) AT=310.05n

* CHECK dout0_2 Vdout0_2ck30 = 0 time = 310
.meas tran vdout0_2ck30 FIND v(dout0_2) AT=310.05n

* CHECK dout0_3 Vdout0_3ck30 = 0 time = 310
.meas tran vdout0_3ck30 FIND v(dout0_3) AT=310.05n

* CHECK dout0_4 Vdout0_4ck30 = 0 time = 310
.meas tran vdout0_4ck30 FIND v(dout0_4) AT=310.05n

* CHECK dout0_5 Vdout0_5ck30 = 0 time = 310
.meas tran vdout0_5ck30 FIND v(dout0_5) AT=310.05n

* CHECK dout0_6 Vdout0_6ck30 = 1.8 time = 310
.meas tran vdout0_6ck30 FIND v(dout0_6) AT=310.05n

* CHECK dout0_7 Vdout0_7ck30 = 1.8 time = 310
.meas tran vdout0_7ck30 FIND v(dout0_7) AT=310.05n

* CHECK dout1_0 Vdout1_0ck32 = 0 time = 330
.meas tran vdout1_0ck32 FIND v(dout1_0) AT=330.05n

* CHECK dout1_1 Vdout1_1ck32 = 0 time = 330
.meas tran vdout1_1ck32 FIND v(dout1_1) AT=330.05n

* CHECK dout1_2 Vdout1_2ck32 = 0 time = 330
.meas tran vdout1_2ck32 FIND v(dout1_2) AT=330.05n

* CHECK dout1_3 Vdout1_3ck32 = 0 time = 330
.meas tran vdout1_3ck32 FIND v(dout1_3) AT=330.05n

* CHECK dout1_4 Vdout1_4ck32 = 0 time = 330
.meas tran vdout1_4ck32 FIND v(dout1_4) AT=330.05n

* CHECK dout1_5 Vdout1_5ck32 = 0 time = 330
.meas tran vdout1_5ck32 FIND v(dout1_5) AT=330.05n

* CHECK dout1_6 Vdout1_6ck32 = 1.8 time = 330
.meas tran vdout1_6ck32 FIND v(dout1_6) AT=330.05n

* CHECK dout1_7 Vdout1_7ck32 = 1.8 time = 330
.meas tran vdout1_7ck32 FIND v(dout1_7) AT=330.05n

* CHECK dout0_0 Vdout0_0ck33 = 0 time = 340
.meas tran vdout0_0ck33 FIND v(dout0_0) AT=340.05n

* CHECK dout0_1 Vdout0_1ck33 = 1.8 time = 340
.meas tran vdout0_1ck33 FIND v(dout0_1) AT=340.05n

* CHECK dout0_2 Vdout0_2ck33 = 1.8 time = 340
.meas tran vdout0_2ck33 FIND v(dout0_2) AT=340.05n

* CHECK dout0_3 Vdout0_3ck33 = 0 time = 340
.meas tran vdout0_3ck33 FIND v(dout0_3) AT=340.05n

* CHECK dout0_4 Vdout0_4ck33 = 0 time = 340
.meas tran vdout0_4ck33 FIND v(dout0_4) AT=340.05n

* CHECK dout0_5 Vdout0_5ck33 = 1.8 time = 340
.meas tran vdout0_5ck33 FIND v(dout0_5) AT=340.05n

* CHECK dout0_6 Vdout0_6ck33 = 0 time = 340
.meas tran vdout0_6ck33 FIND v(dout0_6) AT=340.05n

* CHECK dout0_7 Vdout0_7ck33 = 1.8 time = 340
.meas tran vdout0_7ck33 FIND v(dout0_7) AT=340.05n

* CHECK dout0_0 Vdout0_0ck34 = 0 time = 350
.meas tran vdout0_0ck34 FIND v(dout0_0) AT=350.05n

* CHECK dout0_1 Vdout0_1ck34 = 1.8 time = 350
.meas tran vdout0_1ck34 FIND v(dout0_1) AT=350.05n

* CHECK dout0_2 Vdout0_2ck34 = 1.8 time = 350
.meas tran vdout0_2ck34 FIND v(dout0_2) AT=350.05n

* CHECK dout0_3 Vdout0_3ck34 = 0 time = 350
.meas tran vdout0_3ck34 FIND v(dout0_3) AT=350.05n

* CHECK dout0_4 Vdout0_4ck34 = 0 time = 350
.meas tran vdout0_4ck34 FIND v(dout0_4) AT=350.05n

* CHECK dout0_5 Vdout0_5ck34 = 1.8 time = 350
.meas tran vdout0_5ck34 FIND v(dout0_5) AT=350.05n

* CHECK dout0_6 Vdout0_6ck34 = 0 time = 350
.meas tran vdout0_6ck34 FIND v(dout0_6) AT=350.05n

* CHECK dout0_7 Vdout0_7ck34 = 1.8 time = 350
.meas tran vdout0_7ck34 FIND v(dout0_7) AT=350.05n

* CHECK dout1_0 Vdout1_0ck34 = 1.8 time = 350
.meas tran vdout1_0ck34 FIND v(dout1_0) AT=350.05n

* CHECK dout1_1 Vdout1_1ck34 = 0 time = 350
.meas tran vdout1_1ck34 FIND v(dout1_1) AT=350.05n

* CHECK dout1_2 Vdout1_2ck34 = 0 time = 350
.meas tran vdout1_2ck34 FIND v(dout1_2) AT=350.05n

* CHECK dout1_3 Vdout1_3ck34 = 0 time = 350
.meas tran vdout1_3ck34 FIND v(dout1_3) AT=350.05n

* CHECK dout1_4 Vdout1_4ck34 = 1.8 time = 350
.meas tran vdout1_4ck34 FIND v(dout1_4) AT=350.05n

* CHECK dout1_5 Vdout1_5ck34 = 1.8 time = 350
.meas tran vdout1_5ck34 FIND v(dout1_5) AT=350.05n

* CHECK dout1_6 Vdout1_6ck34 = 0 time = 350
.meas tran vdout1_6ck34 FIND v(dout1_6) AT=350.05n

* CHECK dout1_7 Vdout1_7ck34 = 1.8 time = 350
.meas tran vdout1_7ck34 FIND v(dout1_7) AT=350.05n

* CHECK dout0_0 Vdout0_0ck35 = 0 time = 360
.meas tran vdout0_0ck35 FIND v(dout0_0) AT=360.05n

* CHECK dout0_1 Vdout0_1ck35 = 1.8 time = 360
.meas tran vdout0_1ck35 FIND v(dout0_1) AT=360.05n

* CHECK dout0_2 Vdout0_2ck35 = 1.8 time = 360
.meas tran vdout0_2ck35 FIND v(dout0_2) AT=360.05n

* CHECK dout0_3 Vdout0_3ck35 = 0 time = 360
.meas tran vdout0_3ck35 FIND v(dout0_3) AT=360.05n

* CHECK dout0_4 Vdout0_4ck35 = 0 time = 360
.meas tran vdout0_4ck35 FIND v(dout0_4) AT=360.05n

* CHECK dout0_5 Vdout0_5ck35 = 1.8 time = 360
.meas tran vdout0_5ck35 FIND v(dout0_5) AT=360.05n

* CHECK dout0_6 Vdout0_6ck35 = 0 time = 360
.meas tran vdout0_6ck35 FIND v(dout0_6) AT=360.05n

* CHECK dout0_7 Vdout0_7ck35 = 1.8 time = 360
.meas tran vdout0_7ck35 FIND v(dout0_7) AT=360.05n

* CHECK dout1_0 Vdout1_0ck35 = 0 time = 360
.meas tran vdout1_0ck35 FIND v(dout1_0) AT=360.05n

* CHECK dout1_1 Vdout1_1ck35 = 1.8 time = 360
.meas tran vdout1_1ck35 FIND v(dout1_1) AT=360.05n

* CHECK dout1_2 Vdout1_2ck35 = 1.8 time = 360
.meas tran vdout1_2ck35 FIND v(dout1_2) AT=360.05n

* CHECK dout1_3 Vdout1_3ck35 = 0 time = 360
.meas tran vdout1_3ck35 FIND v(dout1_3) AT=360.05n

* CHECK dout1_4 Vdout1_4ck35 = 0 time = 360
.meas tran vdout1_4ck35 FIND v(dout1_4) AT=360.05n

* CHECK dout1_5 Vdout1_5ck35 = 1.8 time = 360
.meas tran vdout1_5ck35 FIND v(dout1_5) AT=360.05n

* CHECK dout1_6 Vdout1_6ck35 = 0 time = 360
.meas tran vdout1_6ck35 FIND v(dout1_6) AT=360.05n

* CHECK dout1_7 Vdout1_7ck35 = 1.8 time = 360
.meas tran vdout1_7ck35 FIND v(dout1_7) AT=360.05n

* CHECK dout0_0 Vdout0_0ck38 = 1.8 time = 390
.meas tran vdout0_0ck38 FIND v(dout0_0) AT=390.05n

* CHECK dout0_1 Vdout0_1ck38 = 0 time = 390
.meas tran vdout0_1ck38 FIND v(dout0_1) AT=390.05n

* CHECK dout0_2 Vdout0_2ck38 = 1.8 time = 390
.meas tran vdout0_2ck38 FIND v(dout0_2) AT=390.05n

* CHECK dout0_3 Vdout0_3ck38 = 1.8 time = 390
.meas tran vdout0_3ck38 FIND v(dout0_3) AT=390.05n

* CHECK dout0_4 Vdout0_4ck38 = 0 time = 390
.meas tran vdout0_4ck38 FIND v(dout0_4) AT=390.05n

* CHECK dout0_5 Vdout0_5ck38 = 0 time = 390
.meas tran vdout0_5ck38 FIND v(dout0_5) AT=390.05n

* CHECK dout0_6 Vdout0_6ck38 = 1.8 time = 390
.meas tran vdout0_6ck38 FIND v(dout0_6) AT=390.05n

* CHECK dout0_7 Vdout0_7ck38 = 1.8 time = 390
.meas tran vdout0_7ck38 FIND v(dout0_7) AT=390.05n

* CHECK dout0_0 Vdout0_0ck40 = 0 time = 410
.meas tran vdout0_0ck40 FIND v(dout0_0) AT=410.05n

* CHECK dout0_1 Vdout0_1ck40 = 1.8 time = 410
.meas tran vdout0_1ck40 FIND v(dout0_1) AT=410.05n

* CHECK dout0_2 Vdout0_2ck40 = 1.8 time = 410
.meas tran vdout0_2ck40 FIND v(dout0_2) AT=410.05n

* CHECK dout0_3 Vdout0_3ck40 = 0 time = 410
.meas tran vdout0_3ck40 FIND v(dout0_3) AT=410.05n

* CHECK dout0_4 Vdout0_4ck40 = 0 time = 410
.meas tran vdout0_4ck40 FIND v(dout0_4) AT=410.05n

* CHECK dout0_5 Vdout0_5ck40 = 1.8 time = 410
.meas tran vdout0_5ck40 FIND v(dout0_5) AT=410.05n

* CHECK dout0_6 Vdout0_6ck40 = 0 time = 410
.meas tran vdout0_6ck40 FIND v(dout0_6) AT=410.05n

* CHECK dout0_7 Vdout0_7ck40 = 0 time = 410
.meas tran vdout0_7ck40 FIND v(dout0_7) AT=410.05n

* CHECK dout1_0 Vdout1_0ck40 = 1.8 time = 410
.meas tran vdout1_0ck40 FIND v(dout1_0) AT=410.05n

* CHECK dout1_1 Vdout1_1ck40 = 0 time = 410
.meas tran vdout1_1ck40 FIND v(dout1_1) AT=410.05n

* CHECK dout1_2 Vdout1_2ck40 = 1.8 time = 410
.meas tran vdout1_2ck40 FIND v(dout1_2) AT=410.05n

* CHECK dout1_3 Vdout1_3ck40 = 1.8 time = 410
.meas tran vdout1_3ck40 FIND v(dout1_3) AT=410.05n

* CHECK dout1_4 Vdout1_4ck40 = 0 time = 410
.meas tran vdout1_4ck40 FIND v(dout1_4) AT=410.05n

* CHECK dout1_5 Vdout1_5ck40 = 0 time = 410
.meas tran vdout1_5ck40 FIND v(dout1_5) AT=410.05n

* CHECK dout1_6 Vdout1_6ck40 = 1.8 time = 410
.meas tran vdout1_6ck40 FIND v(dout1_6) AT=410.05n

* CHECK dout1_7 Vdout1_7ck40 = 1.8 time = 410
.meas tran vdout1_7ck40 FIND v(dout1_7) AT=410.05n

* CHECK dout0_0 Vdout0_0ck41 = 0 time = 420
.meas tran vdout0_0ck41 FIND v(dout0_0) AT=420.05n

* CHECK dout0_1 Vdout0_1ck41 = 0 time = 420
.meas tran vdout0_1ck41 FIND v(dout0_1) AT=420.05n

* CHECK dout0_2 Vdout0_2ck41 = 1.8 time = 420
.meas tran vdout0_2ck41 FIND v(dout0_2) AT=420.05n

* CHECK dout0_3 Vdout0_3ck41 = 0 time = 420
.meas tran vdout0_3ck41 FIND v(dout0_3) AT=420.05n

* CHECK dout0_4 Vdout0_4ck41 = 0 time = 420
.meas tran vdout0_4ck41 FIND v(dout0_4) AT=420.05n

* CHECK dout0_5 Vdout0_5ck41 = 0 time = 420
.meas tran vdout0_5ck41 FIND v(dout0_5) AT=420.05n

* CHECK dout0_6 Vdout0_6ck41 = 0 time = 420
.meas tran vdout0_6ck41 FIND v(dout0_6) AT=420.05n

* CHECK dout0_7 Vdout0_7ck41 = 0 time = 420
.meas tran vdout0_7ck41 FIND v(dout0_7) AT=420.05n

* CHECK dout1_0 Vdout1_0ck41 = 0 time = 420
.meas tran vdout1_0ck41 FIND v(dout1_0) AT=420.05n

* CHECK dout1_1 Vdout1_1ck41 = 0 time = 420
.meas tran vdout1_1ck41 FIND v(dout1_1) AT=420.05n

* CHECK dout1_2 Vdout1_2ck41 = 1.8 time = 420
.meas tran vdout1_2ck41 FIND v(dout1_2) AT=420.05n

* CHECK dout1_3 Vdout1_3ck41 = 1.8 time = 420
.meas tran vdout1_3ck41 FIND v(dout1_3) AT=420.05n

* CHECK dout1_4 Vdout1_4ck41 = 1.8 time = 420
.meas tran vdout1_4ck41 FIND v(dout1_4) AT=420.05n

* CHECK dout1_5 Vdout1_5ck41 = 0 time = 420
.meas tran vdout1_5ck41 FIND v(dout1_5) AT=420.05n

* CHECK dout1_6 Vdout1_6ck41 = 1.8 time = 420
.meas tran vdout1_6ck41 FIND v(dout1_6) AT=420.05n

* CHECK dout1_7 Vdout1_7ck41 = 0 time = 420
.meas tran vdout1_7ck41 FIND v(dout1_7) AT=420.05n

* CHECK dout0_0 Vdout0_0ck43 = 1.8 time = 440
.meas tran vdout0_0ck43 FIND v(dout0_0) AT=440.05n

* CHECK dout0_1 Vdout0_1ck43 = 1.8 time = 440
.meas tran vdout0_1ck43 FIND v(dout0_1) AT=440.05n

* CHECK dout0_2 Vdout0_2ck43 = 0 time = 440
.meas tran vdout0_2ck43 FIND v(dout0_2) AT=440.05n

* CHECK dout0_3 Vdout0_3ck43 = 0 time = 440
.meas tran vdout0_3ck43 FIND v(dout0_3) AT=440.05n

* CHECK dout0_4 Vdout0_4ck43 = 1.8 time = 440
.meas tran vdout0_4ck43 FIND v(dout0_4) AT=440.05n

* CHECK dout0_5 Vdout0_5ck43 = 0 time = 440
.meas tran vdout0_5ck43 FIND v(dout0_5) AT=440.05n

* CHECK dout0_6 Vdout0_6ck43 = 0 time = 440
.meas tran vdout0_6ck43 FIND v(dout0_6) AT=440.05n

* CHECK dout0_7 Vdout0_7ck43 = 1.8 time = 440
.meas tran vdout0_7ck43 FIND v(dout0_7) AT=440.05n

* CHECK dout1_0 Vdout1_0ck45 = 0 time = 460
.meas tran vdout1_0ck45 FIND v(dout1_0) AT=460.05n

* CHECK dout1_1 Vdout1_1ck45 = 0 time = 460
.meas tran vdout1_1ck45 FIND v(dout1_1) AT=460.05n

* CHECK dout1_2 Vdout1_2ck45 = 1.8 time = 460
.meas tran vdout1_2ck45 FIND v(dout1_2) AT=460.05n

* CHECK dout1_3 Vdout1_3ck45 = 0 time = 460
.meas tran vdout1_3ck45 FIND v(dout1_3) AT=460.05n

* CHECK dout1_4 Vdout1_4ck45 = 0 time = 460
.meas tran vdout1_4ck45 FIND v(dout1_4) AT=460.05n

* CHECK dout1_5 Vdout1_5ck45 = 0 time = 460
.meas tran vdout1_5ck45 FIND v(dout1_5) AT=460.05n

* CHECK dout1_6 Vdout1_6ck45 = 0 time = 460
.meas tran vdout1_6ck45 FIND v(dout1_6) AT=460.05n

* CHECK dout1_7 Vdout1_7ck45 = 0 time = 460
.meas tran vdout1_7ck45 FIND v(dout1_7) AT=460.05n

* CHECK dout0_0 Vdout0_0ck46 = 1.8 time = 470
.meas tran vdout0_0ck46 FIND v(dout0_0) AT=470.05n

* CHECK dout0_1 Vdout0_1ck46 = 0 time = 470
.meas tran vdout0_1ck46 FIND v(dout0_1) AT=470.05n

* CHECK dout0_2 Vdout0_2ck46 = 1.8 time = 470
.meas tran vdout0_2ck46 FIND v(dout0_2) AT=470.05n

* CHECK dout0_3 Vdout0_3ck46 = 1.8 time = 470
.meas tran vdout0_3ck46 FIND v(dout0_3) AT=470.05n

* CHECK dout0_4 Vdout0_4ck46 = 0 time = 470
.meas tran vdout0_4ck46 FIND v(dout0_4) AT=470.05n

* CHECK dout0_5 Vdout0_5ck46 = 0 time = 470
.meas tran vdout0_5ck46 FIND v(dout0_5) AT=470.05n

* CHECK dout0_6 Vdout0_6ck46 = 1.8 time = 470
.meas tran vdout0_6ck46 FIND v(dout0_6) AT=470.05n

* CHECK dout0_7 Vdout0_7ck46 = 1.8 time = 470
.meas tran vdout0_7ck46 FIND v(dout0_7) AT=470.05n

* CHECK dout1_0 Vdout1_0ck47 = 0 time = 480
.meas tran vdout1_0ck47 FIND v(dout1_0) AT=480.05n

* CHECK dout1_1 Vdout1_1ck47 = 1.8 time = 480
.meas tran vdout1_1ck47 FIND v(dout1_1) AT=480.05n

* CHECK dout1_2 Vdout1_2ck47 = 1.8 time = 480
.meas tran vdout1_2ck47 FIND v(dout1_2) AT=480.05n

* CHECK dout1_3 Vdout1_3ck47 = 1.8 time = 480
.meas tran vdout1_3ck47 FIND v(dout1_3) AT=480.05n

* CHECK dout1_4 Vdout1_4ck47 = 0 time = 480
.meas tran vdout1_4ck47 FIND v(dout1_4) AT=480.05n

* CHECK dout1_5 Vdout1_5ck47 = 1.8 time = 480
.meas tran vdout1_5ck47 FIND v(dout1_5) AT=480.05n

* CHECK dout1_6 Vdout1_6ck47 = 0 time = 480
.meas tran vdout1_6ck47 FIND v(dout1_6) AT=480.05n

* CHECK dout1_7 Vdout1_7ck47 = 1.8 time = 480
.meas tran vdout1_7ck47 FIND v(dout1_7) AT=480.05n

* CHECK dout0_0 Vdout0_0ck48 = 0 time = 490
.meas tran vdout0_0ck48 FIND v(dout0_0) AT=490.05n

* CHECK dout0_1 Vdout0_1ck48 = 0 time = 490
.meas tran vdout0_1ck48 FIND v(dout0_1) AT=490.05n

* CHECK dout0_2 Vdout0_2ck48 = 1.8 time = 490
.meas tran vdout0_2ck48 FIND v(dout0_2) AT=490.05n

* CHECK dout0_3 Vdout0_3ck48 = 0 time = 490
.meas tran vdout0_3ck48 FIND v(dout0_3) AT=490.05n

* CHECK dout0_4 Vdout0_4ck48 = 0 time = 490
.meas tran vdout0_4ck48 FIND v(dout0_4) AT=490.05n

* CHECK dout0_5 Vdout0_5ck48 = 0 time = 490
.meas tran vdout0_5ck48 FIND v(dout0_5) AT=490.05n

* CHECK dout0_6 Vdout0_6ck48 = 0 time = 490
.meas tran vdout0_6ck48 FIND v(dout0_6) AT=490.05n

* CHECK dout0_7 Vdout0_7ck48 = 0 time = 490
.meas tran vdout0_7ck48 FIND v(dout0_7) AT=490.05n

* CHECK dout1_0 Vdout1_0ck49 = 0 time = 500
.meas tran vdout1_0ck49 FIND v(dout1_0) AT=500.05n

* CHECK dout1_1 Vdout1_1ck49 = 0 time = 500
.meas tran vdout1_1ck49 FIND v(dout1_1) AT=500.05n

* CHECK dout1_2 Vdout1_2ck49 = 1.8 time = 500
.meas tran vdout1_2ck49 FIND v(dout1_2) AT=500.05n

* CHECK dout1_3 Vdout1_3ck49 = 1.8 time = 500
.meas tran vdout1_3ck49 FIND v(dout1_3) AT=500.05n

* CHECK dout1_4 Vdout1_4ck49 = 1.8 time = 500
.meas tran vdout1_4ck49 FIND v(dout1_4) AT=500.05n

* CHECK dout1_5 Vdout1_5ck49 = 1.8 time = 500
.meas tran vdout1_5ck49 FIND v(dout1_5) AT=500.05n

* CHECK dout1_6 Vdout1_6ck49 = 0 time = 500
.meas tran vdout1_6ck49 FIND v(dout1_6) AT=500.05n

* CHECK dout1_7 Vdout1_7ck49 = 1.8 time = 500
.meas tran vdout1_7ck49 FIND v(dout1_7) AT=500.05n

* CHECK dout1_0 Vdout1_0ck50 = 0 time = 510
.meas tran vdout1_0ck50 FIND v(dout1_0) AT=510.05n

* CHECK dout1_1 Vdout1_1ck50 = 0 time = 510
.meas tran vdout1_1ck50 FIND v(dout1_1) AT=510.05n

* CHECK dout1_2 Vdout1_2ck50 = 1.8 time = 510
.meas tran vdout1_2ck50 FIND v(dout1_2) AT=510.05n

* CHECK dout1_3 Vdout1_3ck50 = 0 time = 510
.meas tran vdout1_3ck50 FIND v(dout1_3) AT=510.05n

* CHECK dout1_4 Vdout1_4ck50 = 0 time = 510
.meas tran vdout1_4ck50 FIND v(dout1_4) AT=510.05n

* CHECK dout1_5 Vdout1_5ck50 = 1.8 time = 510
.meas tran vdout1_5ck50 FIND v(dout1_5) AT=510.05n

* CHECK dout1_6 Vdout1_6ck50 = 0 time = 510
.meas tran vdout1_6ck50 FIND v(dout1_6) AT=510.05n

* CHECK dout1_7 Vdout1_7ck50 = 0 time = 510
.meas tran vdout1_7ck50 FIND v(dout1_7) AT=510.05n

* CHECK dout1_0 Vdout1_0ck51 = 0 time = 520
.meas tran vdout1_0ck51 FIND v(dout1_0) AT=520.05n

* CHECK dout1_1 Vdout1_1ck51 = 0 time = 520
.meas tran vdout1_1ck51 FIND v(dout1_1) AT=520.05n

* CHECK dout1_2 Vdout1_2ck51 = 1.8 time = 520
.meas tran vdout1_2ck51 FIND v(dout1_2) AT=520.05n

* CHECK dout1_3 Vdout1_3ck51 = 0 time = 520
.meas tran vdout1_3ck51 FIND v(dout1_3) AT=520.05n

* CHECK dout1_4 Vdout1_4ck51 = 0 time = 520
.meas tran vdout1_4ck51 FIND v(dout1_4) AT=520.05n

* CHECK dout1_5 Vdout1_5ck51 = 1.8 time = 520
.meas tran vdout1_5ck51 FIND v(dout1_5) AT=520.05n

* CHECK dout1_6 Vdout1_6ck51 = 0 time = 520
.meas tran vdout1_6ck51 FIND v(dout1_6) AT=520.05n

* CHECK dout1_7 Vdout1_7ck51 = 0 time = 520
.meas tran vdout1_7ck51 FIND v(dout1_7) AT=520.05n

* CHECK dout0_0 Vdout0_0ck55 = 0 time = 560
.meas tran vdout0_0ck55 FIND v(dout0_0) AT=560.05n

* CHECK dout0_1 Vdout0_1ck55 = 1.8 time = 560
.meas tran vdout0_1ck55 FIND v(dout0_1) AT=560.05n

* CHECK dout0_2 Vdout0_2ck55 = 0 time = 560
.meas tran vdout0_2ck55 FIND v(dout0_2) AT=560.05n

* CHECK dout0_3 Vdout0_3ck55 = 0 time = 560
.meas tran vdout0_3ck55 FIND v(dout0_3) AT=560.05n

* CHECK dout0_4 Vdout0_4ck55 = 1.8 time = 560
.meas tran vdout0_4ck55 FIND v(dout0_4) AT=560.05n

* CHECK dout0_5 Vdout0_5ck55 = 0 time = 560
.meas tran vdout0_5ck55 FIND v(dout0_5) AT=560.05n

* CHECK dout0_6 Vdout0_6ck55 = 1.8 time = 560
.meas tran vdout0_6ck55 FIND v(dout0_6) AT=560.05n

* CHECK dout0_7 Vdout0_7ck55 = 1.8 time = 560
.meas tran vdout0_7ck55 FIND v(dout0_7) AT=560.05n

* CHECK dout0_0 Vdout0_0ck56 = 0 time = 570
.meas tran vdout0_0ck56 FIND v(dout0_0) AT=570.05n

* CHECK dout0_1 Vdout0_1ck56 = 0 time = 570
.meas tran vdout0_1ck56 FIND v(dout0_1) AT=570.05n

* CHECK dout0_2 Vdout0_2ck56 = 1.8 time = 570
.meas tran vdout0_2ck56 FIND v(dout0_2) AT=570.05n

* CHECK dout0_3 Vdout0_3ck56 = 1.8 time = 570
.meas tran vdout0_3ck56 FIND v(dout0_3) AT=570.05n

* CHECK dout0_4 Vdout0_4ck56 = 1.8 time = 570
.meas tran vdout0_4ck56 FIND v(dout0_4) AT=570.05n

* CHECK dout0_5 Vdout0_5ck56 = 1.8 time = 570
.meas tran vdout0_5ck56 FIND v(dout0_5) AT=570.05n

* CHECK dout0_6 Vdout0_6ck56 = 0 time = 570
.meas tran vdout0_6ck56 FIND v(dout0_6) AT=570.05n

* CHECK dout0_7 Vdout0_7ck56 = 1.8 time = 570
.meas tran vdout0_7ck56 FIND v(dout0_7) AT=570.05n

* CHECK dout1_0 Vdout1_0ck57 = 0 time = 580
.meas tran vdout1_0ck57 FIND v(dout1_0) AT=580.05n

* CHECK dout1_1 Vdout1_1ck57 = 0 time = 580
.meas tran vdout1_1ck57 FIND v(dout1_1) AT=580.05n

* CHECK dout1_2 Vdout1_2ck57 = 1.8 time = 580
.meas tran vdout1_2ck57 FIND v(dout1_2) AT=580.05n

* CHECK dout1_3 Vdout1_3ck57 = 1.8 time = 580
.meas tran vdout1_3ck57 FIND v(dout1_3) AT=580.05n

* CHECK dout1_4 Vdout1_4ck57 = 1.8 time = 580
.meas tran vdout1_4ck57 FIND v(dout1_4) AT=580.05n

* CHECK dout1_5 Vdout1_5ck57 = 1.8 time = 580
.meas tran vdout1_5ck57 FIND v(dout1_5) AT=580.05n

* CHECK dout1_6 Vdout1_6ck57 = 0 time = 580
.meas tran vdout1_6ck57 FIND v(dout1_6) AT=580.05n

* CHECK dout1_7 Vdout1_7ck57 = 1.8 time = 580
.meas tran vdout1_7ck57 FIND v(dout1_7) AT=580.05n

* CHECK dout0_0 Vdout0_0ck58 = 0 time = 590
.meas tran vdout0_0ck58 FIND v(dout0_0) AT=590.05n

* CHECK dout0_1 Vdout0_1ck58 = 1.8 time = 590
.meas tran vdout0_1ck58 FIND v(dout0_1) AT=590.05n

* CHECK dout0_2 Vdout0_2ck58 = 0 time = 590
.meas tran vdout0_2ck58 FIND v(dout0_2) AT=590.05n

* CHECK dout0_3 Vdout0_3ck58 = 0 time = 590
.meas tran vdout0_3ck58 FIND v(dout0_3) AT=590.05n

* CHECK dout0_4 Vdout0_4ck58 = 1.8 time = 590
.meas tran vdout0_4ck58 FIND v(dout0_4) AT=590.05n

* CHECK dout0_5 Vdout0_5ck58 = 0 time = 590
.meas tran vdout0_5ck58 FIND v(dout0_5) AT=590.05n

* CHECK dout0_6 Vdout0_6ck58 = 1.8 time = 590
.meas tran vdout0_6ck58 FIND v(dout0_6) AT=590.05n

* CHECK dout0_7 Vdout0_7ck58 = 1.8 time = 590
.meas tran vdout0_7ck58 FIND v(dout0_7) AT=590.05n

* CHECK dout1_0 Vdout1_0ck59 = 0 time = 600
.meas tran vdout1_0ck59 FIND v(dout1_0) AT=600.05n

* CHECK dout1_1 Vdout1_1ck59 = 1.8 time = 600
.meas tran vdout1_1ck59 FIND v(dout1_1) AT=600.05n

* CHECK dout1_2 Vdout1_2ck59 = 0 time = 600
.meas tran vdout1_2ck59 FIND v(dout1_2) AT=600.05n

* CHECK dout1_3 Vdout1_3ck59 = 0 time = 600
.meas tran vdout1_3ck59 FIND v(dout1_3) AT=600.05n

* CHECK dout1_4 Vdout1_4ck59 = 1.8 time = 600
.meas tran vdout1_4ck59 FIND v(dout1_4) AT=600.05n

* CHECK dout1_5 Vdout1_5ck59 = 0 time = 600
.meas tran vdout1_5ck59 FIND v(dout1_5) AT=600.05n

* CHECK dout1_6 Vdout1_6ck59 = 1.8 time = 600
.meas tran vdout1_6ck59 FIND v(dout1_6) AT=600.05n

* CHECK dout1_7 Vdout1_7ck59 = 1.8 time = 600
.meas tran vdout1_7ck59 FIND v(dout1_7) AT=600.05n

* CHECK dout0_0 Vdout0_0ck60 = 1.8 time = 610
.meas tran vdout0_0ck60 FIND v(dout0_0) AT=610.05n

* CHECK dout0_1 Vdout0_1ck60 = 1.8 time = 610
.meas tran vdout0_1ck60 FIND v(dout0_1) AT=610.05n

* CHECK dout0_2 Vdout0_2ck60 = 0 time = 610
.meas tran vdout0_2ck60 FIND v(dout0_2) AT=610.05n

* CHECK dout0_3 Vdout0_3ck60 = 0 time = 610
.meas tran vdout0_3ck60 FIND v(dout0_3) AT=610.05n

* CHECK dout0_4 Vdout0_4ck60 = 1.8 time = 610
.meas tran vdout0_4ck60 FIND v(dout0_4) AT=610.05n

* CHECK dout0_5 Vdout0_5ck60 = 1.8 time = 610
.meas tran vdout0_5ck60 FIND v(dout0_5) AT=610.05n

* CHECK dout0_6 Vdout0_6ck60 = 1.8 time = 610
.meas tran vdout0_6ck60 FIND v(dout0_6) AT=610.05n

* CHECK dout0_7 Vdout0_7ck60 = 1.8 time = 610
.meas tran vdout0_7ck60 FIND v(dout0_7) AT=610.05n

* CHECK dout0_0 Vdout0_0ck61 = 0 time = 620
.meas tran vdout0_0ck61 FIND v(dout0_0) AT=620.05n

* CHECK dout0_1 Vdout0_1ck61 = 1.8 time = 620
.meas tran vdout0_1ck61 FIND v(dout0_1) AT=620.05n

* CHECK dout0_2 Vdout0_2ck61 = 0 time = 620
.meas tran vdout0_2ck61 FIND v(dout0_2) AT=620.05n

* CHECK dout0_3 Vdout0_3ck61 = 0 time = 620
.meas tran vdout0_3ck61 FIND v(dout0_3) AT=620.05n

* CHECK dout0_4 Vdout0_4ck61 = 1.8 time = 620
.meas tran vdout0_4ck61 FIND v(dout0_4) AT=620.05n

* CHECK dout0_5 Vdout0_5ck61 = 0 time = 620
.meas tran vdout0_5ck61 FIND v(dout0_5) AT=620.05n

* CHECK dout0_6 Vdout0_6ck61 = 1.8 time = 620
.meas tran vdout0_6ck61 FIND v(dout0_6) AT=620.05n

* CHECK dout0_7 Vdout0_7ck61 = 1.8 time = 620
.meas tran vdout0_7ck61 FIND v(dout0_7) AT=620.05n

* CHECK dout1_0 Vdout1_0ck61 = 1.8 time = 620
.meas tran vdout1_0ck61 FIND v(dout1_0) AT=620.05n

* CHECK dout1_1 Vdout1_1ck61 = 1.8 time = 620
.meas tran vdout1_1ck61 FIND v(dout1_1) AT=620.05n

* CHECK dout1_2 Vdout1_2ck61 = 0 time = 620
.meas tran vdout1_2ck61 FIND v(dout1_2) AT=620.05n

* CHECK dout1_3 Vdout1_3ck61 = 0 time = 620
.meas tran vdout1_3ck61 FIND v(dout1_3) AT=620.05n

* CHECK dout1_4 Vdout1_4ck61 = 1.8 time = 620
.meas tran vdout1_4ck61 FIND v(dout1_4) AT=620.05n

* CHECK dout1_5 Vdout1_5ck61 = 1.8 time = 620
.meas tran vdout1_5ck61 FIND v(dout1_5) AT=620.05n

* CHECK dout1_6 Vdout1_6ck61 = 1.8 time = 620
.meas tran vdout1_6ck61 FIND v(dout1_6) AT=620.05n

* CHECK dout1_7 Vdout1_7ck61 = 1.8 time = 620
.meas tran vdout1_7ck61 FIND v(dout1_7) AT=620.05n

* CHECK dout0_0 Vdout0_0ck62 = 0 time = 630
.meas tran vdout0_0ck62 FIND v(dout0_0) AT=630.05n

* CHECK dout0_1 Vdout0_1ck62 = 0 time = 630
.meas tran vdout0_1ck62 FIND v(dout0_1) AT=630.05n

* CHECK dout0_2 Vdout0_2ck62 = 1.8 time = 630
.meas tran vdout0_2ck62 FIND v(dout0_2) AT=630.05n

* CHECK dout0_3 Vdout0_3ck62 = 1.8 time = 630
.meas tran vdout0_3ck62 FIND v(dout0_3) AT=630.05n

* CHECK dout0_4 Vdout0_4ck62 = 1.8 time = 630
.meas tran vdout0_4ck62 FIND v(dout0_4) AT=630.05n

* CHECK dout0_5 Vdout0_5ck62 = 1.8 time = 630
.meas tran vdout0_5ck62 FIND v(dout0_5) AT=630.05n

* CHECK dout0_6 Vdout0_6ck62 = 0 time = 630
.meas tran vdout0_6ck62 FIND v(dout0_6) AT=630.05n

* CHECK dout0_7 Vdout0_7ck62 = 1.8 time = 630
.meas tran vdout0_7ck62 FIND v(dout0_7) AT=630.05n

* CHECK dout0_0 Vdout0_0ck65 = 0 time = 660
.meas tran vdout0_0ck65 FIND v(dout0_0) AT=660.05n

* CHECK dout0_1 Vdout0_1ck65 = 0 time = 660
.meas tran vdout0_1ck65 FIND v(dout0_1) AT=660.05n

* CHECK dout0_2 Vdout0_2ck65 = 1.8 time = 660
.meas tran vdout0_2ck65 FIND v(dout0_2) AT=660.05n

* CHECK dout0_3 Vdout0_3ck65 = 0 time = 660
.meas tran vdout0_3ck65 FIND v(dout0_3) AT=660.05n

* CHECK dout0_4 Vdout0_4ck65 = 0 time = 660
.meas tran vdout0_4ck65 FIND v(dout0_4) AT=660.05n

* CHECK dout0_5 Vdout0_5ck65 = 1.8 time = 660
.meas tran vdout0_5ck65 FIND v(dout0_5) AT=660.05n

* CHECK dout0_6 Vdout0_6ck65 = 1.8 time = 660
.meas tran vdout0_6ck65 FIND v(dout0_6) AT=660.05n

* CHECK dout0_7 Vdout0_7ck65 = 1.8 time = 660
.meas tran vdout0_7ck65 FIND v(dout0_7) AT=660.05n

* CHECK dout1_0 Vdout1_0ck65 = 0 time = 660
.meas tran vdout1_0ck65 FIND v(dout1_0) AT=660.05n

* CHECK dout1_1 Vdout1_1ck65 = 1.8 time = 660
.meas tran vdout1_1ck65 FIND v(dout1_1) AT=660.05n

* CHECK dout1_2 Vdout1_2ck65 = 0 time = 660
.meas tran vdout1_2ck65 FIND v(dout1_2) AT=660.05n

* CHECK dout1_3 Vdout1_3ck65 = 0 time = 660
.meas tran vdout1_3ck65 FIND v(dout1_3) AT=660.05n

* CHECK dout1_4 Vdout1_4ck65 = 1.8 time = 660
.meas tran vdout1_4ck65 FIND v(dout1_4) AT=660.05n

* CHECK dout1_5 Vdout1_5ck65 = 0 time = 660
.meas tran vdout1_5ck65 FIND v(dout1_5) AT=660.05n

* CHECK dout1_6 Vdout1_6ck65 = 1.8 time = 660
.meas tran vdout1_6ck65 FIND v(dout1_6) AT=660.05n

* CHECK dout1_7 Vdout1_7ck65 = 1.8 time = 660
.meas tran vdout1_7ck65 FIND v(dout1_7) AT=660.05n

* CHECK dout0_0 Vdout0_0ck67 = 1.8 time = 680
.meas tran vdout0_0ck67 FIND v(dout0_0) AT=680.05n

* CHECK dout0_1 Vdout0_1ck67 = 0 time = 680
.meas tran vdout0_1ck67 FIND v(dout0_1) AT=680.05n

* CHECK dout0_2 Vdout0_2ck67 = 0 time = 680
.meas tran vdout0_2ck67 FIND v(dout0_2) AT=680.05n

* CHECK dout0_3 Vdout0_3ck67 = 0 time = 680
.meas tran vdout0_3ck67 FIND v(dout0_3) AT=680.05n

* CHECK dout0_4 Vdout0_4ck67 = 1.8 time = 680
.meas tran vdout0_4ck67 FIND v(dout0_4) AT=680.05n

* CHECK dout0_5 Vdout0_5ck67 = 0 time = 680
.meas tran vdout0_5ck67 FIND v(dout0_5) AT=680.05n

* CHECK dout0_6 Vdout0_6ck67 = 0 time = 680
.meas tran vdout0_6ck67 FIND v(dout0_6) AT=680.05n

* CHECK dout0_7 Vdout0_7ck67 = 1.8 time = 680
.meas tran vdout0_7ck67 FIND v(dout0_7) AT=680.05n

* CHECK dout1_0 Vdout1_0ck67 = 1.8 time = 680
.meas tran vdout1_0ck67 FIND v(dout1_0) AT=680.05n

* CHECK dout1_1 Vdout1_1ck67 = 1.8 time = 680
.meas tran vdout1_1ck67 FIND v(dout1_1) AT=680.05n

* CHECK dout1_2 Vdout1_2ck67 = 1.8 time = 680
.meas tran vdout1_2ck67 FIND v(dout1_2) AT=680.05n

* CHECK dout1_3 Vdout1_3ck67 = 1.8 time = 680
.meas tran vdout1_3ck67 FIND v(dout1_3) AT=680.05n

* CHECK dout1_4 Vdout1_4ck67 = 1.8 time = 680
.meas tran vdout1_4ck67 FIND v(dout1_4) AT=680.05n

* CHECK dout1_5 Vdout1_5ck67 = 0 time = 680
.meas tran vdout1_5ck67 FIND v(dout1_5) AT=680.05n

* CHECK dout1_6 Vdout1_6ck67 = 1.8 time = 680
.meas tran vdout1_6ck67 FIND v(dout1_6) AT=680.05n

* CHECK dout1_7 Vdout1_7ck67 = 1.8 time = 680
.meas tran vdout1_7ck67 FIND v(dout1_7) AT=680.05n

* CHECK dout0_0 Vdout0_0ck69 = 0 time = 700
.meas tran vdout0_0ck69 FIND v(dout0_0) AT=700.05n

* CHECK dout0_1 Vdout0_1ck69 = 0 time = 700
.meas tran vdout0_1ck69 FIND v(dout0_1) AT=700.05n

* CHECK dout0_2 Vdout0_2ck69 = 0 time = 700
.meas tran vdout0_2ck69 FIND v(dout0_2) AT=700.05n

* CHECK dout0_3 Vdout0_3ck69 = 0 time = 700
.meas tran vdout0_3ck69 FIND v(dout0_3) AT=700.05n

* CHECK dout0_4 Vdout0_4ck69 = 0 time = 700
.meas tran vdout0_4ck69 FIND v(dout0_4) AT=700.05n

* CHECK dout0_5 Vdout0_5ck69 = 1.8 time = 700
.meas tran vdout0_5ck69 FIND v(dout0_5) AT=700.05n

* CHECK dout0_6 Vdout0_6ck69 = 0 time = 700
.meas tran vdout0_6ck69 FIND v(dout0_6) AT=700.05n

* CHECK dout0_7 Vdout0_7ck69 = 1.8 time = 700
.meas tran vdout0_7ck69 FIND v(dout0_7) AT=700.05n

* CHECK dout1_0 Vdout1_0ck69 = 0 time = 700
.meas tran vdout1_0ck69 FIND v(dout1_0) AT=700.05n

* CHECK dout1_1 Vdout1_1ck69 = 1.8 time = 700
.meas tran vdout1_1ck69 FIND v(dout1_1) AT=700.05n

* CHECK dout1_2 Vdout1_2ck69 = 0 time = 700
.meas tran vdout1_2ck69 FIND v(dout1_2) AT=700.05n

* CHECK dout1_3 Vdout1_3ck69 = 0 time = 700
.meas tran vdout1_3ck69 FIND v(dout1_3) AT=700.05n

* CHECK dout1_4 Vdout1_4ck69 = 1.8 time = 700
.meas tran vdout1_4ck69 FIND v(dout1_4) AT=700.05n

* CHECK dout1_5 Vdout1_5ck69 = 0 time = 700
.meas tran vdout1_5ck69 FIND v(dout1_5) AT=700.05n

* CHECK dout1_6 Vdout1_6ck69 = 1.8 time = 700
.meas tran vdout1_6ck69 FIND v(dout1_6) AT=700.05n

* CHECK dout1_7 Vdout1_7ck69 = 1.8 time = 700
.meas tran vdout1_7ck69 FIND v(dout1_7) AT=700.05n

* CHECK dout0_0 Vdout0_0ck70 = 0 time = 710
.meas tran vdout0_0ck70 FIND v(dout0_0) AT=710.05n

* CHECK dout0_1 Vdout0_1ck70 = 0 time = 710
.meas tran vdout0_1ck70 FIND v(dout0_1) AT=710.05n

* CHECK dout0_2 Vdout0_2ck70 = 0 time = 710
.meas tran vdout0_2ck70 FIND v(dout0_2) AT=710.05n

* CHECK dout0_3 Vdout0_3ck70 = 0 time = 710
.meas tran vdout0_3ck70 FIND v(dout0_3) AT=710.05n

* CHECK dout0_4 Vdout0_4ck70 = 0 time = 710
.meas tran vdout0_4ck70 FIND v(dout0_4) AT=710.05n

* CHECK dout0_5 Vdout0_5ck70 = 1.8 time = 710
.meas tran vdout0_5ck70 FIND v(dout0_5) AT=710.05n

* CHECK dout0_6 Vdout0_6ck70 = 0 time = 710
.meas tran vdout0_6ck70 FIND v(dout0_6) AT=710.05n

* CHECK dout0_7 Vdout0_7ck70 = 1.8 time = 710
.meas tran vdout0_7ck70 FIND v(dout0_7) AT=710.05n

* CHECK dout1_0 Vdout1_0ck71 = 0 time = 720
.meas tran vdout1_0ck71 FIND v(dout1_0) AT=720.05n

* CHECK dout1_1 Vdout1_1ck71 = 1.8 time = 720
.meas tran vdout1_1ck71 FIND v(dout1_1) AT=720.05n

* CHECK dout1_2 Vdout1_2ck71 = 0 time = 720
.meas tran vdout1_2ck71 FIND v(dout1_2) AT=720.05n

* CHECK dout1_3 Vdout1_3ck71 = 1.8 time = 720
.meas tran vdout1_3ck71 FIND v(dout1_3) AT=720.05n

* CHECK dout1_4 Vdout1_4ck71 = 0 time = 720
.meas tran vdout1_4ck71 FIND v(dout1_4) AT=720.05n

* CHECK dout1_5 Vdout1_5ck71 = 0 time = 720
.meas tran vdout1_5ck71 FIND v(dout1_5) AT=720.05n

* CHECK dout1_6 Vdout1_6ck71 = 0 time = 720
.meas tran vdout1_6ck71 FIND v(dout1_6) AT=720.05n

* CHECK dout1_7 Vdout1_7ck71 = 1.8 time = 720
.meas tran vdout1_7ck71 FIND v(dout1_7) AT=720.05n

* CHECK dout0_0 Vdout0_0ck72 = 0 time = 730
.meas tran vdout0_0ck72 FIND v(dout0_0) AT=730.05n

* CHECK dout0_1 Vdout0_1ck72 = 1.8 time = 730
.meas tran vdout0_1ck72 FIND v(dout0_1) AT=730.05n

* CHECK dout0_2 Vdout0_2ck72 = 0 time = 730
.meas tran vdout0_2ck72 FIND v(dout0_2) AT=730.05n

* CHECK dout0_3 Vdout0_3ck72 = 0 time = 730
.meas tran vdout0_3ck72 FIND v(dout0_3) AT=730.05n

* CHECK dout0_4 Vdout0_4ck72 = 1.8 time = 730
.meas tran vdout0_4ck72 FIND v(dout0_4) AT=730.05n

* CHECK dout0_5 Vdout0_5ck72 = 0 time = 730
.meas tran vdout0_5ck72 FIND v(dout0_5) AT=730.05n

* CHECK dout0_6 Vdout0_6ck72 = 1.8 time = 730
.meas tran vdout0_6ck72 FIND v(dout0_6) AT=730.05n

* CHECK dout0_7 Vdout0_7ck72 = 1.8 time = 730
.meas tran vdout0_7ck72 FIND v(dout0_7) AT=730.05n

* CHECK dout0_0 Vdout0_0ck74 = 1.8 time = 750
.meas tran vdout0_0ck74 FIND v(dout0_0) AT=750.05n

* CHECK dout0_1 Vdout0_1ck74 = 1.8 time = 750
.meas tran vdout0_1ck74 FIND v(dout0_1) AT=750.05n

* CHECK dout0_2 Vdout0_2ck74 = 1.8 time = 750
.meas tran vdout0_2ck74 FIND v(dout0_2) AT=750.05n

* CHECK dout0_3 Vdout0_3ck74 = 0 time = 750
.meas tran vdout0_3ck74 FIND v(dout0_3) AT=750.05n

* CHECK dout0_4 Vdout0_4ck74 = 1.8 time = 750
.meas tran vdout0_4ck74 FIND v(dout0_4) AT=750.05n

* CHECK dout0_5 Vdout0_5ck74 = 0 time = 750
.meas tran vdout0_5ck74 FIND v(dout0_5) AT=750.05n

* CHECK dout0_6 Vdout0_6ck74 = 1.8 time = 750
.meas tran vdout0_6ck74 FIND v(dout0_6) AT=750.05n

* CHECK dout0_7 Vdout0_7ck74 = 0 time = 750
.meas tran vdout0_7ck74 FIND v(dout0_7) AT=750.05n

* CHECK dout1_0 Vdout1_0ck74 = 0 time = 750
.meas tran vdout1_0ck74 FIND v(dout1_0) AT=750.05n

* CHECK dout1_1 Vdout1_1ck74 = 0 time = 750
.meas tran vdout1_1ck74 FIND v(dout1_1) AT=750.05n

* CHECK dout1_2 Vdout1_2ck74 = 0 time = 750
.meas tran vdout1_2ck74 FIND v(dout1_2) AT=750.05n

* CHECK dout1_3 Vdout1_3ck74 = 1.8 time = 750
.meas tran vdout1_3ck74 FIND v(dout1_3) AT=750.05n

* CHECK dout1_4 Vdout1_4ck74 = 0 time = 750
.meas tran vdout1_4ck74 FIND v(dout1_4) AT=750.05n

* CHECK dout1_5 Vdout1_5ck74 = 1.8 time = 750
.meas tran vdout1_5ck74 FIND v(dout1_5) AT=750.05n

* CHECK dout1_6 Vdout1_6ck74 = 0 time = 750
.meas tran vdout1_6ck74 FIND v(dout1_6) AT=750.05n

* CHECK dout1_7 Vdout1_7ck74 = 0 time = 750
.meas tran vdout1_7ck74 FIND v(dout1_7) AT=750.05n

* CHECK dout0_0 Vdout0_0ck75 = 0 time = 760
.meas tran vdout0_0ck75 FIND v(dout0_0) AT=760.05n

* CHECK dout0_1 Vdout0_1ck75 = 1.8 time = 760
.meas tran vdout0_1ck75 FIND v(dout0_1) AT=760.05n

* CHECK dout0_2 Vdout0_2ck75 = 0 time = 760
.meas tran vdout0_2ck75 FIND v(dout0_2) AT=760.05n

* CHECK dout0_3 Vdout0_3ck75 = 1.8 time = 760
.meas tran vdout0_3ck75 FIND v(dout0_3) AT=760.05n

* CHECK dout0_4 Vdout0_4ck75 = 0 time = 760
.meas tran vdout0_4ck75 FIND v(dout0_4) AT=760.05n

* CHECK dout0_5 Vdout0_5ck75 = 0 time = 760
.meas tran vdout0_5ck75 FIND v(dout0_5) AT=760.05n

* CHECK dout0_6 Vdout0_6ck75 = 0 time = 760
.meas tran vdout0_6ck75 FIND v(dout0_6) AT=760.05n

* CHECK dout0_7 Vdout0_7ck75 = 1.8 time = 760
.meas tran vdout0_7ck75 FIND v(dout0_7) AT=760.05n

* CHECK dout0_0 Vdout0_0ck77 = 0 time = 780
.meas tran vdout0_0ck77 FIND v(dout0_0) AT=780.05n

* CHECK dout0_1 Vdout0_1ck77 = 1.8 time = 780
.meas tran vdout0_1ck77 FIND v(dout0_1) AT=780.05n

* CHECK dout0_2 Vdout0_2ck77 = 0 time = 780
.meas tran vdout0_2ck77 FIND v(dout0_2) AT=780.05n

* CHECK dout0_3 Vdout0_3ck77 = 0 time = 780
.meas tran vdout0_3ck77 FIND v(dout0_3) AT=780.05n

* CHECK dout0_4 Vdout0_4ck77 = 1.8 time = 780
.meas tran vdout0_4ck77 FIND v(dout0_4) AT=780.05n

* CHECK dout0_5 Vdout0_5ck77 = 0 time = 780
.meas tran vdout0_5ck77 FIND v(dout0_5) AT=780.05n

* CHECK dout0_6 Vdout0_6ck77 = 1.8 time = 780
.meas tran vdout0_6ck77 FIND v(dout0_6) AT=780.05n

* CHECK dout0_7 Vdout0_7ck77 = 1.8 time = 780
.meas tran vdout0_7ck77 FIND v(dout0_7) AT=780.05n

* CHECK dout1_0 Vdout1_0ck77 = 0 time = 780
.meas tran vdout1_0ck77 FIND v(dout1_0) AT=780.05n

* CHECK dout1_1 Vdout1_1ck77 = 1.8 time = 780
.meas tran vdout1_1ck77 FIND v(dout1_1) AT=780.05n

* CHECK dout1_2 Vdout1_2ck77 = 0 time = 780
.meas tran vdout1_2ck77 FIND v(dout1_2) AT=780.05n

* CHECK dout1_3 Vdout1_3ck77 = 0 time = 780
.meas tran vdout1_3ck77 FIND v(dout1_3) AT=780.05n

* CHECK dout1_4 Vdout1_4ck77 = 1.8 time = 780
.meas tran vdout1_4ck77 FIND v(dout1_4) AT=780.05n

* CHECK dout1_5 Vdout1_5ck77 = 0 time = 780
.meas tran vdout1_5ck77 FIND v(dout1_5) AT=780.05n

* CHECK dout1_6 Vdout1_6ck77 = 1.8 time = 780
.meas tran vdout1_6ck77 FIND v(dout1_6) AT=780.05n

* CHECK dout1_7 Vdout1_7ck77 = 1.8 time = 780
.meas tran vdout1_7ck77 FIND v(dout1_7) AT=780.05n

* CHECK dout1_0 Vdout1_0ck79 = 0 time = 800
.meas tran vdout1_0ck79 FIND v(dout1_0) AT=800.05n

* CHECK dout1_1 Vdout1_1ck79 = 0 time = 800
.meas tran vdout1_1ck79 FIND v(dout1_1) AT=800.05n

* CHECK dout1_2 Vdout1_2ck79 = 0 time = 800
.meas tran vdout1_2ck79 FIND v(dout1_2) AT=800.05n

* CHECK dout1_3 Vdout1_3ck79 = 0 time = 800
.meas tran vdout1_3ck79 FIND v(dout1_3) AT=800.05n

* CHECK dout1_4 Vdout1_4ck79 = 0 time = 800
.meas tran vdout1_4ck79 FIND v(dout1_4) AT=800.05n

* CHECK dout1_5 Vdout1_5ck79 = 1.8 time = 800
.meas tran vdout1_5ck79 FIND v(dout1_5) AT=800.05n

* CHECK dout1_6 Vdout1_6ck79 = 0 time = 800
.meas tran vdout1_6ck79 FIND v(dout1_6) AT=800.05n

* CHECK dout1_7 Vdout1_7ck79 = 1.8 time = 800
.meas tran vdout1_7ck79 FIND v(dout1_7) AT=800.05n

* CHECK dout0_0 Vdout0_0ck80 = 0 time = 810
.meas tran vdout0_0ck80 FIND v(dout0_0) AT=810.05n

* CHECK dout0_1 Vdout0_1ck80 = 0 time = 810
.meas tran vdout0_1ck80 FIND v(dout0_1) AT=810.05n

* CHECK dout0_2 Vdout0_2ck80 = 0 time = 810
.meas tran vdout0_2ck80 FIND v(dout0_2) AT=810.05n

* CHECK dout0_3 Vdout0_3ck80 = 1.8 time = 810
.meas tran vdout0_3ck80 FIND v(dout0_3) AT=810.05n

* CHECK dout0_4 Vdout0_4ck80 = 0 time = 810
.meas tran vdout0_4ck80 FIND v(dout0_4) AT=810.05n

* CHECK dout0_5 Vdout0_5ck80 = 1.8 time = 810
.meas tran vdout0_5ck80 FIND v(dout0_5) AT=810.05n

* CHECK dout0_6 Vdout0_6ck80 = 0 time = 810
.meas tran vdout0_6ck80 FIND v(dout0_6) AT=810.05n

* CHECK dout0_7 Vdout0_7ck80 = 0 time = 810
.meas tran vdout0_7ck80 FIND v(dout0_7) AT=810.05n

* CHECK dout1_0 Vdout1_0ck80 = 1.8 time = 810
.meas tran vdout1_0ck80 FIND v(dout1_0) AT=810.05n

* CHECK dout1_1 Vdout1_1ck80 = 1.8 time = 810
.meas tran vdout1_1ck80 FIND v(dout1_1) AT=810.05n

* CHECK dout1_2 Vdout1_2ck80 = 1.8 time = 810
.meas tran vdout1_2ck80 FIND v(dout1_2) AT=810.05n

* CHECK dout1_3 Vdout1_3ck80 = 0 time = 810
.meas tran vdout1_3ck80 FIND v(dout1_3) AT=810.05n

* CHECK dout1_4 Vdout1_4ck80 = 1.8 time = 810
.meas tran vdout1_4ck80 FIND v(dout1_4) AT=810.05n

* CHECK dout1_5 Vdout1_5ck80 = 0 time = 810
.meas tran vdout1_5ck80 FIND v(dout1_5) AT=810.05n

* CHECK dout1_6 Vdout1_6ck80 = 1.8 time = 810
.meas tran vdout1_6ck80 FIND v(dout1_6) AT=810.05n

* CHECK dout1_7 Vdout1_7ck80 = 0 time = 810
.meas tran vdout1_7ck80 FIND v(dout1_7) AT=810.05n

* CHECK dout0_0 Vdout0_0ck82 = 0 time = 830
.meas tran vdout0_0ck82 FIND v(dout0_0) AT=830.05n

* CHECK dout0_1 Vdout0_1ck82 = 0 time = 830
.meas tran vdout0_1ck82 FIND v(dout0_1) AT=830.05n

* CHECK dout0_2 Vdout0_2ck82 = 0 time = 830
.meas tran vdout0_2ck82 FIND v(dout0_2) AT=830.05n

* CHECK dout0_3 Vdout0_3ck82 = 1.8 time = 830
.meas tran vdout0_3ck82 FIND v(dout0_3) AT=830.05n

* CHECK dout0_4 Vdout0_4ck82 = 0 time = 830
.meas tran vdout0_4ck82 FIND v(dout0_4) AT=830.05n

* CHECK dout0_5 Vdout0_5ck82 = 1.8 time = 830
.meas tran vdout0_5ck82 FIND v(dout0_5) AT=830.05n

* CHECK dout0_6 Vdout0_6ck82 = 0 time = 830
.meas tran vdout0_6ck82 FIND v(dout0_6) AT=830.05n

* CHECK dout0_7 Vdout0_7ck82 = 0 time = 830
.meas tran vdout0_7ck82 FIND v(dout0_7) AT=830.05n

* CHECK dout1_0 Vdout1_0ck82 = 0 time = 830
.meas tran vdout1_0ck82 FIND v(dout1_0) AT=830.05n

* CHECK dout1_1 Vdout1_1ck82 = 0 time = 830
.meas tran vdout1_1ck82 FIND v(dout1_1) AT=830.05n

* CHECK dout1_2 Vdout1_2ck82 = 1.8 time = 830
.meas tran vdout1_2ck82 FIND v(dout1_2) AT=830.05n

* CHECK dout1_3 Vdout1_3ck82 = 1.8 time = 830
.meas tran vdout1_3ck82 FIND v(dout1_3) AT=830.05n

* CHECK dout1_4 Vdout1_4ck82 = 0 time = 830
.meas tran vdout1_4ck82 FIND v(dout1_4) AT=830.05n

* CHECK dout1_5 Vdout1_5ck82 = 0 time = 830
.meas tran vdout1_5ck82 FIND v(dout1_5) AT=830.05n

* CHECK dout1_6 Vdout1_6ck82 = 0 time = 830
.meas tran vdout1_6ck82 FIND v(dout1_6) AT=830.05n

* CHECK dout1_7 Vdout1_7ck82 = 0 time = 830
.meas tran vdout1_7ck82 FIND v(dout1_7) AT=830.05n

* CHECK dout0_0 Vdout0_0ck84 = 0 time = 850
.meas tran vdout0_0ck84 FIND v(dout0_0) AT=850.05n

* CHECK dout0_1 Vdout0_1ck84 = 0 time = 850
.meas tran vdout0_1ck84 FIND v(dout0_1) AT=850.05n

* CHECK dout0_2 Vdout0_2ck84 = 0 time = 850
.meas tran vdout0_2ck84 FIND v(dout0_2) AT=850.05n

* CHECK dout0_3 Vdout0_3ck84 = 1.8 time = 850
.meas tran vdout0_3ck84 FIND v(dout0_3) AT=850.05n

* CHECK dout0_4 Vdout0_4ck84 = 0 time = 850
.meas tran vdout0_4ck84 FIND v(dout0_4) AT=850.05n

* CHECK dout0_5 Vdout0_5ck84 = 1.8 time = 850
.meas tran vdout0_5ck84 FIND v(dout0_5) AT=850.05n

* CHECK dout0_6 Vdout0_6ck84 = 0 time = 850
.meas tran vdout0_6ck84 FIND v(dout0_6) AT=850.05n

* CHECK dout0_7 Vdout0_7ck84 = 0 time = 850
.meas tran vdout0_7ck84 FIND v(dout0_7) AT=850.05n

* CHECK dout1_0 Vdout1_0ck84 = 0 time = 850
.meas tran vdout1_0ck84 FIND v(dout1_0) AT=850.05n

* CHECK dout1_1 Vdout1_1ck84 = 0 time = 850
.meas tran vdout1_1ck84 FIND v(dout1_1) AT=850.05n

* CHECK dout1_2 Vdout1_2ck84 = 1.8 time = 850
.meas tran vdout1_2ck84 FIND v(dout1_2) AT=850.05n

* CHECK dout1_3 Vdout1_3ck84 = 1.8 time = 850
.meas tran vdout1_3ck84 FIND v(dout1_3) AT=850.05n

* CHECK dout1_4 Vdout1_4ck84 = 0 time = 850
.meas tran vdout1_4ck84 FIND v(dout1_4) AT=850.05n

* CHECK dout1_5 Vdout1_5ck84 = 0 time = 850
.meas tran vdout1_5ck84 FIND v(dout1_5) AT=850.05n

* CHECK dout1_6 Vdout1_6ck84 = 0 time = 850
.meas tran vdout1_6ck84 FIND v(dout1_6) AT=850.05n

* CHECK dout1_7 Vdout1_7ck84 = 0 time = 850
.meas tran vdout1_7ck84 FIND v(dout1_7) AT=850.05n

* CHECK dout1_0 Vdout1_0ck88 = 1.8 time = 890
.meas tran vdout1_0ck88 FIND v(dout1_0) AT=890.05n

* CHECK dout1_1 Vdout1_1ck88 = 1.8 time = 890
.meas tran vdout1_1ck88 FIND v(dout1_1) AT=890.05n

* CHECK dout1_2 Vdout1_2ck88 = 1.8 time = 890
.meas tran vdout1_2ck88 FIND v(dout1_2) AT=890.05n

* CHECK dout1_3 Vdout1_3ck88 = 1.8 time = 890
.meas tran vdout1_3ck88 FIND v(dout1_3) AT=890.05n

* CHECK dout1_4 Vdout1_4ck88 = 0 time = 890
.meas tran vdout1_4ck88 FIND v(dout1_4) AT=890.05n

* CHECK dout1_5 Vdout1_5ck88 = 1.8 time = 890
.meas tran vdout1_5ck88 FIND v(dout1_5) AT=890.05n

* CHECK dout1_6 Vdout1_6ck88 = 1.8 time = 890
.meas tran vdout1_6ck88 FIND v(dout1_6) AT=890.05n

* CHECK dout1_7 Vdout1_7ck88 = 0 time = 890
.meas tran vdout1_7ck88 FIND v(dout1_7) AT=890.05n

* CHECK dout0_0 Vdout0_0ck90 = 1.8 time = 910
.meas tran vdout0_0ck90 FIND v(dout0_0) AT=910.05n

* CHECK dout0_1 Vdout0_1ck90 = 1.8 time = 910
.meas tran vdout0_1ck90 FIND v(dout0_1) AT=910.05n

* CHECK dout0_2 Vdout0_2ck90 = 1.8 time = 910
.meas tran vdout0_2ck90 FIND v(dout0_2) AT=910.05n

* CHECK dout0_3 Vdout0_3ck90 = 1.8 time = 910
.meas tran vdout0_3ck90 FIND v(dout0_3) AT=910.05n

* CHECK dout0_4 Vdout0_4ck90 = 0 time = 910
.meas tran vdout0_4ck90 FIND v(dout0_4) AT=910.05n

* CHECK dout0_5 Vdout0_5ck90 = 1.8 time = 910
.meas tran vdout0_5ck90 FIND v(dout0_5) AT=910.05n

* CHECK dout0_6 Vdout0_6ck90 = 1.8 time = 910
.meas tran vdout0_6ck90 FIND v(dout0_6) AT=910.05n

* CHECK dout0_7 Vdout0_7ck90 = 0 time = 910
.meas tran vdout0_7ck90 FIND v(dout0_7) AT=910.05n

* CHECK dout1_0 Vdout1_0ck91 = 0 time = 920
.meas tran vdout1_0ck91 FIND v(dout1_0) AT=920.05n

* CHECK dout1_1 Vdout1_1ck91 = 0 time = 920
.meas tran vdout1_1ck91 FIND v(dout1_1) AT=920.05n

* CHECK dout1_2 Vdout1_2ck91 = 0 time = 920
.meas tran vdout1_2ck91 FIND v(dout1_2) AT=920.05n

* CHECK dout1_3 Vdout1_3ck91 = 1.8 time = 920
.meas tran vdout1_3ck91 FIND v(dout1_3) AT=920.05n

* CHECK dout1_4 Vdout1_4ck91 = 0 time = 920
.meas tran vdout1_4ck91 FIND v(dout1_4) AT=920.05n

* CHECK dout1_5 Vdout1_5ck91 = 1.8 time = 920
.meas tran vdout1_5ck91 FIND v(dout1_5) AT=920.05n

* CHECK dout1_6 Vdout1_6ck91 = 0 time = 920
.meas tran vdout1_6ck91 FIND v(dout1_6) AT=920.05n

* CHECK dout1_7 Vdout1_7ck91 = 0 time = 920
.meas tran vdout1_7ck91 FIND v(dout1_7) AT=920.05n

* CHECK dout1_0 Vdout1_0ck92 = 1.8 time = 930
.meas tran vdout1_0ck92 FIND v(dout1_0) AT=930.05n

* CHECK dout1_1 Vdout1_1ck92 = 1.8 time = 930
.meas tran vdout1_1ck92 FIND v(dout1_1) AT=930.05n

* CHECK dout1_2 Vdout1_2ck92 = 0 time = 930
.meas tran vdout1_2ck92 FIND v(dout1_2) AT=930.05n

* CHECK dout1_3 Vdout1_3ck92 = 1.8 time = 930
.meas tran vdout1_3ck92 FIND v(dout1_3) AT=930.05n

* CHECK dout1_4 Vdout1_4ck92 = 0 time = 930
.meas tran vdout1_4ck92 FIND v(dout1_4) AT=930.05n

* CHECK dout1_5 Vdout1_5ck92 = 0 time = 930
.meas tran vdout1_5ck92 FIND v(dout1_5) AT=930.05n

* CHECK dout1_6 Vdout1_6ck92 = 0 time = 930
.meas tran vdout1_6ck92 FIND v(dout1_6) AT=930.05n

* CHECK dout1_7 Vdout1_7ck92 = 0 time = 930
.meas tran vdout1_7ck92 FIND v(dout1_7) AT=930.05n

* CHECK dout0_0 Vdout0_0ck93 = 1.8 time = 940
.meas tran vdout0_0ck93 FIND v(dout0_0) AT=940.05n

* CHECK dout0_1 Vdout0_1ck93 = 1.8 time = 940
.meas tran vdout0_1ck93 FIND v(dout0_1) AT=940.05n

* CHECK dout0_2 Vdout0_2ck93 = 0 time = 940
.meas tran vdout0_2ck93 FIND v(dout0_2) AT=940.05n

* CHECK dout0_3 Vdout0_3ck93 = 1.8 time = 940
.meas tran vdout0_3ck93 FIND v(dout0_3) AT=940.05n

* CHECK dout0_4 Vdout0_4ck93 = 0 time = 940
.meas tran vdout0_4ck93 FIND v(dout0_4) AT=940.05n

* CHECK dout0_5 Vdout0_5ck93 = 0 time = 940
.meas tran vdout0_5ck93 FIND v(dout0_5) AT=940.05n

* CHECK dout0_6 Vdout0_6ck93 = 0 time = 940
.meas tran vdout0_6ck93 FIND v(dout0_6) AT=940.05n

* CHECK dout0_7 Vdout0_7ck93 = 0 time = 940
.meas tran vdout0_7ck93 FIND v(dout0_7) AT=940.05n

* CHECK dout0_0 Vdout0_0ck94 = 1.8 time = 950
.meas tran vdout0_0ck94 FIND v(dout0_0) AT=950.05n

* CHECK dout0_1 Vdout0_1ck94 = 0 time = 950
.meas tran vdout0_1ck94 FIND v(dout0_1) AT=950.05n

* CHECK dout0_2 Vdout0_2ck94 = 0 time = 950
.meas tran vdout0_2ck94 FIND v(dout0_2) AT=950.05n

* CHECK dout0_3 Vdout0_3ck94 = 1.8 time = 950
.meas tran vdout0_3ck94 FIND v(dout0_3) AT=950.05n

* CHECK dout0_4 Vdout0_4ck94 = 0 time = 950
.meas tran vdout0_4ck94 FIND v(dout0_4) AT=950.05n

* CHECK dout0_5 Vdout0_5ck94 = 0 time = 950
.meas tran vdout0_5ck94 FIND v(dout0_5) AT=950.05n

* CHECK dout0_6 Vdout0_6ck94 = 1.8 time = 950
.meas tran vdout0_6ck94 FIND v(dout0_6) AT=950.05n

* CHECK dout0_7 Vdout0_7ck94 = 0 time = 950
.meas tran vdout0_7ck94 FIND v(dout0_7) AT=950.05n

* CHECK dout1_0 Vdout1_0ck95 = 1.8 time = 960
.meas tran vdout1_0ck95 FIND v(dout1_0) AT=960.05n

* CHECK dout1_1 Vdout1_1ck95 = 1.8 time = 960
.meas tran vdout1_1ck95 FIND v(dout1_1) AT=960.05n

* CHECK dout1_2 Vdout1_2ck95 = 0 time = 960
.meas tran vdout1_2ck95 FIND v(dout1_2) AT=960.05n

* CHECK dout1_3 Vdout1_3ck95 = 1.8 time = 960
.meas tran vdout1_3ck95 FIND v(dout1_3) AT=960.05n

* CHECK dout1_4 Vdout1_4ck95 = 0 time = 960
.meas tran vdout1_4ck95 FIND v(dout1_4) AT=960.05n

* CHECK dout1_5 Vdout1_5ck95 = 0 time = 960
.meas tran vdout1_5ck95 FIND v(dout1_5) AT=960.05n

* CHECK dout1_6 Vdout1_6ck95 = 0 time = 960
.meas tran vdout1_6ck95 FIND v(dout1_6) AT=960.05n

* CHECK dout1_7 Vdout1_7ck95 = 0 time = 960
.meas tran vdout1_7ck95 FIND v(dout1_7) AT=960.05n

* CHECK dout0_0 Vdout0_0ck96 = 1.8 time = 970
.meas tran vdout0_0ck96 FIND v(dout0_0) AT=970.05n

* CHECK dout0_1 Vdout0_1ck96 = 1.8 time = 970
.meas tran vdout0_1ck96 FIND v(dout0_1) AT=970.05n

* CHECK dout0_2 Vdout0_2ck96 = 0 time = 970
.meas tran vdout0_2ck96 FIND v(dout0_2) AT=970.05n

* CHECK dout0_3 Vdout0_3ck96 = 1.8 time = 970
.meas tran vdout0_3ck96 FIND v(dout0_3) AT=970.05n

* CHECK dout0_4 Vdout0_4ck96 = 0 time = 970
.meas tran vdout0_4ck96 FIND v(dout0_4) AT=970.05n

* CHECK dout0_5 Vdout0_5ck96 = 0 time = 970
.meas tran vdout0_5ck96 FIND v(dout0_5) AT=970.05n

* CHECK dout0_6 Vdout0_6ck96 = 0 time = 970
.meas tran vdout0_6ck96 FIND v(dout0_6) AT=970.05n

* CHECK dout0_7 Vdout0_7ck96 = 0 time = 970
.meas tran vdout0_7ck96 FIND v(dout0_7) AT=970.05n

* CHECK dout1_0 Vdout1_0ck96 = 1.8 time = 970
.meas tran vdout1_0ck96 FIND v(dout1_0) AT=970.05n

* CHECK dout1_1 Vdout1_1ck96 = 1.8 time = 970
.meas tran vdout1_1ck96 FIND v(dout1_1) AT=970.05n

* CHECK dout1_2 Vdout1_2ck96 = 0 time = 970
.meas tran vdout1_2ck96 FIND v(dout1_2) AT=970.05n

* CHECK dout1_3 Vdout1_3ck96 = 1.8 time = 970
.meas tran vdout1_3ck96 FIND v(dout1_3) AT=970.05n

* CHECK dout1_4 Vdout1_4ck96 = 0 time = 970
.meas tran vdout1_4ck96 FIND v(dout1_4) AT=970.05n

* CHECK dout1_5 Vdout1_5ck96 = 0 time = 970
.meas tran vdout1_5ck96 FIND v(dout1_5) AT=970.05n

* CHECK dout1_6 Vdout1_6ck96 = 0 time = 970
.meas tran vdout1_6ck96 FIND v(dout1_6) AT=970.05n

* CHECK dout1_7 Vdout1_7ck96 = 0 time = 970
.meas tran vdout1_7ck96 FIND v(dout1_7) AT=970.05n

* CHECK dout0_0 Vdout0_0ck97 = 1.8 time = 980
.meas tran vdout0_0ck97 FIND v(dout0_0) AT=980.05n

* CHECK dout0_1 Vdout0_1ck97 = 1.8 time = 980
.meas tran vdout0_1ck97 FIND v(dout0_1) AT=980.05n

* CHECK dout0_2 Vdout0_2ck97 = 0 time = 980
.meas tran vdout0_2ck97 FIND v(dout0_2) AT=980.05n

* CHECK dout0_3 Vdout0_3ck97 = 1.8 time = 980
.meas tran vdout0_3ck97 FIND v(dout0_3) AT=980.05n

* CHECK dout0_4 Vdout0_4ck97 = 0 time = 980
.meas tran vdout0_4ck97 FIND v(dout0_4) AT=980.05n

* CHECK dout0_5 Vdout0_5ck97 = 0 time = 980
.meas tran vdout0_5ck97 FIND v(dout0_5) AT=980.05n

* CHECK dout0_6 Vdout0_6ck97 = 0 time = 980
.meas tran vdout0_6ck97 FIND v(dout0_6) AT=980.05n

* CHECK dout0_7 Vdout0_7ck97 = 0 time = 980
.meas tran vdout0_7ck97 FIND v(dout0_7) AT=980.05n

* CHECK dout1_0 Vdout1_0ck97 = 1.8 time = 980
.meas tran vdout1_0ck97 FIND v(dout1_0) AT=980.05n

* CHECK dout1_1 Vdout1_1ck97 = 0 time = 980
.meas tran vdout1_1ck97 FIND v(dout1_1) AT=980.05n

* CHECK dout1_2 Vdout1_2ck97 = 0 time = 980
.meas tran vdout1_2ck97 FIND v(dout1_2) AT=980.05n

* CHECK dout1_3 Vdout1_3ck97 = 1.8 time = 980
.meas tran vdout1_3ck97 FIND v(dout1_3) AT=980.05n

* CHECK dout1_4 Vdout1_4ck97 = 0 time = 980
.meas tran vdout1_4ck97 FIND v(dout1_4) AT=980.05n

* CHECK dout1_5 Vdout1_5ck97 = 0 time = 980
.meas tran vdout1_5ck97 FIND v(dout1_5) AT=980.05n

* CHECK dout1_6 Vdout1_6ck97 = 1.8 time = 980
.meas tran vdout1_6ck97 FIND v(dout1_6) AT=980.05n

* CHECK dout1_7 Vdout1_7ck97 = 0 time = 980
.meas tran vdout1_7ck97 FIND v(dout1_7) AT=980.05n

* CHECK dout0_0 Vdout0_0ck98 = 0 time = 990
.meas tran vdout0_0ck98 FIND v(dout0_0) AT=990.05n

* CHECK dout0_1 Vdout0_1ck98 = 0 time = 990
.meas tran vdout0_1ck98 FIND v(dout0_1) AT=990.05n

* CHECK dout0_2 Vdout0_2ck98 = 1.8 time = 990
.meas tran vdout0_2ck98 FIND v(dout0_2) AT=990.05n

* CHECK dout0_3 Vdout0_3ck98 = 0 time = 990
.meas tran vdout0_3ck98 FIND v(dout0_3) AT=990.05n

* CHECK dout0_4 Vdout0_4ck98 = 0 time = 990
.meas tran vdout0_4ck98 FIND v(dout0_4) AT=990.05n

* CHECK dout0_5 Vdout0_5ck98 = 1.8 time = 990
.meas tran vdout0_5ck98 FIND v(dout0_5) AT=990.05n

* CHECK dout0_6 Vdout0_6ck98 = 1.8 time = 990
.meas tran vdout0_6ck98 FIND v(dout0_6) AT=990.05n

* CHECK dout0_7 Vdout0_7ck98 = 1.8 time = 990
.meas tran vdout0_7ck98 FIND v(dout0_7) AT=990.05n

* CHECK dout1_0 Vdout1_0ck99 = 0 time = 1000
.meas tran vdout1_0ck99 FIND v(dout1_0) AT=1000.05n

* CHECK dout1_1 Vdout1_1ck99 = 0 time = 1000
.meas tran vdout1_1ck99 FIND v(dout1_1) AT=1000.05n

* CHECK dout1_2 Vdout1_2ck99 = 1.8 time = 1000
.meas tran vdout1_2ck99 FIND v(dout1_2) AT=1000.05n

* CHECK dout1_3 Vdout1_3ck99 = 0 time = 1000
.meas tran vdout1_3ck99 FIND v(dout1_3) AT=1000.05n

* CHECK dout1_4 Vdout1_4ck99 = 0 time = 1000
.meas tran vdout1_4ck99 FIND v(dout1_4) AT=1000.05n

* CHECK dout1_5 Vdout1_5ck99 = 1.8 time = 1000
.meas tran vdout1_5ck99 FIND v(dout1_5) AT=1000.05n

* CHECK dout1_6 Vdout1_6ck99 = 1.8 time = 1000
.meas tran vdout1_6ck99 FIND v(dout1_6) AT=1000.05n

* CHECK dout1_7 Vdout1_7ck99 = 1.8 time = 1000
.meas tran vdout1_7ck99 FIND v(dout1_7) AT=1000.05n

* CHECK dout1_0 Vdout1_0ck100 = 0 time = 1010
.meas tran vdout1_0ck100 FIND v(dout1_0) AT=1010.05n

* CHECK dout1_1 Vdout1_1ck100 = 1.8 time = 1010
.meas tran vdout1_1ck100 FIND v(dout1_1) AT=1010.05n

* CHECK dout1_2 Vdout1_2ck100 = 0 time = 1010
.meas tran vdout1_2ck100 FIND v(dout1_2) AT=1010.05n

* CHECK dout1_3 Vdout1_3ck100 = 1.8 time = 1010
.meas tran vdout1_3ck100 FIND v(dout1_3) AT=1010.05n

* CHECK dout1_4 Vdout1_4ck100 = 1.8 time = 1010
.meas tran vdout1_4ck100 FIND v(dout1_4) AT=1010.05n

* CHECK dout1_5 Vdout1_5ck100 = 0 time = 1010
.meas tran vdout1_5ck100 FIND v(dout1_5) AT=1010.05n

* CHECK dout1_6 Vdout1_6ck100 = 0 time = 1010
.meas tran vdout1_6ck100 FIND v(dout1_6) AT=1010.05n

* CHECK dout1_7 Vdout1_7ck100 = 0 time = 1010
.meas tran vdout1_7ck100 FIND v(dout1_7) AT=1010.05n

* CHECK dout1_0 Vdout1_0ck101 = 1.8 time = 1020
.meas tran vdout1_0ck101 FIND v(dout1_0) AT=1020.05n

* CHECK dout1_1 Vdout1_1ck101 = 1.8 time = 1020
.meas tran vdout1_1ck101 FIND v(dout1_1) AT=1020.05n

* CHECK dout1_2 Vdout1_2ck101 = 0 time = 1020
.meas tran vdout1_2ck101 FIND v(dout1_2) AT=1020.05n

* CHECK dout1_3 Vdout1_3ck101 = 1.8 time = 1020
.meas tran vdout1_3ck101 FIND v(dout1_3) AT=1020.05n

* CHECK dout1_4 Vdout1_4ck101 = 0 time = 1020
.meas tran vdout1_4ck101 FIND v(dout1_4) AT=1020.05n

* CHECK dout1_5 Vdout1_5ck101 = 0 time = 1020
.meas tran vdout1_5ck101 FIND v(dout1_5) AT=1020.05n

* CHECK dout1_6 Vdout1_6ck101 = 0 time = 1020
.meas tran vdout1_6ck101 FIND v(dout1_6) AT=1020.05n

* CHECK dout1_7 Vdout1_7ck101 = 0 time = 1020
.meas tran vdout1_7ck101 FIND v(dout1_7) AT=1020.05n

* CHECK dout1_0 Vdout1_0ck102 = 1.8 time = 1030
.meas tran vdout1_0ck102 FIND v(dout1_0) AT=1030.05n

* CHECK dout1_1 Vdout1_1ck102 = 0 time = 1030
.meas tran vdout1_1ck102 FIND v(dout1_1) AT=1030.05n

* CHECK dout1_2 Vdout1_2ck102 = 0 time = 1030
.meas tran vdout1_2ck102 FIND v(dout1_2) AT=1030.05n

* CHECK dout1_3 Vdout1_3ck102 = 1.8 time = 1030
.meas tran vdout1_3ck102 FIND v(dout1_3) AT=1030.05n

* CHECK dout1_4 Vdout1_4ck102 = 0 time = 1030
.meas tran vdout1_4ck102 FIND v(dout1_4) AT=1030.05n

* CHECK dout1_5 Vdout1_5ck102 = 0 time = 1030
.meas tran vdout1_5ck102 FIND v(dout1_5) AT=1030.05n

* CHECK dout1_6 Vdout1_6ck102 = 1.8 time = 1030
.meas tran vdout1_6ck102 FIND v(dout1_6) AT=1030.05n

* CHECK dout1_7 Vdout1_7ck102 = 0 time = 1030
.meas tran vdout1_7ck102 FIND v(dout1_7) AT=1030.05n

* CHECK dout1_0 Vdout1_0ck103 = 1.8 time = 1040
.meas tran vdout1_0ck103 FIND v(dout1_0) AT=1040.05n

* CHECK dout1_1 Vdout1_1ck103 = 0 time = 1040
.meas tran vdout1_1ck103 FIND v(dout1_1) AT=1040.05n

* CHECK dout1_2 Vdout1_2ck103 = 0 time = 1040
.meas tran vdout1_2ck103 FIND v(dout1_2) AT=1040.05n

* CHECK dout1_3 Vdout1_3ck103 = 1.8 time = 1040
.meas tran vdout1_3ck103 FIND v(dout1_3) AT=1040.05n

* CHECK dout1_4 Vdout1_4ck103 = 0 time = 1040
.meas tran vdout1_4ck103 FIND v(dout1_4) AT=1040.05n

* CHECK dout1_5 Vdout1_5ck103 = 0 time = 1040
.meas tran vdout1_5ck103 FIND v(dout1_5) AT=1040.05n

* CHECK dout1_6 Vdout1_6ck103 = 1.8 time = 1040
.meas tran vdout1_6ck103 FIND v(dout1_6) AT=1040.05n

* CHECK dout1_7 Vdout1_7ck103 = 0 time = 1040
.meas tran vdout1_7ck103 FIND v(dout1_7) AT=1040.05n

* CHECK dout0_0 Vdout0_0ck104 = 0 time = 1050
.meas tran vdout0_0ck104 FIND v(dout0_0) AT=1050.05n

* CHECK dout0_1 Vdout0_1ck104 = 0 time = 1050
.meas tran vdout0_1ck104 FIND v(dout0_1) AT=1050.05n

* CHECK dout0_2 Vdout0_2ck104 = 0 time = 1050
.meas tran vdout0_2ck104 FIND v(dout0_2) AT=1050.05n

* CHECK dout0_3 Vdout0_3ck104 = 0 time = 1050
.meas tran vdout0_3ck104 FIND v(dout0_3) AT=1050.05n

* CHECK dout0_4 Vdout0_4ck104 = 1.8 time = 1050
.meas tran vdout0_4ck104 FIND v(dout0_4) AT=1050.05n

* CHECK dout0_5 Vdout0_5ck104 = 0 time = 1050
.meas tran vdout0_5ck104 FIND v(dout0_5) AT=1050.05n

* CHECK dout0_6 Vdout0_6ck104 = 1.8 time = 1050
.meas tran vdout0_6ck104 FIND v(dout0_6) AT=1050.05n

* CHECK dout0_7 Vdout0_7ck104 = 0 time = 1050
.meas tran vdout0_7ck104 FIND v(dout0_7) AT=1050.05n

* CHECK dout1_0 Vdout1_0ck104 = 0 time = 1050
.meas tran vdout1_0ck104 FIND v(dout1_0) AT=1050.05n

* CHECK dout1_1 Vdout1_1ck104 = 1.8 time = 1050
.meas tran vdout1_1ck104 FIND v(dout1_1) AT=1050.05n

* CHECK dout1_2 Vdout1_2ck104 = 0 time = 1050
.meas tran vdout1_2ck104 FIND v(dout1_2) AT=1050.05n

* CHECK dout1_3 Vdout1_3ck104 = 1.8 time = 1050
.meas tran vdout1_3ck104 FIND v(dout1_3) AT=1050.05n

* CHECK dout1_4 Vdout1_4ck104 = 1.8 time = 1050
.meas tran vdout1_4ck104 FIND v(dout1_4) AT=1050.05n

* CHECK dout1_5 Vdout1_5ck104 = 0 time = 1050
.meas tran vdout1_5ck104 FIND v(dout1_5) AT=1050.05n

* CHECK dout1_6 Vdout1_6ck104 = 0 time = 1050
.meas tran vdout1_6ck104 FIND v(dout1_6) AT=1050.05n

* CHECK dout1_7 Vdout1_7ck104 = 0 time = 1050
.meas tran vdout1_7ck104 FIND v(dout1_7) AT=1050.05n

* CHECK dout0_0 Vdout0_0ck106 = 0 time = 1070
.meas tran vdout0_0ck106 FIND v(dout0_0) AT=1070.05n

* CHECK dout0_1 Vdout0_1ck106 = 1.8 time = 1070
.meas tran vdout0_1ck106 FIND v(dout0_1) AT=1070.05n

* CHECK dout0_2 Vdout0_2ck106 = 0 time = 1070
.meas tran vdout0_2ck106 FIND v(dout0_2) AT=1070.05n

* CHECK dout0_3 Vdout0_3ck106 = 0 time = 1070
.meas tran vdout0_3ck106 FIND v(dout0_3) AT=1070.05n

* CHECK dout0_4 Vdout0_4ck106 = 1.8 time = 1070
.meas tran vdout0_4ck106 FIND v(dout0_4) AT=1070.05n

* CHECK dout0_5 Vdout0_5ck106 = 0 time = 1070
.meas tran vdout0_5ck106 FIND v(dout0_5) AT=1070.05n

* CHECK dout0_6 Vdout0_6ck106 = 1.8 time = 1070
.meas tran vdout0_6ck106 FIND v(dout0_6) AT=1070.05n

* CHECK dout0_7 Vdout0_7ck106 = 1.8 time = 1070
.meas tran vdout0_7ck106 FIND v(dout0_7) AT=1070.05n

* CHECK dout0_0 Vdout0_0ck108 = 1.8 time = 1090
.meas tran vdout0_0ck108 FIND v(dout0_0) AT=1090.05n

* CHECK dout0_1 Vdout0_1ck108 = 1.8 time = 1090
.meas tran vdout0_1ck108 FIND v(dout0_1) AT=1090.05n

* CHECK dout0_2 Vdout0_2ck108 = 1.8 time = 1090
.meas tran vdout0_2ck108 FIND v(dout0_2) AT=1090.05n

* CHECK dout0_3 Vdout0_3ck108 = 0 time = 1090
.meas tran vdout0_3ck108 FIND v(dout0_3) AT=1090.05n

* CHECK dout0_4 Vdout0_4ck108 = 1.8 time = 1090
.meas tran vdout0_4ck108 FIND v(dout0_4) AT=1090.05n

* CHECK dout0_5 Vdout0_5ck108 = 1.8 time = 1090
.meas tran vdout0_5ck108 FIND v(dout0_5) AT=1090.05n

* CHECK dout0_6 Vdout0_6ck108 = 0 time = 1090
.meas tran vdout0_6ck108 FIND v(dout0_6) AT=1090.05n

* CHECK dout0_7 Vdout0_7ck108 = 1.8 time = 1090
.meas tran vdout0_7ck108 FIND v(dout0_7) AT=1090.05n

* CHECK dout1_0 Vdout1_0ck109 = 1.8 time = 1100
.meas tran vdout1_0ck109 FIND v(dout1_0) AT=1100.05n

* CHECK dout1_1 Vdout1_1ck109 = 1.8 time = 1100
.meas tran vdout1_1ck109 FIND v(dout1_1) AT=1100.05n

* CHECK dout1_2 Vdout1_2ck109 = 0 time = 1100
.meas tran vdout1_2ck109 FIND v(dout1_2) AT=1100.05n

* CHECK dout1_3 Vdout1_3ck109 = 1.8 time = 1100
.meas tran vdout1_3ck109 FIND v(dout1_3) AT=1100.05n

* CHECK dout1_4 Vdout1_4ck109 = 0 time = 1100
.meas tran vdout1_4ck109 FIND v(dout1_4) AT=1100.05n

* CHECK dout1_5 Vdout1_5ck109 = 0 time = 1100
.meas tran vdout1_5ck109 FIND v(dout1_5) AT=1100.05n

* CHECK dout1_6 Vdout1_6ck109 = 0 time = 1100
.meas tran vdout1_6ck109 FIND v(dout1_6) AT=1100.05n

* CHECK dout1_7 Vdout1_7ck109 = 0 time = 1100
.meas tran vdout1_7ck109 FIND v(dout1_7) AT=1100.05n

* CHECK dout0_0 Vdout0_0ck110 = 0 time = 1110
.meas tran vdout0_0ck110 FIND v(dout0_0) AT=1110.05n

* CHECK dout0_1 Vdout0_1ck110 = 0 time = 1110
.meas tran vdout0_1ck110 FIND v(dout0_1) AT=1110.05n

* CHECK dout0_2 Vdout0_2ck110 = 0 time = 1110
.meas tran vdout0_2ck110 FIND v(dout0_2) AT=1110.05n

* CHECK dout0_3 Vdout0_3ck110 = 1.8 time = 1110
.meas tran vdout0_3ck110 FIND v(dout0_3) AT=1110.05n

* CHECK dout0_4 Vdout0_4ck110 = 0 time = 1110
.meas tran vdout0_4ck110 FIND v(dout0_4) AT=1110.05n

* CHECK dout0_5 Vdout0_5ck110 = 0 time = 1110
.meas tran vdout0_5ck110 FIND v(dout0_5) AT=1110.05n

* CHECK dout0_6 Vdout0_6ck110 = 0 time = 1110
.meas tran vdout0_6ck110 FIND v(dout0_6) AT=1110.05n

* CHECK dout0_7 Vdout0_7ck110 = 1.8 time = 1110
.meas tran vdout0_7ck110 FIND v(dout0_7) AT=1110.05n

* CHECK dout1_0 Vdout1_0ck110 = 1.8 time = 1110
.meas tran vdout1_0ck110 FIND v(dout1_0) AT=1110.05n

* CHECK dout1_1 Vdout1_1ck110 = 1.8 time = 1110
.meas tran vdout1_1ck110 FIND v(dout1_1) AT=1110.05n

* CHECK dout1_2 Vdout1_2ck110 = 0 time = 1110
.meas tran vdout1_2ck110 FIND v(dout1_2) AT=1110.05n

* CHECK dout1_3 Vdout1_3ck110 = 1.8 time = 1110
.meas tran vdout1_3ck110 FIND v(dout1_3) AT=1110.05n

* CHECK dout1_4 Vdout1_4ck110 = 0 time = 1110
.meas tran vdout1_4ck110 FIND v(dout1_4) AT=1110.05n

* CHECK dout1_5 Vdout1_5ck110 = 0 time = 1110
.meas tran vdout1_5ck110 FIND v(dout1_5) AT=1110.05n

* CHECK dout1_6 Vdout1_6ck110 = 0 time = 1110
.meas tran vdout1_6ck110 FIND v(dout1_6) AT=1110.05n

* CHECK dout1_7 Vdout1_7ck110 = 0 time = 1110
.meas tran vdout1_7ck110 FIND v(dout1_7) AT=1110.05n

* CHECK dout1_0 Vdout1_0ck111 = 0 time = 1120
.meas tran vdout1_0ck111 FIND v(dout1_0) AT=1120.05n

* CHECK dout1_1 Vdout1_1ck111 = 1.8 time = 1120
.meas tran vdout1_1ck111 FIND v(dout1_1) AT=1120.05n

* CHECK dout1_2 Vdout1_2ck111 = 0 time = 1120
.meas tran vdout1_2ck111 FIND v(dout1_2) AT=1120.05n

* CHECK dout1_3 Vdout1_3ck111 = 0 time = 1120
.meas tran vdout1_3ck111 FIND v(dout1_3) AT=1120.05n

* CHECK dout1_4 Vdout1_4ck111 = 1.8 time = 1120
.meas tran vdout1_4ck111 FIND v(dout1_4) AT=1120.05n

* CHECK dout1_5 Vdout1_5ck111 = 0 time = 1120
.meas tran vdout1_5ck111 FIND v(dout1_5) AT=1120.05n

* CHECK dout1_6 Vdout1_6ck111 = 1.8 time = 1120
.meas tran vdout1_6ck111 FIND v(dout1_6) AT=1120.05n

* CHECK dout1_7 Vdout1_7ck111 = 1.8 time = 1120
.meas tran vdout1_7ck111 FIND v(dout1_7) AT=1120.05n

* CHECK dout1_0 Vdout1_0ck112 = 1.8 time = 1130
.meas tran vdout1_0ck112 FIND v(dout1_0) AT=1130.05n

* CHECK dout1_1 Vdout1_1ck112 = 1.8 time = 1130
.meas tran vdout1_1ck112 FIND v(dout1_1) AT=1130.05n

* CHECK dout1_2 Vdout1_2ck112 = 0 time = 1130
.meas tran vdout1_2ck112 FIND v(dout1_2) AT=1130.05n

* CHECK dout1_3 Vdout1_3ck112 = 1.8 time = 1130
.meas tran vdout1_3ck112 FIND v(dout1_3) AT=1130.05n

* CHECK dout1_4 Vdout1_4ck112 = 0 time = 1130
.meas tran vdout1_4ck112 FIND v(dout1_4) AT=1130.05n

* CHECK dout1_5 Vdout1_5ck112 = 0 time = 1130
.meas tran vdout1_5ck112 FIND v(dout1_5) AT=1130.05n

* CHECK dout1_6 Vdout1_6ck112 = 0 time = 1130
.meas tran vdout1_6ck112 FIND v(dout1_6) AT=1130.05n

* CHECK dout1_7 Vdout1_7ck112 = 0 time = 1130
.meas tran vdout1_7ck112 FIND v(dout1_7) AT=1130.05n

* CHECK dout0_0 Vdout0_0ck114 = 1.8 time = 1150
.meas tran vdout0_0ck114 FIND v(dout0_0) AT=1150.05n

* CHECK dout0_1 Vdout0_1ck114 = 1.8 time = 1150
.meas tran vdout0_1ck114 FIND v(dout0_1) AT=1150.05n

* CHECK dout0_2 Vdout0_2ck114 = 0 time = 1150
.meas tran vdout0_2ck114 FIND v(dout0_2) AT=1150.05n

* CHECK dout0_3 Vdout0_3ck114 = 1.8 time = 1150
.meas tran vdout0_3ck114 FIND v(dout0_3) AT=1150.05n

* CHECK dout0_4 Vdout0_4ck114 = 0 time = 1150
.meas tran vdout0_4ck114 FIND v(dout0_4) AT=1150.05n

* CHECK dout0_5 Vdout0_5ck114 = 0 time = 1150
.meas tran vdout0_5ck114 FIND v(dout0_5) AT=1150.05n

* CHECK dout0_6 Vdout0_6ck114 = 0 time = 1150
.meas tran vdout0_6ck114 FIND v(dout0_6) AT=1150.05n

* CHECK dout0_7 Vdout0_7ck114 = 0 time = 1150
.meas tran vdout0_7ck114 FIND v(dout0_7) AT=1150.05n

* CHECK dout0_0 Vdout0_0ck115 = 1.8 time = 1160
.meas tran vdout0_0ck115 FIND v(dout0_0) AT=1160.05n

* CHECK dout0_1 Vdout0_1ck115 = 0 time = 1160
.meas tran vdout0_1ck115 FIND v(dout0_1) AT=1160.05n

* CHECK dout0_2 Vdout0_2ck115 = 1.8 time = 1160
.meas tran vdout0_2ck115 FIND v(dout0_2) AT=1160.05n

* CHECK dout0_3 Vdout0_3ck115 = 1.8 time = 1160
.meas tran vdout0_3ck115 FIND v(dout0_3) AT=1160.05n

* CHECK dout0_4 Vdout0_4ck115 = 1.8 time = 1160
.meas tran vdout0_4ck115 FIND v(dout0_4) AT=1160.05n

* CHECK dout0_5 Vdout0_5ck115 = 0 time = 1160
.meas tran vdout0_5ck115 FIND v(dout0_5) AT=1160.05n

* CHECK dout0_6 Vdout0_6ck115 = 1.8 time = 1160
.meas tran vdout0_6ck115 FIND v(dout0_6) AT=1160.05n

* CHECK dout0_7 Vdout0_7ck115 = 1.8 time = 1160
.meas tran vdout0_7ck115 FIND v(dout0_7) AT=1160.05n

* CHECK dout1_0 Vdout1_0ck115 = 1.8 time = 1160
.meas tran vdout1_0ck115 FIND v(dout1_0) AT=1160.05n

* CHECK dout1_1 Vdout1_1ck115 = 0 time = 1160
.meas tran vdout1_1ck115 FIND v(dout1_1) AT=1160.05n

* CHECK dout1_2 Vdout1_2ck115 = 1.8 time = 1160
.meas tran vdout1_2ck115 FIND v(dout1_2) AT=1160.05n

* CHECK dout1_3 Vdout1_3ck115 = 1.8 time = 1160
.meas tran vdout1_3ck115 FIND v(dout1_3) AT=1160.05n

* CHECK dout1_4 Vdout1_4ck115 = 1.8 time = 1160
.meas tran vdout1_4ck115 FIND v(dout1_4) AT=1160.05n

* CHECK dout1_5 Vdout1_5ck115 = 0 time = 1160
.meas tran vdout1_5ck115 FIND v(dout1_5) AT=1160.05n

* CHECK dout1_6 Vdout1_6ck115 = 1.8 time = 1160
.meas tran vdout1_6ck115 FIND v(dout1_6) AT=1160.05n

* CHECK dout1_7 Vdout1_7ck115 = 1.8 time = 1160
.meas tran vdout1_7ck115 FIND v(dout1_7) AT=1160.05n

* CHECK dout1_0 Vdout1_0ck116 = 1.8 time = 1170
.meas tran vdout1_0ck116 FIND v(dout1_0) AT=1170.05n

* CHECK dout1_1 Vdout1_1ck116 = 1.8 time = 1170
.meas tran vdout1_1ck116 FIND v(dout1_1) AT=1170.05n

* CHECK dout1_2 Vdout1_2ck116 = 0 time = 1170
.meas tran vdout1_2ck116 FIND v(dout1_2) AT=1170.05n

* CHECK dout1_3 Vdout1_3ck116 = 1.8 time = 1170
.meas tran vdout1_3ck116 FIND v(dout1_3) AT=1170.05n

* CHECK dout1_4 Vdout1_4ck116 = 0 time = 1170
.meas tran vdout1_4ck116 FIND v(dout1_4) AT=1170.05n

* CHECK dout1_5 Vdout1_5ck116 = 0 time = 1170
.meas tran vdout1_5ck116 FIND v(dout1_5) AT=1170.05n

* CHECK dout1_6 Vdout1_6ck116 = 0 time = 1170
.meas tran vdout1_6ck116 FIND v(dout1_6) AT=1170.05n

* CHECK dout1_7 Vdout1_7ck116 = 0 time = 1170
.meas tran vdout1_7ck116 FIND v(dout1_7) AT=1170.05n

* CHECK dout0_0 Vdout0_0ck117 = 0 time = 1180
.meas tran vdout0_0ck117 FIND v(dout0_0) AT=1180.05n

* CHECK dout0_1 Vdout0_1ck117 = 1.8 time = 1180
.meas tran vdout0_1ck117 FIND v(dout0_1) AT=1180.05n

* CHECK dout0_2 Vdout0_2ck117 = 1.8 time = 1180
.meas tran vdout0_2ck117 FIND v(dout0_2) AT=1180.05n

* CHECK dout0_3 Vdout0_3ck117 = 0 time = 1180
.meas tran vdout0_3ck117 FIND v(dout0_3) AT=1180.05n

* CHECK dout0_4 Vdout0_4ck117 = 0 time = 1180
.meas tran vdout0_4ck117 FIND v(dout0_4) AT=1180.05n

* CHECK dout0_5 Vdout0_5ck117 = 0 time = 1180
.meas tran vdout0_5ck117 FIND v(dout0_5) AT=1180.05n

* CHECK dout0_6 Vdout0_6ck117 = 0 time = 1180
.meas tran vdout0_6ck117 FIND v(dout0_6) AT=1180.05n

* CHECK dout0_7 Vdout0_7ck117 = 1.8 time = 1180
.meas tran vdout0_7ck117 FIND v(dout0_7) AT=1180.05n

* CHECK dout1_0 Vdout1_0ck117 = 0 time = 1180
.meas tran vdout1_0ck117 FIND v(dout1_0) AT=1180.05n

* CHECK dout1_1 Vdout1_1ck117 = 0 time = 1180
.meas tran vdout1_1ck117 FIND v(dout1_1) AT=1180.05n

* CHECK dout1_2 Vdout1_2ck117 = 0 time = 1180
.meas tran vdout1_2ck117 FIND v(dout1_2) AT=1180.05n

* CHECK dout1_3 Vdout1_3ck117 = 1.8 time = 1180
.meas tran vdout1_3ck117 FIND v(dout1_3) AT=1180.05n

* CHECK dout1_4 Vdout1_4ck117 = 0 time = 1180
.meas tran vdout1_4ck117 FIND v(dout1_4) AT=1180.05n

* CHECK dout1_5 Vdout1_5ck117 = 0 time = 1180
.meas tran vdout1_5ck117 FIND v(dout1_5) AT=1180.05n

* CHECK dout1_6 Vdout1_6ck117 = 0 time = 1180
.meas tran vdout1_6ck117 FIND v(dout1_6) AT=1180.05n

* CHECK dout1_7 Vdout1_7ck117 = 1.8 time = 1180
.meas tran vdout1_7ck117 FIND v(dout1_7) AT=1180.05n

* CHECK dout0_0 Vdout0_0ck119 = 1.8 time = 1200
.meas tran vdout0_0ck119 FIND v(dout0_0) AT=1200.05n

* CHECK dout0_1 Vdout0_1ck119 = 0 time = 1200
.meas tran vdout0_1ck119 FIND v(dout0_1) AT=1200.05n

* CHECK dout0_2 Vdout0_2ck119 = 1.8 time = 1200
.meas tran vdout0_2ck119 FIND v(dout0_2) AT=1200.05n

* CHECK dout0_3 Vdout0_3ck119 = 1.8 time = 1200
.meas tran vdout0_3ck119 FIND v(dout0_3) AT=1200.05n

* CHECK dout0_4 Vdout0_4ck119 = 1.8 time = 1200
.meas tran vdout0_4ck119 FIND v(dout0_4) AT=1200.05n

* CHECK dout0_5 Vdout0_5ck119 = 0 time = 1200
.meas tran vdout0_5ck119 FIND v(dout0_5) AT=1200.05n

* CHECK dout0_6 Vdout0_6ck119 = 1.8 time = 1200
.meas tran vdout0_6ck119 FIND v(dout0_6) AT=1200.05n

* CHECK dout0_7 Vdout0_7ck119 = 1.8 time = 1200
.meas tran vdout0_7ck119 FIND v(dout0_7) AT=1200.05n

* CHECK dout1_0 Vdout1_0ck120 = 0 time = 1210
.meas tran vdout1_0ck120 FIND v(dout1_0) AT=1210.05n

* CHECK dout1_1 Vdout1_1ck120 = 1.8 time = 1210
.meas tran vdout1_1ck120 FIND v(dout1_1) AT=1210.05n

* CHECK dout1_2 Vdout1_2ck120 = 1.8 time = 1210
.meas tran vdout1_2ck120 FIND v(dout1_2) AT=1210.05n

* CHECK dout1_3 Vdout1_3ck120 = 0 time = 1210
.meas tran vdout1_3ck120 FIND v(dout1_3) AT=1210.05n

* CHECK dout1_4 Vdout1_4ck120 = 0 time = 1210
.meas tran vdout1_4ck120 FIND v(dout1_4) AT=1210.05n

* CHECK dout1_5 Vdout1_5ck120 = 0 time = 1210
.meas tran vdout1_5ck120 FIND v(dout1_5) AT=1210.05n

* CHECK dout1_6 Vdout1_6ck120 = 0 time = 1210
.meas tran vdout1_6ck120 FIND v(dout1_6) AT=1210.05n

* CHECK dout1_7 Vdout1_7ck120 = 1.8 time = 1210
.meas tran vdout1_7ck120 FIND v(dout1_7) AT=1210.05n

* CHECK dout1_0 Vdout1_0ck122 = 0 time = 1230
.meas tran vdout1_0ck122 FIND v(dout1_0) AT=1230.05n

* CHECK dout1_1 Vdout1_1ck122 = 0 time = 1230
.meas tran vdout1_1ck122 FIND v(dout1_1) AT=1230.05n

* CHECK dout1_2 Vdout1_2ck122 = 0 time = 1230
.meas tran vdout1_2ck122 FIND v(dout1_2) AT=1230.05n

* CHECK dout1_3 Vdout1_3ck122 = 0 time = 1230
.meas tran vdout1_3ck122 FIND v(dout1_3) AT=1230.05n

* CHECK dout1_4 Vdout1_4ck122 = 0 time = 1230
.meas tran vdout1_4ck122 FIND v(dout1_4) AT=1230.05n

* CHECK dout1_5 Vdout1_5ck122 = 1.8 time = 1230
.meas tran vdout1_5ck122 FIND v(dout1_5) AT=1230.05n

* CHECK dout1_6 Vdout1_6ck122 = 1.8 time = 1230
.meas tran vdout1_6ck122 FIND v(dout1_6) AT=1230.05n

* CHECK dout1_7 Vdout1_7ck122 = 1.8 time = 1230
.meas tran vdout1_7ck122 FIND v(dout1_7) AT=1230.05n

* CHECK dout0_0 Vdout0_0ck123 = 0 time = 1240
.meas tran vdout0_0ck123 FIND v(dout0_0) AT=1240.05n

* CHECK dout0_1 Vdout0_1ck123 = 1.8 time = 1240
.meas tran vdout0_1ck123 FIND v(dout0_1) AT=1240.05n

* CHECK dout0_2 Vdout0_2ck123 = 1.8 time = 1240
.meas tran vdout0_2ck123 FIND v(dout0_2) AT=1240.05n

* CHECK dout0_3 Vdout0_3ck123 = 0 time = 1240
.meas tran vdout0_3ck123 FIND v(dout0_3) AT=1240.05n

* CHECK dout0_4 Vdout0_4ck123 = 0 time = 1240
.meas tran vdout0_4ck123 FIND v(dout0_4) AT=1240.05n

* CHECK dout0_5 Vdout0_5ck123 = 0 time = 1240
.meas tran vdout0_5ck123 FIND v(dout0_5) AT=1240.05n

* CHECK dout0_6 Vdout0_6ck123 = 0 time = 1240
.meas tran vdout0_6ck123 FIND v(dout0_6) AT=1240.05n

* CHECK dout0_7 Vdout0_7ck123 = 1.8 time = 1240
.meas tran vdout0_7ck123 FIND v(dout0_7) AT=1240.05n

* CHECK dout1_0 Vdout1_0ck123 = 1.8 time = 1240
.meas tran vdout1_0ck123 FIND v(dout1_0) AT=1240.05n

* CHECK dout1_1 Vdout1_1ck123 = 1.8 time = 1240
.meas tran vdout1_1ck123 FIND v(dout1_1) AT=1240.05n

* CHECK dout1_2 Vdout1_2ck123 = 0 time = 1240
.meas tran vdout1_2ck123 FIND v(dout1_2) AT=1240.05n

* CHECK dout1_3 Vdout1_3ck123 = 1.8 time = 1240
.meas tran vdout1_3ck123 FIND v(dout1_3) AT=1240.05n

* CHECK dout1_4 Vdout1_4ck123 = 0 time = 1240
.meas tran vdout1_4ck123 FIND v(dout1_4) AT=1240.05n

* CHECK dout1_5 Vdout1_5ck123 = 0 time = 1240
.meas tran vdout1_5ck123 FIND v(dout1_5) AT=1240.05n

* CHECK dout1_6 Vdout1_6ck123 = 0 time = 1240
.meas tran vdout1_6ck123 FIND v(dout1_6) AT=1240.05n

* CHECK dout1_7 Vdout1_7ck123 = 0 time = 1240
.meas tran vdout1_7ck123 FIND v(dout1_7) AT=1240.05n

* CHECK dout0_0 Vdout0_0ck124 = 0 time = 1250
.meas tran vdout0_0ck124 FIND v(dout0_0) AT=1250.05n

* CHECK dout0_1 Vdout0_1ck124 = 0 time = 1250
.meas tran vdout0_1ck124 FIND v(dout0_1) AT=1250.05n

* CHECK dout0_2 Vdout0_2ck124 = 1.8 time = 1250
.meas tran vdout0_2ck124 FIND v(dout0_2) AT=1250.05n

* CHECK dout0_3 Vdout0_3ck124 = 0 time = 1250
.meas tran vdout0_3ck124 FIND v(dout0_3) AT=1250.05n

* CHECK dout0_4 Vdout0_4ck124 = 1.8 time = 1250
.meas tran vdout0_4ck124 FIND v(dout0_4) AT=1250.05n

* CHECK dout0_5 Vdout0_5ck124 = 1.8 time = 1250
.meas tran vdout0_5ck124 FIND v(dout0_5) AT=1250.05n

* CHECK dout0_6 Vdout0_6ck124 = 0 time = 1250
.meas tran vdout0_6ck124 FIND v(dout0_6) AT=1250.05n

* CHECK dout0_7 Vdout0_7ck124 = 0 time = 1250
.meas tran vdout0_7ck124 FIND v(dout0_7) AT=1250.05n

* CHECK dout1_0 Vdout1_0ck126 = 1.8 time = 1270
.meas tran vdout1_0ck126 FIND v(dout1_0) AT=1270.05n

* CHECK dout1_1 Vdout1_1ck126 = 1.8 time = 1270
.meas tran vdout1_1ck126 FIND v(dout1_1) AT=1270.05n

* CHECK dout1_2 Vdout1_2ck126 = 0 time = 1270
.meas tran vdout1_2ck126 FIND v(dout1_2) AT=1270.05n

* CHECK dout1_3 Vdout1_3ck126 = 1.8 time = 1270
.meas tran vdout1_3ck126 FIND v(dout1_3) AT=1270.05n

* CHECK dout1_4 Vdout1_4ck126 = 0 time = 1270
.meas tran vdout1_4ck126 FIND v(dout1_4) AT=1270.05n

* CHECK dout1_5 Vdout1_5ck126 = 0 time = 1270
.meas tran vdout1_5ck126 FIND v(dout1_5) AT=1270.05n

* CHECK dout1_6 Vdout1_6ck126 = 0 time = 1270
.meas tran vdout1_6ck126 FIND v(dout1_6) AT=1270.05n

* CHECK dout1_7 Vdout1_7ck126 = 0 time = 1270
.meas tran vdout1_7ck126 FIND v(dout1_7) AT=1270.05n

* CHECK dout0_0 Vdout0_0ck127 = 0 time = 1280
.meas tran vdout0_0ck127 FIND v(dout0_0) AT=1280.05n

* CHECK dout0_1 Vdout0_1ck127 = 1.8 time = 1280
.meas tran vdout0_1ck127 FIND v(dout0_1) AT=1280.05n

* CHECK dout0_2 Vdout0_2ck127 = 1.8 time = 1280
.meas tran vdout0_2ck127 FIND v(dout0_2) AT=1280.05n

* CHECK dout0_3 Vdout0_3ck127 = 0 time = 1280
.meas tran vdout0_3ck127 FIND v(dout0_3) AT=1280.05n

* CHECK dout0_4 Vdout0_4ck127 = 0 time = 1280
.meas tran vdout0_4ck127 FIND v(dout0_4) AT=1280.05n

* CHECK dout0_5 Vdout0_5ck127 = 0 time = 1280
.meas tran vdout0_5ck127 FIND v(dout0_5) AT=1280.05n

* CHECK dout0_6 Vdout0_6ck127 = 0 time = 1280
.meas tran vdout0_6ck127 FIND v(dout0_6) AT=1280.05n

* CHECK dout0_7 Vdout0_7ck127 = 1.8 time = 1280
.meas tran vdout0_7ck127 FIND v(dout0_7) AT=1280.05n

* CHECK dout1_0 Vdout1_0ck127 = 0 time = 1280
.meas tran vdout1_0ck127 FIND v(dout1_0) AT=1280.05n

* CHECK dout1_1 Vdout1_1ck127 = 1.8 time = 1280
.meas tran vdout1_1ck127 FIND v(dout1_1) AT=1280.05n

* CHECK dout1_2 Vdout1_2ck127 = 1.8 time = 1280
.meas tran vdout1_2ck127 FIND v(dout1_2) AT=1280.05n

* CHECK dout1_3 Vdout1_3ck127 = 0 time = 1280
.meas tran vdout1_3ck127 FIND v(dout1_3) AT=1280.05n

* CHECK dout1_4 Vdout1_4ck127 = 0 time = 1280
.meas tran vdout1_4ck127 FIND v(dout1_4) AT=1280.05n

* CHECK dout1_5 Vdout1_5ck127 = 0 time = 1280
.meas tran vdout1_5ck127 FIND v(dout1_5) AT=1280.05n

* CHECK dout1_6 Vdout1_6ck127 = 0 time = 1280
.meas tran vdout1_6ck127 FIND v(dout1_6) AT=1280.05n

* CHECK dout1_7 Vdout1_7ck127 = 1.8 time = 1280
.meas tran vdout1_7ck127 FIND v(dout1_7) AT=1280.05n

* CHECK dout0_0 Vdout0_0ck128 = 0 time = 1290
.meas tran vdout0_0ck128 FIND v(dout0_0) AT=1290.05n

* CHECK dout0_1 Vdout0_1ck128 = 0 time = 1290
.meas tran vdout0_1ck128 FIND v(dout0_1) AT=1290.05n

* CHECK dout0_2 Vdout0_2ck128 = 1.8 time = 1290
.meas tran vdout0_2ck128 FIND v(dout0_2) AT=1290.05n

* CHECK dout0_3 Vdout0_3ck128 = 1.8 time = 1290
.meas tran vdout0_3ck128 FIND v(dout0_3) AT=1290.05n

* CHECK dout0_4 Vdout0_4ck128 = 0 time = 1290
.meas tran vdout0_4ck128 FIND v(dout0_4) AT=1290.05n

* CHECK dout0_5 Vdout0_5ck128 = 1.8 time = 1290
.meas tran vdout0_5ck128 FIND v(dout0_5) AT=1290.05n

* CHECK dout0_6 Vdout0_6ck128 = 1.8 time = 1290
.meas tran vdout0_6ck128 FIND v(dout0_6) AT=1290.05n

* CHECK dout0_7 Vdout0_7ck128 = 1.8 time = 1290
.meas tran vdout0_7ck128 FIND v(dout0_7) AT=1290.05n

* CHECK dout1_0 Vdout1_0ck128 = 0 time = 1290
.meas tran vdout1_0ck128 FIND v(dout1_0) AT=1290.05n

* CHECK dout1_1 Vdout1_1ck128 = 0 time = 1290
.meas tran vdout1_1ck128 FIND v(dout1_1) AT=1290.05n

* CHECK dout1_2 Vdout1_2ck128 = 1.8 time = 1290
.meas tran vdout1_2ck128 FIND v(dout1_2) AT=1290.05n

* CHECK dout1_3 Vdout1_3ck128 = 1.8 time = 1290
.meas tran vdout1_3ck128 FIND v(dout1_3) AT=1290.05n

* CHECK dout1_4 Vdout1_4ck128 = 0 time = 1290
.meas tran vdout1_4ck128 FIND v(dout1_4) AT=1290.05n

* CHECK dout1_5 Vdout1_5ck128 = 1.8 time = 1290
.meas tran vdout1_5ck128 FIND v(dout1_5) AT=1290.05n

* CHECK dout1_6 Vdout1_6ck128 = 1.8 time = 1290
.meas tran vdout1_6ck128 FIND v(dout1_6) AT=1290.05n

* CHECK dout1_7 Vdout1_7ck128 = 1.8 time = 1290
.meas tran vdout1_7ck128 FIND v(dout1_7) AT=1290.05n

* CHECK dout1_0 Vdout1_0ck129 = 1.8 time = 1300
.meas tran vdout1_0ck129 FIND v(dout1_0) AT=1300.05n

* CHECK dout1_1 Vdout1_1ck129 = 1.8 time = 1300
.meas tran vdout1_1ck129 FIND v(dout1_1) AT=1300.05n

* CHECK dout1_2 Vdout1_2ck129 = 0 time = 1300
.meas tran vdout1_2ck129 FIND v(dout1_2) AT=1300.05n

* CHECK dout1_3 Vdout1_3ck129 = 1.8 time = 1300
.meas tran vdout1_3ck129 FIND v(dout1_3) AT=1300.05n

* CHECK dout1_4 Vdout1_4ck129 = 0 time = 1300
.meas tran vdout1_4ck129 FIND v(dout1_4) AT=1300.05n

* CHECK dout1_5 Vdout1_5ck129 = 0 time = 1300
.meas tran vdout1_5ck129 FIND v(dout1_5) AT=1300.05n

* CHECK dout1_6 Vdout1_6ck129 = 0 time = 1300
.meas tran vdout1_6ck129 FIND v(dout1_6) AT=1300.05n

* CHECK dout1_7 Vdout1_7ck129 = 0 time = 1300
.meas tran vdout1_7ck129 FIND v(dout1_7) AT=1300.05n

* CHECK dout1_0 Vdout1_0ck130 = 0 time = 1310
.meas tran vdout1_0ck130 FIND v(dout1_0) AT=1310.05n

* CHECK dout1_1 Vdout1_1ck130 = 0 time = 1310
.meas tran vdout1_1ck130 FIND v(dout1_1) AT=1310.05n

* CHECK dout1_2 Vdout1_2ck130 = 1.8 time = 1310
.meas tran vdout1_2ck130 FIND v(dout1_2) AT=1310.05n

* CHECK dout1_3 Vdout1_3ck130 = 1.8 time = 1310
.meas tran vdout1_3ck130 FIND v(dout1_3) AT=1310.05n

* CHECK dout1_4 Vdout1_4ck130 = 0 time = 1310
.meas tran vdout1_4ck130 FIND v(dout1_4) AT=1310.05n

* CHECK dout1_5 Vdout1_5ck130 = 1.8 time = 1310
.meas tran vdout1_5ck130 FIND v(dout1_5) AT=1310.05n

* CHECK dout1_6 Vdout1_6ck130 = 1.8 time = 1310
.meas tran vdout1_6ck130 FIND v(dout1_6) AT=1310.05n

* CHECK dout1_7 Vdout1_7ck130 = 1.8 time = 1310
.meas tran vdout1_7ck130 FIND v(dout1_7) AT=1310.05n

* CHECK dout0_0 Vdout0_0ck131 = 0 time = 1320
.meas tran vdout0_0ck131 FIND v(dout0_0) AT=1320.05n

* CHECK dout0_1 Vdout0_1ck131 = 0 time = 1320
.meas tran vdout0_1ck131 FIND v(dout0_1) AT=1320.05n

* CHECK dout0_2 Vdout0_2ck131 = 1.8 time = 1320
.meas tran vdout0_2ck131 FIND v(dout0_2) AT=1320.05n

* CHECK dout0_3 Vdout0_3ck131 = 1.8 time = 1320
.meas tran vdout0_3ck131 FIND v(dout0_3) AT=1320.05n

* CHECK dout0_4 Vdout0_4ck131 = 0 time = 1320
.meas tran vdout0_4ck131 FIND v(dout0_4) AT=1320.05n

* CHECK dout0_5 Vdout0_5ck131 = 1.8 time = 1320
.meas tran vdout0_5ck131 FIND v(dout0_5) AT=1320.05n

* CHECK dout0_6 Vdout0_6ck131 = 1.8 time = 1320
.meas tran vdout0_6ck131 FIND v(dout0_6) AT=1320.05n

* CHECK dout0_7 Vdout0_7ck131 = 1.8 time = 1320
.meas tran vdout0_7ck131 FIND v(dout0_7) AT=1320.05n

* CHECK dout0_0 Vdout0_0ck133 = 0 time = 1340
.meas tran vdout0_0ck133 FIND v(dout0_0) AT=1340.05n

* CHECK dout0_1 Vdout0_1ck133 = 0 time = 1340
.meas tran vdout0_1ck133 FIND v(dout0_1) AT=1340.05n

* CHECK dout0_2 Vdout0_2ck133 = 1.8 time = 1340
.meas tran vdout0_2ck133 FIND v(dout0_2) AT=1340.05n

* CHECK dout0_3 Vdout0_3ck133 = 1.8 time = 1340
.meas tran vdout0_3ck133 FIND v(dout0_3) AT=1340.05n

* CHECK dout0_4 Vdout0_4ck133 = 0 time = 1340
.meas tran vdout0_4ck133 FIND v(dout0_4) AT=1340.05n

* CHECK dout0_5 Vdout0_5ck133 = 1.8 time = 1340
.meas tran vdout0_5ck133 FIND v(dout0_5) AT=1340.05n

* CHECK dout0_6 Vdout0_6ck133 = 1.8 time = 1340
.meas tran vdout0_6ck133 FIND v(dout0_6) AT=1340.05n

* CHECK dout0_7 Vdout0_7ck133 = 1.8 time = 1340
.meas tran vdout0_7ck133 FIND v(dout0_7) AT=1340.05n

* CHECK dout0_0 Vdout0_0ck135 = 0 time = 1360
.meas tran vdout0_0ck135 FIND v(dout0_0) AT=1360.05n

* CHECK dout0_1 Vdout0_1ck135 = 1.8 time = 1360
.meas tran vdout0_1ck135 FIND v(dout0_1) AT=1360.05n

* CHECK dout0_2 Vdout0_2ck135 = 1.8 time = 1360
.meas tran vdout0_2ck135 FIND v(dout0_2) AT=1360.05n

* CHECK dout0_3 Vdout0_3ck135 = 0 time = 1360
.meas tran vdout0_3ck135 FIND v(dout0_3) AT=1360.05n

* CHECK dout0_4 Vdout0_4ck135 = 0 time = 1360
.meas tran vdout0_4ck135 FIND v(dout0_4) AT=1360.05n

* CHECK dout0_5 Vdout0_5ck135 = 0 time = 1360
.meas tran vdout0_5ck135 FIND v(dout0_5) AT=1360.05n

* CHECK dout0_6 Vdout0_6ck135 = 0 time = 1360
.meas tran vdout0_6ck135 FIND v(dout0_6) AT=1360.05n

* CHECK dout0_7 Vdout0_7ck135 = 1.8 time = 1360
.meas tran vdout0_7ck135 FIND v(dout0_7) AT=1360.05n

* CHECK dout1_0 Vdout1_0ck135 = 0 time = 1360
.meas tran vdout1_0ck135 FIND v(dout1_0) AT=1360.05n

* CHECK dout1_1 Vdout1_1ck135 = 1.8 time = 1360
.meas tran vdout1_1ck135 FIND v(dout1_1) AT=1360.05n

* CHECK dout1_2 Vdout1_2ck135 = 0 time = 1360
.meas tran vdout1_2ck135 FIND v(dout1_2) AT=1360.05n

* CHECK dout1_3 Vdout1_3ck135 = 1.8 time = 1360
.meas tran vdout1_3ck135 FIND v(dout1_3) AT=1360.05n

* CHECK dout1_4 Vdout1_4ck135 = 0 time = 1360
.meas tran vdout1_4ck135 FIND v(dout1_4) AT=1360.05n

* CHECK dout1_5 Vdout1_5ck135 = 1.8 time = 1360
.meas tran vdout1_5ck135 FIND v(dout1_5) AT=1360.05n

* CHECK dout1_6 Vdout1_6ck135 = 0 time = 1360
.meas tran vdout1_6ck135 FIND v(dout1_6) AT=1360.05n

* CHECK dout1_7 Vdout1_7ck135 = 1.8 time = 1360
.meas tran vdout1_7ck135 FIND v(dout1_7) AT=1360.05n

* CHECK dout0_0 Vdout0_0ck137 = 1.8 time = 1380
.meas tran vdout0_0ck137 FIND v(dout0_0) AT=1380.05n

* CHECK dout0_1 Vdout0_1ck137 = 1.8 time = 1380
.meas tran vdout0_1ck137 FIND v(dout0_1) AT=1380.05n

* CHECK dout0_2 Vdout0_2ck137 = 1.8 time = 1380
.meas tran vdout0_2ck137 FIND v(dout0_2) AT=1380.05n

* CHECK dout0_3 Vdout0_3ck137 = 1.8 time = 1380
.meas tran vdout0_3ck137 FIND v(dout0_3) AT=1380.05n

* CHECK dout0_4 Vdout0_4ck137 = 0 time = 1380
.meas tran vdout0_4ck137 FIND v(dout0_4) AT=1380.05n

* CHECK dout0_5 Vdout0_5ck137 = 1.8 time = 1380
.meas tran vdout0_5ck137 FIND v(dout0_5) AT=1380.05n

* CHECK dout0_6 Vdout0_6ck137 = 0 time = 1380
.meas tran vdout0_6ck137 FIND v(dout0_6) AT=1380.05n

* CHECK dout0_7 Vdout0_7ck137 = 0 time = 1380
.meas tran vdout0_7ck137 FIND v(dout0_7) AT=1380.05n

* CHECK dout0_0 Vdout0_0ck138 = 0 time = 1390
.meas tran vdout0_0ck138 FIND v(dout0_0) AT=1390.05n

* CHECK dout0_1 Vdout0_1ck138 = 1.8 time = 1390
.meas tran vdout0_1ck138 FIND v(dout0_1) AT=1390.05n

* CHECK dout0_2 Vdout0_2ck138 = 0 time = 1390
.meas tran vdout0_2ck138 FIND v(dout0_2) AT=1390.05n

* CHECK dout0_3 Vdout0_3ck138 = 1.8 time = 1390
.meas tran vdout0_3ck138 FIND v(dout0_3) AT=1390.05n

* CHECK dout0_4 Vdout0_4ck138 = 0 time = 1390
.meas tran vdout0_4ck138 FIND v(dout0_4) AT=1390.05n

* CHECK dout0_5 Vdout0_5ck138 = 1.8 time = 1390
.meas tran vdout0_5ck138 FIND v(dout0_5) AT=1390.05n

* CHECK dout0_6 Vdout0_6ck138 = 0 time = 1390
.meas tran vdout0_6ck138 FIND v(dout0_6) AT=1390.05n

* CHECK dout0_7 Vdout0_7ck138 = 1.8 time = 1390
.meas tran vdout0_7ck138 FIND v(dout0_7) AT=1390.05n

* CHECK dout1_0 Vdout1_0ck139 = 1.8 time = 1400
.meas tran vdout1_0ck139 FIND v(dout1_0) AT=1400.05n

* CHECK dout1_1 Vdout1_1ck139 = 1.8 time = 1400
.meas tran vdout1_1ck139 FIND v(dout1_1) AT=1400.05n

* CHECK dout1_2 Vdout1_2ck139 = 0 time = 1400
.meas tran vdout1_2ck139 FIND v(dout1_2) AT=1400.05n

* CHECK dout1_3 Vdout1_3ck139 = 1.8 time = 1400
.meas tran vdout1_3ck139 FIND v(dout1_3) AT=1400.05n

* CHECK dout1_4 Vdout1_4ck139 = 0 time = 1400
.meas tran vdout1_4ck139 FIND v(dout1_4) AT=1400.05n

* CHECK dout1_5 Vdout1_5ck139 = 1.8 time = 1400
.meas tran vdout1_5ck139 FIND v(dout1_5) AT=1400.05n

* CHECK dout1_6 Vdout1_6ck139 = 0 time = 1400
.meas tran vdout1_6ck139 FIND v(dout1_6) AT=1400.05n

* CHECK dout1_7 Vdout1_7ck139 = 0 time = 1400
.meas tran vdout1_7ck139 FIND v(dout1_7) AT=1400.05n

* CHECK dout1_0 Vdout1_0ck140 = 0 time = 1410
.meas tran vdout1_0ck140 FIND v(dout1_0) AT=1410.05n

* CHECK dout1_1 Vdout1_1ck140 = 1.8 time = 1410
.meas tran vdout1_1ck140 FIND v(dout1_1) AT=1410.05n

* CHECK dout1_2 Vdout1_2ck140 = 0 time = 1410
.meas tran vdout1_2ck140 FIND v(dout1_2) AT=1410.05n

* CHECK dout1_3 Vdout1_3ck140 = 1.8 time = 1410
.meas tran vdout1_3ck140 FIND v(dout1_3) AT=1410.05n

* CHECK dout1_4 Vdout1_4ck140 = 0 time = 1410
.meas tran vdout1_4ck140 FIND v(dout1_4) AT=1410.05n

* CHECK dout1_5 Vdout1_5ck140 = 1.8 time = 1410
.meas tran vdout1_5ck140 FIND v(dout1_5) AT=1410.05n

* CHECK dout1_6 Vdout1_6ck140 = 0 time = 1410
.meas tran vdout1_6ck140 FIND v(dout1_6) AT=1410.05n

* CHECK dout1_7 Vdout1_7ck140 = 1.8 time = 1410
.meas tran vdout1_7ck140 FIND v(dout1_7) AT=1410.05n

* CHECK dout1_0 Vdout1_0ck141 = 1.8 time = 1420
.meas tran vdout1_0ck141 FIND v(dout1_0) AT=1420.05n

* CHECK dout1_1 Vdout1_1ck141 = 1.8 time = 1420
.meas tran vdout1_1ck141 FIND v(dout1_1) AT=1420.05n

* CHECK dout1_2 Vdout1_2ck141 = 0 time = 1420
.meas tran vdout1_2ck141 FIND v(dout1_2) AT=1420.05n

* CHECK dout1_3 Vdout1_3ck141 = 1.8 time = 1420
.meas tran vdout1_3ck141 FIND v(dout1_3) AT=1420.05n

* CHECK dout1_4 Vdout1_4ck141 = 0 time = 1420
.meas tran vdout1_4ck141 FIND v(dout1_4) AT=1420.05n

* CHECK dout1_5 Vdout1_5ck141 = 1.8 time = 1420
.meas tran vdout1_5ck141 FIND v(dout1_5) AT=1420.05n

* CHECK dout1_6 Vdout1_6ck141 = 1.8 time = 1420
.meas tran vdout1_6ck141 FIND v(dout1_6) AT=1420.05n

* CHECK dout1_7 Vdout1_7ck141 = 1.8 time = 1420
.meas tran vdout1_7ck141 FIND v(dout1_7) AT=1420.05n

* CHECK dout1_0 Vdout1_0ck145 = 1.8 time = 1460
.meas tran vdout1_0ck145 FIND v(dout1_0) AT=1460.05n

* CHECK dout1_1 Vdout1_1ck145 = 0 time = 1460
.meas tran vdout1_1ck145 FIND v(dout1_1) AT=1460.05n

* CHECK dout1_2 Vdout1_2ck145 = 0 time = 1460
.meas tran vdout1_2ck145 FIND v(dout1_2) AT=1460.05n

* CHECK dout1_3 Vdout1_3ck145 = 0 time = 1460
.meas tran vdout1_3ck145 FIND v(dout1_3) AT=1460.05n

* CHECK dout1_4 Vdout1_4ck145 = 0 time = 1460
.meas tran vdout1_4ck145 FIND v(dout1_4) AT=1460.05n

* CHECK dout1_5 Vdout1_5ck145 = 1.8 time = 1460
.meas tran vdout1_5ck145 FIND v(dout1_5) AT=1460.05n

* CHECK dout1_6 Vdout1_6ck145 = 0 time = 1460
.meas tran vdout1_6ck145 FIND v(dout1_6) AT=1460.05n

* CHECK dout1_7 Vdout1_7ck145 = 1.8 time = 1460
.meas tran vdout1_7ck145 FIND v(dout1_7) AT=1460.05n

* CHECK dout0_0 Vdout0_0ck146 = 0 time = 1470
.meas tran vdout0_0ck146 FIND v(dout0_0) AT=1470.05n

* CHECK dout0_1 Vdout0_1ck146 = 0 time = 1470
.meas tran vdout0_1ck146 FIND v(dout0_1) AT=1470.05n

* CHECK dout0_2 Vdout0_2ck146 = 0 time = 1470
.meas tran vdout0_2ck146 FIND v(dout0_2) AT=1470.05n

* CHECK dout0_3 Vdout0_3ck146 = 0 time = 1470
.meas tran vdout0_3ck146 FIND v(dout0_3) AT=1470.05n

* CHECK dout0_4 Vdout0_4ck146 = 0 time = 1470
.meas tran vdout0_4ck146 FIND v(dout0_4) AT=1470.05n

* CHECK dout0_5 Vdout0_5ck146 = 0 time = 1470
.meas tran vdout0_5ck146 FIND v(dout0_5) AT=1470.05n

* CHECK dout0_6 Vdout0_6ck146 = 1.8 time = 1470
.meas tran vdout0_6ck146 FIND v(dout0_6) AT=1470.05n

* CHECK dout0_7 Vdout0_7ck146 = 1.8 time = 1470
.meas tran vdout0_7ck146 FIND v(dout0_7) AT=1470.05n

* CHECK dout1_0 Vdout1_0ck146 = 1.8 time = 1470
.meas tran vdout1_0ck146 FIND v(dout1_0) AT=1470.05n

* CHECK dout1_1 Vdout1_1ck146 = 1.8 time = 1470
.meas tran vdout1_1ck146 FIND v(dout1_1) AT=1470.05n

* CHECK dout1_2 Vdout1_2ck146 = 0 time = 1470
.meas tran vdout1_2ck146 FIND v(dout1_2) AT=1470.05n

* CHECK dout1_3 Vdout1_3ck146 = 1.8 time = 1470
.meas tran vdout1_3ck146 FIND v(dout1_3) AT=1470.05n

* CHECK dout1_4 Vdout1_4ck146 = 0 time = 1470
.meas tran vdout1_4ck146 FIND v(dout1_4) AT=1470.05n

* CHECK dout1_5 Vdout1_5ck146 = 1.8 time = 1470
.meas tran vdout1_5ck146 FIND v(dout1_5) AT=1470.05n

* CHECK dout1_6 Vdout1_6ck146 = 1.8 time = 1470
.meas tran vdout1_6ck146 FIND v(dout1_6) AT=1470.05n

* CHECK dout1_7 Vdout1_7ck146 = 1.8 time = 1470
.meas tran vdout1_7ck146 FIND v(dout1_7) AT=1470.05n

* CHECK dout1_0 Vdout1_0ck147 = 0 time = 1480
.meas tran vdout1_0ck147 FIND v(dout1_0) AT=1480.05n

* CHECK dout1_1 Vdout1_1ck147 = 0 time = 1480
.meas tran vdout1_1ck147 FIND v(dout1_1) AT=1480.05n

* CHECK dout1_2 Vdout1_2ck147 = 0 time = 1480
.meas tran vdout1_2ck147 FIND v(dout1_2) AT=1480.05n

* CHECK dout1_3 Vdout1_3ck147 = 0 time = 1480
.meas tran vdout1_3ck147 FIND v(dout1_3) AT=1480.05n

* CHECK dout1_4 Vdout1_4ck147 = 0 time = 1480
.meas tran vdout1_4ck147 FIND v(dout1_4) AT=1480.05n

* CHECK dout1_5 Vdout1_5ck147 = 0 time = 1480
.meas tran vdout1_5ck147 FIND v(dout1_5) AT=1480.05n

* CHECK dout1_6 Vdout1_6ck147 = 1.8 time = 1480
.meas tran vdout1_6ck147 FIND v(dout1_6) AT=1480.05n

* CHECK dout1_7 Vdout1_7ck147 = 1.8 time = 1480
.meas tran vdout1_7ck147 FIND v(dout1_7) AT=1480.05n

* CHECK dout0_0 Vdout0_0ck148 = 1.8 time = 1490
.meas tran vdout0_0ck148 FIND v(dout0_0) AT=1490.05n

* CHECK dout0_1 Vdout0_1ck148 = 0 time = 1490
.meas tran vdout0_1ck148 FIND v(dout0_1) AT=1490.05n

* CHECK dout0_2 Vdout0_2ck148 = 0 time = 1490
.meas tran vdout0_2ck148 FIND v(dout0_2) AT=1490.05n

* CHECK dout0_3 Vdout0_3ck148 = 0 time = 1490
.meas tran vdout0_3ck148 FIND v(dout0_3) AT=1490.05n

* CHECK dout0_4 Vdout0_4ck148 = 0 time = 1490
.meas tran vdout0_4ck148 FIND v(dout0_4) AT=1490.05n

* CHECK dout0_5 Vdout0_5ck148 = 1.8 time = 1490
.meas tran vdout0_5ck148 FIND v(dout0_5) AT=1490.05n

* CHECK dout0_6 Vdout0_6ck148 = 0 time = 1490
.meas tran vdout0_6ck148 FIND v(dout0_6) AT=1490.05n

* CHECK dout0_7 Vdout0_7ck148 = 1.8 time = 1490
.meas tran vdout0_7ck148 FIND v(dout0_7) AT=1490.05n

* CHECK dout1_0 Vdout1_0ck149 = 1.8 time = 1500
.meas tran vdout1_0ck149 FIND v(dout1_0) AT=1500.05n

* CHECK dout1_1 Vdout1_1ck149 = 0 time = 1500
.meas tran vdout1_1ck149 FIND v(dout1_1) AT=1500.05n

* CHECK dout1_2 Vdout1_2ck149 = 1.8 time = 1500
.meas tran vdout1_2ck149 FIND v(dout1_2) AT=1500.05n

* CHECK dout1_3 Vdout1_3ck149 = 1.8 time = 1500
.meas tran vdout1_3ck149 FIND v(dout1_3) AT=1500.05n

* CHECK dout1_4 Vdout1_4ck149 = 1.8 time = 1500
.meas tran vdout1_4ck149 FIND v(dout1_4) AT=1500.05n

* CHECK dout1_5 Vdout1_5ck149 = 1.8 time = 1500
.meas tran vdout1_5ck149 FIND v(dout1_5) AT=1500.05n

* CHECK dout1_6 Vdout1_6ck149 = 1.8 time = 1500
.meas tran vdout1_6ck149 FIND v(dout1_6) AT=1500.05n

* CHECK dout1_7 Vdout1_7ck149 = 1.8 time = 1500
.meas tran vdout1_7ck149 FIND v(dout1_7) AT=1500.05n

* CHECK dout0_0 Vdout0_0ck154 = 1.8 time = 1550
.meas tran vdout0_0ck154 FIND v(dout0_0) AT=1550.05n

* CHECK dout0_1 Vdout0_1ck154 = 0 time = 1550
.meas tran vdout0_1ck154 FIND v(dout0_1) AT=1550.05n

* CHECK dout0_2 Vdout0_2ck154 = 0 time = 1550
.meas tran vdout0_2ck154 FIND v(dout0_2) AT=1550.05n

* CHECK dout0_3 Vdout0_3ck154 = 0 time = 1550
.meas tran vdout0_3ck154 FIND v(dout0_3) AT=1550.05n

* CHECK dout0_4 Vdout0_4ck154 = 0 time = 1550
.meas tran vdout0_4ck154 FIND v(dout0_4) AT=1550.05n

* CHECK dout0_5 Vdout0_5ck154 = 1.8 time = 1550
.meas tran vdout0_5ck154 FIND v(dout0_5) AT=1550.05n

* CHECK dout0_6 Vdout0_6ck154 = 0 time = 1550
.meas tran vdout0_6ck154 FIND v(dout0_6) AT=1550.05n

* CHECK dout0_7 Vdout0_7ck154 = 1.8 time = 1550
.meas tran vdout0_7ck154 FIND v(dout0_7) AT=1550.05n

* CHECK dout1_0 Vdout1_0ck155 = 1.8 time = 1560
.meas tran vdout1_0ck155 FIND v(dout1_0) AT=1560.05n

* CHECK dout1_1 Vdout1_1ck155 = 0 time = 1560
.meas tran vdout1_1ck155 FIND v(dout1_1) AT=1560.05n

* CHECK dout1_2 Vdout1_2ck155 = 0 time = 1560
.meas tran vdout1_2ck155 FIND v(dout1_2) AT=1560.05n

* CHECK dout1_3 Vdout1_3ck155 = 0 time = 1560
.meas tran vdout1_3ck155 FIND v(dout1_3) AT=1560.05n

* CHECK dout1_4 Vdout1_4ck155 = 0 time = 1560
.meas tran vdout1_4ck155 FIND v(dout1_4) AT=1560.05n

* CHECK dout1_5 Vdout1_5ck155 = 1.8 time = 1560
.meas tran vdout1_5ck155 FIND v(dout1_5) AT=1560.05n

* CHECK dout1_6 Vdout1_6ck155 = 0 time = 1560
.meas tran vdout1_6ck155 FIND v(dout1_6) AT=1560.05n

* CHECK dout1_7 Vdout1_7ck155 = 1.8 time = 1560
.meas tran vdout1_7ck155 FIND v(dout1_7) AT=1560.05n

* CHECK dout0_0 Vdout0_0ck159 = 0 time = 1600
.meas tran vdout0_0ck159 FIND v(dout0_0) AT=1600.05n

* CHECK dout0_1 Vdout0_1ck159 = 0 time = 1600
.meas tran vdout0_1ck159 FIND v(dout0_1) AT=1600.05n

* CHECK dout0_2 Vdout0_2ck159 = 1.8 time = 1600
.meas tran vdout0_2ck159 FIND v(dout0_2) AT=1600.05n

* CHECK dout0_3 Vdout0_3ck159 = 1.8 time = 1600
.meas tran vdout0_3ck159 FIND v(dout0_3) AT=1600.05n

* CHECK dout0_4 Vdout0_4ck159 = 0 time = 1600
.meas tran vdout0_4ck159 FIND v(dout0_4) AT=1600.05n

* CHECK dout0_5 Vdout0_5ck159 = 1.8 time = 1600
.meas tran vdout0_5ck159 FIND v(dout0_5) AT=1600.05n

* CHECK dout0_6 Vdout0_6ck159 = 0 time = 1600
.meas tran vdout0_6ck159 FIND v(dout0_6) AT=1600.05n

* CHECK dout0_7 Vdout0_7ck159 = 1.8 time = 1600
.meas tran vdout0_7ck159 FIND v(dout0_7) AT=1600.05n

* CHECK dout0_0 Vdout0_0ck160 = 0 time = 1610
.meas tran vdout0_0ck160 FIND v(dout0_0) AT=1610.05n

* CHECK dout0_1 Vdout0_1ck160 = 0 time = 1610
.meas tran vdout0_1ck160 FIND v(dout0_1) AT=1610.05n

* CHECK dout0_2 Vdout0_2ck160 = 0 time = 1610
.meas tran vdout0_2ck160 FIND v(dout0_2) AT=1610.05n

* CHECK dout0_3 Vdout0_3ck160 = 0 time = 1610
.meas tran vdout0_3ck160 FIND v(dout0_3) AT=1610.05n

* CHECK dout0_4 Vdout0_4ck160 = 1.8 time = 1610
.meas tran vdout0_4ck160 FIND v(dout0_4) AT=1610.05n

* CHECK dout0_5 Vdout0_5ck160 = 1.8 time = 1610
.meas tran vdout0_5ck160 FIND v(dout0_5) AT=1610.05n

* CHECK dout0_6 Vdout0_6ck160 = 0 time = 1610
.meas tran vdout0_6ck160 FIND v(dout0_6) AT=1610.05n

* CHECK dout0_7 Vdout0_7ck160 = 1.8 time = 1610
.meas tran vdout0_7ck160 FIND v(dout0_7) AT=1610.05n

* CHECK dout1_0 Vdout1_0ck161 = 0 time = 1620
.meas tran vdout1_0ck161 FIND v(dout1_0) AT=1620.05n

* CHECK dout1_1 Vdout1_1ck161 = 0 time = 1620
.meas tran vdout1_1ck161 FIND v(dout1_1) AT=1620.05n

* CHECK dout1_2 Vdout1_2ck161 = 1.8 time = 1620
.meas tran vdout1_2ck161 FIND v(dout1_2) AT=1620.05n

* CHECK dout1_3 Vdout1_3ck161 = 0 time = 1620
.meas tran vdout1_3ck161 FIND v(dout1_3) AT=1620.05n

* CHECK dout1_4 Vdout1_4ck161 = 1.8 time = 1620
.meas tran vdout1_4ck161 FIND v(dout1_4) AT=1620.05n

* CHECK dout1_5 Vdout1_5ck161 = 0 time = 1620
.meas tran vdout1_5ck161 FIND v(dout1_5) AT=1620.05n

* CHECK dout1_6 Vdout1_6ck161 = 1.8 time = 1620
.meas tran vdout1_6ck161 FIND v(dout1_6) AT=1620.05n

* CHECK dout1_7 Vdout1_7ck161 = 0 time = 1620
.meas tran vdout1_7ck161 FIND v(dout1_7) AT=1620.05n

* CHECK dout1_0 Vdout1_0ck162 = 1.8 time = 1630
.meas tran vdout1_0ck162 FIND v(dout1_0) AT=1630.05n

* CHECK dout1_1 Vdout1_1ck162 = 0 time = 1630
.meas tran vdout1_1ck162 FIND v(dout1_1) AT=1630.05n

* CHECK dout1_2 Vdout1_2ck162 = 0 time = 1630
.meas tran vdout1_2ck162 FIND v(dout1_2) AT=1630.05n

* CHECK dout1_3 Vdout1_3ck162 = 0 time = 1630
.meas tran vdout1_3ck162 FIND v(dout1_3) AT=1630.05n

* CHECK dout1_4 Vdout1_4ck162 = 0 time = 1630
.meas tran vdout1_4ck162 FIND v(dout1_4) AT=1630.05n

* CHECK dout1_5 Vdout1_5ck162 = 1.8 time = 1630
.meas tran vdout1_5ck162 FIND v(dout1_5) AT=1630.05n

* CHECK dout1_6 Vdout1_6ck162 = 0 time = 1630
.meas tran vdout1_6ck162 FIND v(dout1_6) AT=1630.05n

* CHECK dout1_7 Vdout1_7ck162 = 0 time = 1630
.meas tran vdout1_7ck162 FIND v(dout1_7) AT=1630.05n

* CHECK dout0_0 Vdout0_0ck163 = 1.8 time = 1640
.meas tran vdout0_0ck163 FIND v(dout0_0) AT=1640.05n

* CHECK dout0_1 Vdout0_1ck163 = 0 time = 1640
.meas tran vdout0_1ck163 FIND v(dout0_1) AT=1640.05n

* CHECK dout0_2 Vdout0_2ck163 = 0 time = 1640
.meas tran vdout0_2ck163 FIND v(dout0_2) AT=1640.05n

* CHECK dout0_3 Vdout0_3ck163 = 0 time = 1640
.meas tran vdout0_3ck163 FIND v(dout0_3) AT=1640.05n

* CHECK dout0_4 Vdout0_4ck163 = 0 time = 1640
.meas tran vdout0_4ck163 FIND v(dout0_4) AT=1640.05n

* CHECK dout0_5 Vdout0_5ck163 = 1.8 time = 1640
.meas tran vdout0_5ck163 FIND v(dout0_5) AT=1640.05n

* CHECK dout0_6 Vdout0_6ck163 = 0 time = 1640
.meas tran vdout0_6ck163 FIND v(dout0_6) AT=1640.05n

* CHECK dout0_7 Vdout0_7ck163 = 1.8 time = 1640
.meas tran vdout0_7ck163 FIND v(dout0_7) AT=1640.05n

* CHECK dout1_0 Vdout1_0ck163 = 0 time = 1640
.meas tran vdout1_0ck163 FIND v(dout1_0) AT=1640.05n

* CHECK dout1_1 Vdout1_1ck163 = 0 time = 1640
.meas tran vdout1_1ck163 FIND v(dout1_1) AT=1640.05n

* CHECK dout1_2 Vdout1_2ck163 = 1.8 time = 1640
.meas tran vdout1_2ck163 FIND v(dout1_2) AT=1640.05n

* CHECK dout1_3 Vdout1_3ck163 = 1.8 time = 1640
.meas tran vdout1_3ck163 FIND v(dout1_3) AT=1640.05n

* CHECK dout1_4 Vdout1_4ck163 = 1.8 time = 1640
.meas tran vdout1_4ck163 FIND v(dout1_4) AT=1640.05n

* CHECK dout1_5 Vdout1_5ck163 = 0 time = 1640
.meas tran vdout1_5ck163 FIND v(dout1_5) AT=1640.05n

* CHECK dout1_6 Vdout1_6ck163 = 1.8 time = 1640
.meas tran vdout1_6ck163 FIND v(dout1_6) AT=1640.05n

* CHECK dout1_7 Vdout1_7ck163 = 0 time = 1640
.meas tran vdout1_7ck163 FIND v(dout1_7) AT=1640.05n

* CHECK dout1_0 Vdout1_0ck164 = 0 time = 1650
.meas tran vdout1_0ck164 FIND v(dout1_0) AT=1650.05n

* CHECK dout1_1 Vdout1_1ck164 = 0 time = 1650
.meas tran vdout1_1ck164 FIND v(dout1_1) AT=1650.05n

* CHECK dout1_2 Vdout1_2ck164 = 1.8 time = 1650
.meas tran vdout1_2ck164 FIND v(dout1_2) AT=1650.05n

* CHECK dout1_3 Vdout1_3ck164 = 1.8 time = 1650
.meas tran vdout1_3ck164 FIND v(dout1_3) AT=1650.05n

* CHECK dout1_4 Vdout1_4ck164 = 1.8 time = 1650
.meas tran vdout1_4ck164 FIND v(dout1_4) AT=1650.05n

* CHECK dout1_5 Vdout1_5ck164 = 0 time = 1650
.meas tran vdout1_5ck164 FIND v(dout1_5) AT=1650.05n

* CHECK dout1_6 Vdout1_6ck164 = 1.8 time = 1650
.meas tran vdout1_6ck164 FIND v(dout1_6) AT=1650.05n

* CHECK dout1_7 Vdout1_7ck164 = 0 time = 1650
.meas tran vdout1_7ck164 FIND v(dout1_7) AT=1650.05n

* CHECK dout0_0 Vdout0_0ck165 = 1.8 time = 1660
.meas tran vdout0_0ck165 FIND v(dout0_0) AT=1660.05n

* CHECK dout0_1 Vdout0_1ck165 = 0 time = 1660
.meas tran vdout0_1ck165 FIND v(dout0_1) AT=1660.05n

* CHECK dout0_2 Vdout0_2ck165 = 0 time = 1660
.meas tran vdout0_2ck165 FIND v(dout0_2) AT=1660.05n

* CHECK dout0_3 Vdout0_3ck165 = 0 time = 1660
.meas tran vdout0_3ck165 FIND v(dout0_3) AT=1660.05n

* CHECK dout0_4 Vdout0_4ck165 = 0 time = 1660
.meas tran vdout0_4ck165 FIND v(dout0_4) AT=1660.05n

* CHECK dout0_5 Vdout0_5ck165 = 1.8 time = 1660
.meas tran vdout0_5ck165 FIND v(dout0_5) AT=1660.05n

* CHECK dout0_6 Vdout0_6ck165 = 0 time = 1660
.meas tran vdout0_6ck165 FIND v(dout0_6) AT=1660.05n

* CHECK dout0_7 Vdout0_7ck165 = 0 time = 1660
.meas tran vdout0_7ck165 FIND v(dout0_7) AT=1660.05n

* CHECK dout1_0 Vdout1_0ck166 = 1.8 time = 1670
.meas tran vdout1_0ck166 FIND v(dout1_0) AT=1670.05n

* CHECK dout1_1 Vdout1_1ck166 = 0 time = 1670
.meas tran vdout1_1ck166 FIND v(dout1_1) AT=1670.05n

* CHECK dout1_2 Vdout1_2ck166 = 0 time = 1670
.meas tran vdout1_2ck166 FIND v(dout1_2) AT=1670.05n

* CHECK dout1_3 Vdout1_3ck166 = 0 time = 1670
.meas tran vdout1_3ck166 FIND v(dout1_3) AT=1670.05n

* CHECK dout1_4 Vdout1_4ck166 = 0 time = 1670
.meas tran vdout1_4ck166 FIND v(dout1_4) AT=1670.05n

* CHECK dout1_5 Vdout1_5ck166 = 1.8 time = 1670
.meas tran vdout1_5ck166 FIND v(dout1_5) AT=1670.05n

* CHECK dout1_6 Vdout1_6ck166 = 0 time = 1670
.meas tran vdout1_6ck166 FIND v(dout1_6) AT=1670.05n

* CHECK dout1_7 Vdout1_7ck166 = 0 time = 1670
.meas tran vdout1_7ck166 FIND v(dout1_7) AT=1670.05n

* CHECK dout1_0 Vdout1_0ck168 = 0 time = 1690
.meas tran vdout1_0ck168 FIND v(dout1_0) AT=1690.05n

* CHECK dout1_1 Vdout1_1ck168 = 0 time = 1690
.meas tran vdout1_1ck168 FIND v(dout1_1) AT=1690.05n

* CHECK dout1_2 Vdout1_2ck168 = 1.8 time = 1690
.meas tran vdout1_2ck168 FIND v(dout1_2) AT=1690.05n

* CHECK dout1_3 Vdout1_3ck168 = 1.8 time = 1690
.meas tran vdout1_3ck168 FIND v(dout1_3) AT=1690.05n

* CHECK dout1_4 Vdout1_4ck168 = 0 time = 1690
.meas tran vdout1_4ck168 FIND v(dout1_4) AT=1690.05n

* CHECK dout1_5 Vdout1_5ck168 = 1.8 time = 1690
.meas tran vdout1_5ck168 FIND v(dout1_5) AT=1690.05n

* CHECK dout1_6 Vdout1_6ck168 = 1.8 time = 1690
.meas tran vdout1_6ck168 FIND v(dout1_6) AT=1690.05n

* CHECK dout1_7 Vdout1_7ck168 = 1.8 time = 1690
.meas tran vdout1_7ck168 FIND v(dout1_7) AT=1690.05n

* CHECK dout0_0 Vdout0_0ck169 = 0 time = 1700
.meas tran vdout0_0ck169 FIND v(dout0_0) AT=1700.05n

* CHECK dout0_1 Vdout0_1ck169 = 0 time = 1700
.meas tran vdout0_1ck169 FIND v(dout0_1) AT=1700.05n

* CHECK dout0_2 Vdout0_2ck169 = 1.8 time = 1700
.meas tran vdout0_2ck169 FIND v(dout0_2) AT=1700.05n

* CHECK dout0_3 Vdout0_3ck169 = 1.8 time = 1700
.meas tran vdout0_3ck169 FIND v(dout0_3) AT=1700.05n

* CHECK dout0_4 Vdout0_4ck169 = 0 time = 1700
.meas tran vdout0_4ck169 FIND v(dout0_4) AT=1700.05n

* CHECK dout0_5 Vdout0_5ck169 = 1.8 time = 1700
.meas tran vdout0_5ck169 FIND v(dout0_5) AT=1700.05n

* CHECK dout0_6 Vdout0_6ck169 = 1.8 time = 1700
.meas tran vdout0_6ck169 FIND v(dout0_6) AT=1700.05n

* CHECK dout0_7 Vdout0_7ck169 = 1.8 time = 1700
.meas tran vdout0_7ck169 FIND v(dout0_7) AT=1700.05n

* CHECK dout1_0 Vdout1_0ck169 = 1.8 time = 1700
.meas tran vdout1_0ck169 FIND v(dout1_0) AT=1700.05n

* CHECK dout1_1 Vdout1_1ck169 = 0 time = 1700
.meas tran vdout1_1ck169 FIND v(dout1_1) AT=1700.05n

* CHECK dout1_2 Vdout1_2ck169 = 0 time = 1700
.meas tran vdout1_2ck169 FIND v(dout1_2) AT=1700.05n

* CHECK dout1_3 Vdout1_3ck169 = 0 time = 1700
.meas tran vdout1_3ck169 FIND v(dout1_3) AT=1700.05n

* CHECK dout1_4 Vdout1_4ck169 = 0 time = 1700
.meas tran vdout1_4ck169 FIND v(dout1_4) AT=1700.05n

* CHECK dout1_5 Vdout1_5ck169 = 1.8 time = 1700
.meas tran vdout1_5ck169 FIND v(dout1_5) AT=1700.05n

* CHECK dout1_6 Vdout1_6ck169 = 0 time = 1700
.meas tran vdout1_6ck169 FIND v(dout1_6) AT=1700.05n

* CHECK dout1_7 Vdout1_7ck169 = 0 time = 1700
.meas tran vdout1_7ck169 FIND v(dout1_7) AT=1700.05n

* CHECK dout1_0 Vdout1_0ck170 = 0 time = 1710
.meas tran vdout1_0ck170 FIND v(dout1_0) AT=1710.05n

* CHECK dout1_1 Vdout1_1ck170 = 0 time = 1710
.meas tran vdout1_1ck170 FIND v(dout1_1) AT=1710.05n

* CHECK dout1_2 Vdout1_2ck170 = 1.8 time = 1710
.meas tran vdout1_2ck170 FIND v(dout1_2) AT=1710.05n

* CHECK dout1_3 Vdout1_3ck170 = 1.8 time = 1710
.meas tran vdout1_3ck170 FIND v(dout1_3) AT=1710.05n

* CHECK dout1_4 Vdout1_4ck170 = 0 time = 1710
.meas tran vdout1_4ck170 FIND v(dout1_4) AT=1710.05n

* CHECK dout1_5 Vdout1_5ck170 = 1.8 time = 1710
.meas tran vdout1_5ck170 FIND v(dout1_5) AT=1710.05n

* CHECK dout1_6 Vdout1_6ck170 = 1.8 time = 1710
.meas tran vdout1_6ck170 FIND v(dout1_6) AT=1710.05n

* CHECK dout1_7 Vdout1_7ck170 = 1.8 time = 1710
.meas tran vdout1_7ck170 FIND v(dout1_7) AT=1710.05n

* CHECK dout1_0 Vdout1_0ck173 = 0 time = 1740
.meas tran vdout1_0ck173 FIND v(dout1_0) AT=1740.05n

* CHECK dout1_1 Vdout1_1ck173 = 0 time = 1740
.meas tran vdout1_1ck173 FIND v(dout1_1) AT=1740.05n

* CHECK dout1_2 Vdout1_2ck173 = 1.8 time = 1740
.meas tran vdout1_2ck173 FIND v(dout1_2) AT=1740.05n

* CHECK dout1_3 Vdout1_3ck173 = 1.8 time = 1740
.meas tran vdout1_3ck173 FIND v(dout1_3) AT=1740.05n

* CHECK dout1_4 Vdout1_4ck173 = 0 time = 1740
.meas tran vdout1_4ck173 FIND v(dout1_4) AT=1740.05n

* CHECK dout1_5 Vdout1_5ck173 = 1.8 time = 1740
.meas tran vdout1_5ck173 FIND v(dout1_5) AT=1740.05n

* CHECK dout1_6 Vdout1_6ck173 = 1.8 time = 1740
.meas tran vdout1_6ck173 FIND v(dout1_6) AT=1740.05n

* CHECK dout1_7 Vdout1_7ck173 = 1.8 time = 1740
.meas tran vdout1_7ck173 FIND v(dout1_7) AT=1740.05n

* CHECK dout0_0 Vdout0_0ck174 = 1.8 time = 1750
.meas tran vdout0_0ck174 FIND v(dout0_0) AT=1750.05n

* CHECK dout0_1 Vdout0_1ck174 = 0 time = 1750
.meas tran vdout0_1ck174 FIND v(dout0_1) AT=1750.05n

* CHECK dout0_2 Vdout0_2ck174 = 1.8 time = 1750
.meas tran vdout0_2ck174 FIND v(dout0_2) AT=1750.05n

* CHECK dout0_3 Vdout0_3ck174 = 0 time = 1750
.meas tran vdout0_3ck174 FIND v(dout0_3) AT=1750.05n

* CHECK dout0_4 Vdout0_4ck174 = 0 time = 1750
.meas tran vdout0_4ck174 FIND v(dout0_4) AT=1750.05n

* CHECK dout0_5 Vdout0_5ck174 = 0 time = 1750
.meas tran vdout0_5ck174 FIND v(dout0_5) AT=1750.05n

* CHECK dout0_6 Vdout0_6ck174 = 0 time = 1750
.meas tran vdout0_6ck174 FIND v(dout0_6) AT=1750.05n

* CHECK dout0_7 Vdout0_7ck174 = 1.8 time = 1750
.meas tran vdout0_7ck174 FIND v(dout0_7) AT=1750.05n

* CHECK dout1_0 Vdout1_0ck174 = 0 time = 1750
.meas tran vdout1_0ck174 FIND v(dout1_0) AT=1750.05n

* CHECK dout1_1 Vdout1_1ck174 = 0 time = 1750
.meas tran vdout1_1ck174 FIND v(dout1_1) AT=1750.05n

* CHECK dout1_2 Vdout1_2ck174 = 1.8 time = 1750
.meas tran vdout1_2ck174 FIND v(dout1_2) AT=1750.05n

* CHECK dout1_3 Vdout1_3ck174 = 1.8 time = 1750
.meas tran vdout1_3ck174 FIND v(dout1_3) AT=1750.05n

* CHECK dout1_4 Vdout1_4ck174 = 0 time = 1750
.meas tran vdout1_4ck174 FIND v(dout1_4) AT=1750.05n

* CHECK dout1_5 Vdout1_5ck174 = 1.8 time = 1750
.meas tran vdout1_5ck174 FIND v(dout1_5) AT=1750.05n

* CHECK dout1_6 Vdout1_6ck174 = 1.8 time = 1750
.meas tran vdout1_6ck174 FIND v(dout1_6) AT=1750.05n

* CHECK dout1_7 Vdout1_7ck174 = 1.8 time = 1750
.meas tran vdout1_7ck174 FIND v(dout1_7) AT=1750.05n

* CHECK dout0_0 Vdout0_0ck175 = 1.8 time = 1760
.meas tran vdout0_0ck175 FIND v(dout0_0) AT=1760.05n

* CHECK dout0_1 Vdout0_1ck175 = 0 time = 1760
.meas tran vdout0_1ck175 FIND v(dout0_1) AT=1760.05n

* CHECK dout0_2 Vdout0_2ck175 = 1.8 time = 1760
.meas tran vdout0_2ck175 FIND v(dout0_2) AT=1760.05n

* CHECK dout0_3 Vdout0_3ck175 = 0 time = 1760
.meas tran vdout0_3ck175 FIND v(dout0_3) AT=1760.05n

* CHECK dout0_4 Vdout0_4ck175 = 0 time = 1760
.meas tran vdout0_4ck175 FIND v(dout0_4) AT=1760.05n

* CHECK dout0_5 Vdout0_5ck175 = 0 time = 1760
.meas tran vdout0_5ck175 FIND v(dout0_5) AT=1760.05n

* CHECK dout0_6 Vdout0_6ck175 = 0 time = 1760
.meas tran vdout0_6ck175 FIND v(dout0_6) AT=1760.05n

* CHECK dout0_7 Vdout0_7ck175 = 1.8 time = 1760
.meas tran vdout0_7ck175 FIND v(dout0_7) AT=1760.05n

* CHECK dout1_0 Vdout1_0ck175 = 0 time = 1760
.meas tran vdout1_0ck175 FIND v(dout1_0) AT=1760.05n

* CHECK dout1_1 Vdout1_1ck175 = 0 time = 1760
.meas tran vdout1_1ck175 FIND v(dout1_1) AT=1760.05n

* CHECK dout1_2 Vdout1_2ck175 = 1.8 time = 1760
.meas tran vdout1_2ck175 FIND v(dout1_2) AT=1760.05n

* CHECK dout1_3 Vdout1_3ck175 = 1.8 time = 1760
.meas tran vdout1_3ck175 FIND v(dout1_3) AT=1760.05n

* CHECK dout1_4 Vdout1_4ck175 = 0 time = 1760
.meas tran vdout1_4ck175 FIND v(dout1_4) AT=1760.05n

* CHECK dout1_5 Vdout1_5ck175 = 1.8 time = 1760
.meas tran vdout1_5ck175 FIND v(dout1_5) AT=1760.05n

* CHECK dout1_6 Vdout1_6ck175 = 1.8 time = 1760
.meas tran vdout1_6ck175 FIND v(dout1_6) AT=1760.05n

* CHECK dout1_7 Vdout1_7ck175 = 1.8 time = 1760
.meas tran vdout1_7ck175 FIND v(dout1_7) AT=1760.05n

* CHECK dout0_0 Vdout0_0ck176 = 0 time = 1770
.meas tran vdout0_0ck176 FIND v(dout0_0) AT=1770.05n

* CHECK dout0_1 Vdout0_1ck176 = 1.8 time = 1770
.meas tran vdout0_1ck176 FIND v(dout0_1) AT=1770.05n

* CHECK dout0_2 Vdout0_2ck176 = 1.8 time = 1770
.meas tran vdout0_2ck176 FIND v(dout0_2) AT=1770.05n

* CHECK dout0_3 Vdout0_3ck176 = 0 time = 1770
.meas tran vdout0_3ck176 FIND v(dout0_3) AT=1770.05n

* CHECK dout0_4 Vdout0_4ck176 = 0 time = 1770
.meas tran vdout0_4ck176 FIND v(dout0_4) AT=1770.05n

* CHECK dout0_5 Vdout0_5ck176 = 0 time = 1770
.meas tran vdout0_5ck176 FIND v(dout0_5) AT=1770.05n

* CHECK dout0_6 Vdout0_6ck176 = 0 time = 1770
.meas tran vdout0_6ck176 FIND v(dout0_6) AT=1770.05n

* CHECK dout0_7 Vdout0_7ck176 = 0 time = 1770
.meas tran vdout0_7ck176 FIND v(dout0_7) AT=1770.05n

* CHECK dout1_0 Vdout1_0ck176 = 0 time = 1770
.meas tran vdout1_0ck176 FIND v(dout1_0) AT=1770.05n

* CHECK dout1_1 Vdout1_1ck176 = 1.8 time = 1770
.meas tran vdout1_1ck176 FIND v(dout1_1) AT=1770.05n

* CHECK dout1_2 Vdout1_2ck176 = 1.8 time = 1770
.meas tran vdout1_2ck176 FIND v(dout1_2) AT=1770.05n

* CHECK dout1_3 Vdout1_3ck176 = 0 time = 1770
.meas tran vdout1_3ck176 FIND v(dout1_3) AT=1770.05n

* CHECK dout1_4 Vdout1_4ck176 = 0 time = 1770
.meas tran vdout1_4ck176 FIND v(dout1_4) AT=1770.05n

* CHECK dout1_5 Vdout1_5ck176 = 0 time = 1770
.meas tran vdout1_5ck176 FIND v(dout1_5) AT=1770.05n

* CHECK dout1_6 Vdout1_6ck176 = 0 time = 1770
.meas tran vdout1_6ck176 FIND v(dout1_6) AT=1770.05n

* CHECK dout1_7 Vdout1_7ck176 = 0 time = 1770
.meas tran vdout1_7ck176 FIND v(dout1_7) AT=1770.05n

* CHECK dout0_0 Vdout0_0ck177 = 0 time = 1780
.meas tran vdout0_0ck177 FIND v(dout0_0) AT=1780.05n

* CHECK dout0_1 Vdout0_1ck177 = 1.8 time = 1780
.meas tran vdout0_1ck177 FIND v(dout0_1) AT=1780.05n

* CHECK dout0_2 Vdout0_2ck177 = 0 time = 1780
.meas tran vdout0_2ck177 FIND v(dout0_2) AT=1780.05n

* CHECK dout0_3 Vdout0_3ck177 = 1.8 time = 1780
.meas tran vdout0_3ck177 FIND v(dout0_3) AT=1780.05n

* CHECK dout0_4 Vdout0_4ck177 = 0 time = 1780
.meas tran vdout0_4ck177 FIND v(dout0_4) AT=1780.05n

* CHECK dout0_5 Vdout0_5ck177 = 0 time = 1780
.meas tran vdout0_5ck177 FIND v(dout0_5) AT=1780.05n

* CHECK dout0_6 Vdout0_6ck177 = 1.8 time = 1780
.meas tran vdout0_6ck177 FIND v(dout0_6) AT=1780.05n

* CHECK dout0_7 Vdout0_7ck177 = 1.8 time = 1780
.meas tran vdout0_7ck177 FIND v(dout0_7) AT=1780.05n

* CHECK dout1_0 Vdout1_0ck177 = 0 time = 1780
.meas tran vdout1_0ck177 FIND v(dout1_0) AT=1780.05n

* CHECK dout1_1 Vdout1_1ck177 = 0 time = 1780
.meas tran vdout1_1ck177 FIND v(dout1_1) AT=1780.05n

* CHECK dout1_2 Vdout1_2ck177 = 1.8 time = 1780
.meas tran vdout1_2ck177 FIND v(dout1_2) AT=1780.05n

* CHECK dout1_3 Vdout1_3ck177 = 1.8 time = 1780
.meas tran vdout1_3ck177 FIND v(dout1_3) AT=1780.05n

* CHECK dout1_4 Vdout1_4ck177 = 0 time = 1780
.meas tran vdout1_4ck177 FIND v(dout1_4) AT=1780.05n

* CHECK dout1_5 Vdout1_5ck177 = 1.8 time = 1780
.meas tran vdout1_5ck177 FIND v(dout1_5) AT=1780.05n

* CHECK dout1_6 Vdout1_6ck177 = 1.8 time = 1780
.meas tran vdout1_6ck177 FIND v(dout1_6) AT=1780.05n

* CHECK dout1_7 Vdout1_7ck177 = 1.8 time = 1780
.meas tran vdout1_7ck177 FIND v(dout1_7) AT=1780.05n

* CHECK dout0_0 Vdout0_0ck179 = 0 time = 1800
.meas tran vdout0_0ck179 FIND v(dout0_0) AT=1800.05n

* CHECK dout0_1 Vdout0_1ck179 = 1.8 time = 1800
.meas tran vdout0_1ck179 FIND v(dout0_1) AT=1800.05n

* CHECK dout0_2 Vdout0_2ck179 = 0 time = 1800
.meas tran vdout0_2ck179 FIND v(dout0_2) AT=1800.05n

* CHECK dout0_3 Vdout0_3ck179 = 1.8 time = 1800
.meas tran vdout0_3ck179 FIND v(dout0_3) AT=1800.05n

* CHECK dout0_4 Vdout0_4ck179 = 0 time = 1800
.meas tran vdout0_4ck179 FIND v(dout0_4) AT=1800.05n

* CHECK dout0_5 Vdout0_5ck179 = 0 time = 1800
.meas tran vdout0_5ck179 FIND v(dout0_5) AT=1800.05n

* CHECK dout0_6 Vdout0_6ck179 = 1.8 time = 1800
.meas tran vdout0_6ck179 FIND v(dout0_6) AT=1800.05n

* CHECK dout0_7 Vdout0_7ck179 = 1.8 time = 1800
.meas tran vdout0_7ck179 FIND v(dout0_7) AT=1800.05n

* CHECK dout1_0 Vdout1_0ck179 = 0 time = 1800
.meas tran vdout1_0ck179 FIND v(dout1_0) AT=1800.05n

* CHECK dout1_1 Vdout1_1ck179 = 0 time = 1800
.meas tran vdout1_1ck179 FIND v(dout1_1) AT=1800.05n

* CHECK dout1_2 Vdout1_2ck179 = 1.8 time = 1800
.meas tran vdout1_2ck179 FIND v(dout1_2) AT=1800.05n

* CHECK dout1_3 Vdout1_3ck179 = 1.8 time = 1800
.meas tran vdout1_3ck179 FIND v(dout1_3) AT=1800.05n

* CHECK dout1_4 Vdout1_4ck179 = 0 time = 1800
.meas tran vdout1_4ck179 FIND v(dout1_4) AT=1800.05n

* CHECK dout1_5 Vdout1_5ck179 = 1.8 time = 1800
.meas tran vdout1_5ck179 FIND v(dout1_5) AT=1800.05n

* CHECK dout1_6 Vdout1_6ck179 = 1.8 time = 1800
.meas tran vdout1_6ck179 FIND v(dout1_6) AT=1800.05n

* CHECK dout1_7 Vdout1_7ck179 = 1.8 time = 1800
.meas tran vdout1_7ck179 FIND v(dout1_7) AT=1800.05n

* CHECK dout1_0 Vdout1_0ck181 = 1.8 time = 1820
.meas tran vdout1_0ck181 FIND v(dout1_0) AT=1820.05n

* CHECK dout1_1 Vdout1_1ck181 = 0 time = 1820
.meas tran vdout1_1ck181 FIND v(dout1_1) AT=1820.05n

* CHECK dout1_2 Vdout1_2ck181 = 1.8 time = 1820
.meas tran vdout1_2ck181 FIND v(dout1_2) AT=1820.05n

* CHECK dout1_3 Vdout1_3ck181 = 0 time = 1820
.meas tran vdout1_3ck181 FIND v(dout1_3) AT=1820.05n

* CHECK dout1_4 Vdout1_4ck181 = 0 time = 1820
.meas tran vdout1_4ck181 FIND v(dout1_4) AT=1820.05n

* CHECK dout1_5 Vdout1_5ck181 = 0 time = 1820
.meas tran vdout1_5ck181 FIND v(dout1_5) AT=1820.05n

* CHECK dout1_6 Vdout1_6ck181 = 0 time = 1820
.meas tran vdout1_6ck181 FIND v(dout1_6) AT=1820.05n

* CHECK dout1_7 Vdout1_7ck181 = 1.8 time = 1820
.meas tran vdout1_7ck181 FIND v(dout1_7) AT=1820.05n

* CHECK dout0_0 Vdout0_0ck182 = 0 time = 1830
.meas tran vdout0_0ck182 FIND v(dout0_0) AT=1830.05n

* CHECK dout0_1 Vdout0_1ck182 = 1.8 time = 1830
.meas tran vdout0_1ck182 FIND v(dout0_1) AT=1830.05n

* CHECK dout0_2 Vdout0_2ck182 = 1.8 time = 1830
.meas tran vdout0_2ck182 FIND v(dout0_2) AT=1830.05n

* CHECK dout0_3 Vdout0_3ck182 = 1.8 time = 1830
.meas tran vdout0_3ck182 FIND v(dout0_3) AT=1830.05n

* CHECK dout0_4 Vdout0_4ck182 = 0 time = 1830
.meas tran vdout0_4ck182 FIND v(dout0_4) AT=1830.05n

* CHECK dout0_5 Vdout0_5ck182 = 1.8 time = 1830
.meas tran vdout0_5ck182 FIND v(dout0_5) AT=1830.05n

* CHECK dout0_6 Vdout0_6ck182 = 0 time = 1830
.meas tran vdout0_6ck182 FIND v(dout0_6) AT=1830.05n

* CHECK dout0_7 Vdout0_7ck182 = 1.8 time = 1830
.meas tran vdout0_7ck182 FIND v(dout0_7) AT=1830.05n

* CHECK dout0_0 Vdout0_0ck183 = 0 time = 1840
.meas tran vdout0_0ck183 FIND v(dout0_0) AT=1840.05n

* CHECK dout0_1 Vdout0_1ck183 = 0 time = 1840
.meas tran vdout0_1ck183 FIND v(dout0_1) AT=1840.05n

* CHECK dout0_2 Vdout0_2ck183 = 1.8 time = 1840
.meas tran vdout0_2ck183 FIND v(dout0_2) AT=1840.05n

* CHECK dout0_3 Vdout0_3ck183 = 1.8 time = 1840
.meas tran vdout0_3ck183 FIND v(dout0_3) AT=1840.05n

* CHECK dout0_4 Vdout0_4ck183 = 1.8 time = 1840
.meas tran vdout0_4ck183 FIND v(dout0_4) AT=1840.05n

* CHECK dout0_5 Vdout0_5ck183 = 1.8 time = 1840
.meas tran vdout0_5ck183 FIND v(dout0_5) AT=1840.05n

* CHECK dout0_6 Vdout0_6ck183 = 0 time = 1840
.meas tran vdout0_6ck183 FIND v(dout0_6) AT=1840.05n

* CHECK dout0_7 Vdout0_7ck183 = 1.8 time = 1840
.meas tran vdout0_7ck183 FIND v(dout0_7) AT=1840.05n

* CHECK dout1_0 Vdout1_0ck183 = 0 time = 1840
.meas tran vdout1_0ck183 FIND v(dout1_0) AT=1840.05n

* CHECK dout1_1 Vdout1_1ck183 = 1.8 time = 1840
.meas tran vdout1_1ck183 FIND v(dout1_1) AT=1840.05n

* CHECK dout1_2 Vdout1_2ck183 = 1.8 time = 1840
.meas tran vdout1_2ck183 FIND v(dout1_2) AT=1840.05n

* CHECK dout1_3 Vdout1_3ck183 = 1.8 time = 1840
.meas tran vdout1_3ck183 FIND v(dout1_3) AT=1840.05n

* CHECK dout1_4 Vdout1_4ck183 = 0 time = 1840
.meas tran vdout1_4ck183 FIND v(dout1_4) AT=1840.05n

* CHECK dout1_5 Vdout1_5ck183 = 1.8 time = 1840
.meas tran vdout1_5ck183 FIND v(dout1_5) AT=1840.05n

* CHECK dout1_6 Vdout1_6ck183 = 0 time = 1840
.meas tran vdout1_6ck183 FIND v(dout1_6) AT=1840.05n

* CHECK dout1_7 Vdout1_7ck183 = 1.8 time = 1840
.meas tran vdout1_7ck183 FIND v(dout1_7) AT=1840.05n

* CHECK dout0_0 Vdout0_0ck184 = 1.8 time = 1850
.meas tran vdout0_0ck184 FIND v(dout0_0) AT=1850.05n

* CHECK dout0_1 Vdout0_1ck184 = 0 time = 1850
.meas tran vdout0_1ck184 FIND v(dout0_1) AT=1850.05n

* CHECK dout0_2 Vdout0_2ck184 = 1.8 time = 1850
.meas tran vdout0_2ck184 FIND v(dout0_2) AT=1850.05n

* CHECK dout0_3 Vdout0_3ck184 = 0 time = 1850
.meas tran vdout0_3ck184 FIND v(dout0_3) AT=1850.05n

* CHECK dout0_4 Vdout0_4ck184 = 0 time = 1850
.meas tran vdout0_4ck184 FIND v(dout0_4) AT=1850.05n

* CHECK dout0_5 Vdout0_5ck184 = 0 time = 1850
.meas tran vdout0_5ck184 FIND v(dout0_5) AT=1850.05n

* CHECK dout0_6 Vdout0_6ck184 = 0 time = 1850
.meas tran vdout0_6ck184 FIND v(dout0_6) AT=1850.05n

* CHECK dout0_7 Vdout0_7ck184 = 1.8 time = 1850
.meas tran vdout0_7ck184 FIND v(dout0_7) AT=1850.05n

* CHECK dout1_0 Vdout1_0ck185 = 0 time = 1860
.meas tran vdout1_0ck185 FIND v(dout1_0) AT=1860.05n

* CHECK dout1_1 Vdout1_1ck185 = 1.8 time = 1860
.meas tran vdout1_1ck185 FIND v(dout1_1) AT=1860.05n

* CHECK dout1_2 Vdout1_2ck185 = 0 time = 1860
.meas tran vdout1_2ck185 FIND v(dout1_2) AT=1860.05n

* CHECK dout1_3 Vdout1_3ck185 = 1.8 time = 1860
.meas tran vdout1_3ck185 FIND v(dout1_3) AT=1860.05n

* CHECK dout1_4 Vdout1_4ck185 = 0 time = 1860
.meas tran vdout1_4ck185 FIND v(dout1_4) AT=1860.05n

* CHECK dout1_5 Vdout1_5ck185 = 0 time = 1860
.meas tran vdout1_5ck185 FIND v(dout1_5) AT=1860.05n

* CHECK dout1_6 Vdout1_6ck185 = 1.8 time = 1860
.meas tran vdout1_6ck185 FIND v(dout1_6) AT=1860.05n

* CHECK dout1_7 Vdout1_7ck185 = 1.8 time = 1860
.meas tran vdout1_7ck185 FIND v(dout1_7) AT=1860.05n

* CHECK dout1_0 Vdout1_0ck187 = 0 time = 1880
.meas tran vdout1_0ck187 FIND v(dout1_0) AT=1880.05n

* CHECK dout1_1 Vdout1_1ck187 = 0 time = 1880
.meas tran vdout1_1ck187 FIND v(dout1_1) AT=1880.05n

* CHECK dout1_2 Vdout1_2ck187 = 1.8 time = 1880
.meas tran vdout1_2ck187 FIND v(dout1_2) AT=1880.05n

* CHECK dout1_3 Vdout1_3ck187 = 1.8 time = 1880
.meas tran vdout1_3ck187 FIND v(dout1_3) AT=1880.05n

* CHECK dout1_4 Vdout1_4ck187 = 1.8 time = 1880
.meas tran vdout1_4ck187 FIND v(dout1_4) AT=1880.05n

* CHECK dout1_5 Vdout1_5ck187 = 1.8 time = 1880
.meas tran vdout1_5ck187 FIND v(dout1_5) AT=1880.05n

* CHECK dout1_6 Vdout1_6ck187 = 0 time = 1880
.meas tran vdout1_6ck187 FIND v(dout1_6) AT=1880.05n

* CHECK dout1_7 Vdout1_7ck187 = 1.8 time = 1880
.meas tran vdout1_7ck187 FIND v(dout1_7) AT=1880.05n

* CHECK dout0_0 Vdout0_0ck188 = 0 time = 1890
.meas tran vdout0_0ck188 FIND v(dout0_0) AT=1890.05n

* CHECK dout0_1 Vdout0_1ck188 = 0 time = 1890
.meas tran vdout0_1ck188 FIND v(dout0_1) AT=1890.05n

* CHECK dout0_2 Vdout0_2ck188 = 1.8 time = 1890
.meas tran vdout0_2ck188 FIND v(dout0_2) AT=1890.05n

* CHECK dout0_3 Vdout0_3ck188 = 1.8 time = 1890
.meas tran vdout0_3ck188 FIND v(dout0_3) AT=1890.05n

* CHECK dout0_4 Vdout0_4ck188 = 1.8 time = 1890
.meas tran vdout0_4ck188 FIND v(dout0_4) AT=1890.05n

* CHECK dout0_5 Vdout0_5ck188 = 1.8 time = 1890
.meas tran vdout0_5ck188 FIND v(dout0_5) AT=1890.05n

* CHECK dout0_6 Vdout0_6ck188 = 0 time = 1890
.meas tran vdout0_6ck188 FIND v(dout0_6) AT=1890.05n

* CHECK dout0_7 Vdout0_7ck188 = 1.8 time = 1890
.meas tran vdout0_7ck188 FIND v(dout0_7) AT=1890.05n

* CHECK dout0_0 Vdout0_0ck190 = 1.8 time = 1910
.meas tran vdout0_0ck190 FIND v(dout0_0) AT=1910.05n

* CHECK dout0_1 Vdout0_1ck190 = 1.8 time = 1910
.meas tran vdout0_1ck190 FIND v(dout0_1) AT=1910.05n

* CHECK dout0_2 Vdout0_2ck190 = 1.8 time = 1910
.meas tran vdout0_2ck190 FIND v(dout0_2) AT=1910.05n

* CHECK dout0_3 Vdout0_3ck190 = 0 time = 1910
.meas tran vdout0_3ck190 FIND v(dout0_3) AT=1910.05n

* CHECK dout0_4 Vdout0_4ck190 = 0 time = 1910
.meas tran vdout0_4ck190 FIND v(dout0_4) AT=1910.05n

* CHECK dout0_5 Vdout0_5ck190 = 1.8 time = 1910
.meas tran vdout0_5ck190 FIND v(dout0_5) AT=1910.05n

* CHECK dout0_6 Vdout0_6ck190 = 0 time = 1910
.meas tran vdout0_6ck190 FIND v(dout0_6) AT=1910.05n

* CHECK dout0_7 Vdout0_7ck190 = 1.8 time = 1910
.meas tran vdout0_7ck190 FIND v(dout0_7) AT=1910.05n

* CHECK dout0_0 Vdout0_0ck191 = 0 time = 1920
.meas tran vdout0_0ck191 FIND v(dout0_0) AT=1920.05n

* CHECK dout0_1 Vdout0_1ck191 = 0 time = 1920
.meas tran vdout0_1ck191 FIND v(dout0_1) AT=1920.05n

* CHECK dout0_2 Vdout0_2ck191 = 1.8 time = 1920
.meas tran vdout0_2ck191 FIND v(dout0_2) AT=1920.05n

* CHECK dout0_3 Vdout0_3ck191 = 1.8 time = 1920
.meas tran vdout0_3ck191 FIND v(dout0_3) AT=1920.05n

* CHECK dout0_4 Vdout0_4ck191 = 1.8 time = 1920
.meas tran vdout0_4ck191 FIND v(dout0_4) AT=1920.05n

* CHECK dout0_5 Vdout0_5ck191 = 1.8 time = 1920
.meas tran vdout0_5ck191 FIND v(dout0_5) AT=1920.05n

* CHECK dout0_6 Vdout0_6ck191 = 0 time = 1920
.meas tran vdout0_6ck191 FIND v(dout0_6) AT=1920.05n

* CHECK dout0_7 Vdout0_7ck191 = 1.8 time = 1920
.meas tran vdout0_7ck191 FIND v(dout0_7) AT=1920.05n

* CHECK dout0_0 Vdout0_0ck192 = 1.8 time = 1930
.meas tran vdout0_0ck192 FIND v(dout0_0) AT=1930.05n

* CHECK dout0_1 Vdout0_1ck192 = 1.8 time = 1930
.meas tran vdout0_1ck192 FIND v(dout0_1) AT=1930.05n

* CHECK dout0_2 Vdout0_2ck192 = 1.8 time = 1930
.meas tran vdout0_2ck192 FIND v(dout0_2) AT=1930.05n

* CHECK dout0_3 Vdout0_3ck192 = 0 time = 1930
.meas tran vdout0_3ck192 FIND v(dout0_3) AT=1930.05n

* CHECK dout0_4 Vdout0_4ck192 = 0 time = 1930
.meas tran vdout0_4ck192 FIND v(dout0_4) AT=1930.05n

* CHECK dout0_5 Vdout0_5ck192 = 1.8 time = 1930
.meas tran vdout0_5ck192 FIND v(dout0_5) AT=1930.05n

* CHECK dout0_6 Vdout0_6ck192 = 0 time = 1930
.meas tran vdout0_6ck192 FIND v(dout0_6) AT=1930.05n

* CHECK dout0_7 Vdout0_7ck192 = 1.8 time = 1930
.meas tran vdout0_7ck192 FIND v(dout0_7) AT=1930.05n

* CHECK dout0_0 Vdout0_0ck195 = 1.8 time = 1960
.meas tran vdout0_0ck195 FIND v(dout0_0) AT=1960.05n

* CHECK dout0_1 Vdout0_1ck195 = 0 time = 1960
.meas tran vdout0_1ck195 FIND v(dout0_1) AT=1960.05n

* CHECK dout0_2 Vdout0_2ck195 = 1.8 time = 1960
.meas tran vdout0_2ck195 FIND v(dout0_2) AT=1960.05n

* CHECK dout0_3 Vdout0_3ck195 = 0 time = 1960
.meas tran vdout0_3ck195 FIND v(dout0_3) AT=1960.05n

* CHECK dout0_4 Vdout0_4ck195 = 0 time = 1960
.meas tran vdout0_4ck195 FIND v(dout0_4) AT=1960.05n

* CHECK dout0_5 Vdout0_5ck195 = 0 time = 1960
.meas tran vdout0_5ck195 FIND v(dout0_5) AT=1960.05n

* CHECK dout0_6 Vdout0_6ck195 = 0 time = 1960
.meas tran vdout0_6ck195 FIND v(dout0_6) AT=1960.05n

* CHECK dout0_7 Vdout0_7ck195 = 1.8 time = 1960
.meas tran vdout0_7ck195 FIND v(dout0_7) AT=1960.05n

* CHECK dout1_0 Vdout1_0ck195 = 1.8 time = 1960
.meas tran vdout1_0ck195 FIND v(dout1_0) AT=1960.05n

* CHECK dout1_1 Vdout1_1ck195 = 0 time = 1960
.meas tran vdout1_1ck195 FIND v(dout1_1) AT=1960.05n

* CHECK dout1_2 Vdout1_2ck195 = 1.8 time = 1960
.meas tran vdout1_2ck195 FIND v(dout1_2) AT=1960.05n

* CHECK dout1_3 Vdout1_3ck195 = 0 time = 1960
.meas tran vdout1_3ck195 FIND v(dout1_3) AT=1960.05n

* CHECK dout1_4 Vdout1_4ck195 = 0 time = 1960
.meas tran vdout1_4ck195 FIND v(dout1_4) AT=1960.05n

* CHECK dout1_5 Vdout1_5ck195 = 0 time = 1960
.meas tran vdout1_5ck195 FIND v(dout1_5) AT=1960.05n

* CHECK dout1_6 Vdout1_6ck195 = 0 time = 1960
.meas tran vdout1_6ck195 FIND v(dout1_6) AT=1960.05n

* CHECK dout1_7 Vdout1_7ck195 = 1.8 time = 1960
.meas tran vdout1_7ck195 FIND v(dout1_7) AT=1960.05n

* CHECK dout0_0 Vdout0_0ck196 = 0 time = 1970
.meas tran vdout0_0ck196 FIND v(dout0_0) AT=1970.05n

* CHECK dout0_1 Vdout0_1ck196 = 0 time = 1970
.meas tran vdout0_1ck196 FIND v(dout0_1) AT=1970.05n

* CHECK dout0_2 Vdout0_2ck196 = 1.8 time = 1970
.meas tran vdout0_2ck196 FIND v(dout0_2) AT=1970.05n

* CHECK dout0_3 Vdout0_3ck196 = 1.8 time = 1970
.meas tran vdout0_3ck196 FIND v(dout0_3) AT=1970.05n

* CHECK dout0_4 Vdout0_4ck196 = 1.8 time = 1970
.meas tran vdout0_4ck196 FIND v(dout0_4) AT=1970.05n

* CHECK dout0_5 Vdout0_5ck196 = 1.8 time = 1970
.meas tran vdout0_5ck196 FIND v(dout0_5) AT=1970.05n

* CHECK dout0_6 Vdout0_6ck196 = 0 time = 1970
.meas tran vdout0_6ck196 FIND v(dout0_6) AT=1970.05n

* CHECK dout0_7 Vdout0_7ck196 = 1.8 time = 1970
.meas tran vdout0_7ck196 FIND v(dout0_7) AT=1970.05n

* CHECK dout0_0 Vdout0_0ck197 = 1.8 time = 1980
.meas tran vdout0_0ck197 FIND v(dout0_0) AT=1980.05n

* CHECK dout0_1 Vdout0_1ck197 = 0 time = 1980
.meas tran vdout0_1ck197 FIND v(dout0_1) AT=1980.05n

* CHECK dout0_2 Vdout0_2ck197 = 1.8 time = 1980
.meas tran vdout0_2ck197 FIND v(dout0_2) AT=1980.05n

* CHECK dout0_3 Vdout0_3ck197 = 0 time = 1980
.meas tran vdout0_3ck197 FIND v(dout0_3) AT=1980.05n

* CHECK dout0_4 Vdout0_4ck197 = 1.8 time = 1980
.meas tran vdout0_4ck197 FIND v(dout0_4) AT=1980.05n

* CHECK dout0_5 Vdout0_5ck197 = 1.8 time = 1980
.meas tran vdout0_5ck197 FIND v(dout0_5) AT=1980.05n

* CHECK dout0_6 Vdout0_6ck197 = 0 time = 1980
.meas tran vdout0_6ck197 FIND v(dout0_6) AT=1980.05n

* CHECK dout0_7 Vdout0_7ck197 = 0 time = 1980
.meas tran vdout0_7ck197 FIND v(dout0_7) AT=1980.05n

* CHECK dout0_0 Vdout0_0ck198 = 1.8 time = 1990
.meas tran vdout0_0ck198 FIND v(dout0_0) AT=1990.05n

* CHECK dout0_1 Vdout0_1ck198 = 0 time = 1990
.meas tran vdout0_1ck198 FIND v(dout0_1) AT=1990.05n

* CHECK dout0_2 Vdout0_2ck198 = 1.8 time = 1990
.meas tran vdout0_2ck198 FIND v(dout0_2) AT=1990.05n

* CHECK dout0_3 Vdout0_3ck198 = 0 time = 1990
.meas tran vdout0_3ck198 FIND v(dout0_3) AT=1990.05n

* CHECK dout0_4 Vdout0_4ck198 = 0 time = 1990
.meas tran vdout0_4ck198 FIND v(dout0_4) AT=1990.05n

* CHECK dout0_5 Vdout0_5ck198 = 0 time = 1990
.meas tran vdout0_5ck198 FIND v(dout0_5) AT=1990.05n

* CHECK dout0_6 Vdout0_6ck198 = 0 time = 1990
.meas tran vdout0_6ck198 FIND v(dout0_6) AT=1990.05n

* CHECK dout0_7 Vdout0_7ck198 = 1.8 time = 1990
.meas tran vdout0_7ck198 FIND v(dout0_7) AT=1990.05n

* CHECK dout1_0 Vdout1_0ck198 = 1.8 time = 1990
.meas tran vdout1_0ck198 FIND v(dout1_0) AT=1990.05n

* CHECK dout1_1 Vdout1_1ck198 = 0 time = 1990
.meas tran vdout1_1ck198 FIND v(dout1_1) AT=1990.05n

* CHECK dout1_2 Vdout1_2ck198 = 1.8 time = 1990
.meas tran vdout1_2ck198 FIND v(dout1_2) AT=1990.05n

* CHECK dout1_3 Vdout1_3ck198 = 0 time = 1990
.meas tran vdout1_3ck198 FIND v(dout1_3) AT=1990.05n

* CHECK dout1_4 Vdout1_4ck198 = 1.8 time = 1990
.meas tran vdout1_4ck198 FIND v(dout1_4) AT=1990.05n

* CHECK dout1_5 Vdout1_5ck198 = 1.8 time = 1990
.meas tran vdout1_5ck198 FIND v(dout1_5) AT=1990.05n

* CHECK dout1_6 Vdout1_6ck198 = 0 time = 1990
.meas tran vdout1_6ck198 FIND v(dout1_6) AT=1990.05n

* CHECK dout1_7 Vdout1_7ck198 = 0 time = 1990
.meas tran vdout1_7ck198 FIND v(dout1_7) AT=1990.05n

* CHECK dout0_0 Vdout0_0ck200 = 1.8 time = 2010
.meas tran vdout0_0ck200 FIND v(dout0_0) AT=2010.05n

* CHECK dout0_1 Vdout0_1ck200 = 0 time = 2010
.meas tran vdout0_1ck200 FIND v(dout0_1) AT=2010.05n

* CHECK dout0_2 Vdout0_2ck200 = 0 time = 2010
.meas tran vdout0_2ck200 FIND v(dout0_2) AT=2010.05n

* CHECK dout0_3 Vdout0_3ck200 = 0 time = 2010
.meas tran vdout0_3ck200 FIND v(dout0_3) AT=2010.05n

* CHECK dout0_4 Vdout0_4ck200 = 0 time = 2010
.meas tran vdout0_4ck200 FIND v(dout0_4) AT=2010.05n

* CHECK dout0_5 Vdout0_5ck200 = 1.8 time = 2010
.meas tran vdout0_5ck200 FIND v(dout0_5) AT=2010.05n

* CHECK dout0_6 Vdout0_6ck200 = 1.8 time = 2010
.meas tran vdout0_6ck200 FIND v(dout0_6) AT=2010.05n

* CHECK dout0_7 Vdout0_7ck200 = 1.8 time = 2010
.meas tran vdout0_7ck200 FIND v(dout0_7) AT=2010.05n

* CHECK dout1_0 Vdout1_0ck200 = 1.8 time = 2010
.meas tran vdout1_0ck200 FIND v(dout1_0) AT=2010.05n

* CHECK dout1_1 Vdout1_1ck200 = 0 time = 2010
.meas tran vdout1_1ck200 FIND v(dout1_1) AT=2010.05n

* CHECK dout1_2 Vdout1_2ck200 = 1.8 time = 2010
.meas tran vdout1_2ck200 FIND v(dout1_2) AT=2010.05n

* CHECK dout1_3 Vdout1_3ck200 = 0 time = 2010
.meas tran vdout1_3ck200 FIND v(dout1_3) AT=2010.05n

* CHECK dout1_4 Vdout1_4ck200 = 0 time = 2010
.meas tran vdout1_4ck200 FIND v(dout1_4) AT=2010.05n

* CHECK dout1_5 Vdout1_5ck200 = 0 time = 2010
.meas tran vdout1_5ck200 FIND v(dout1_5) AT=2010.05n

* CHECK dout1_6 Vdout1_6ck200 = 0 time = 2010
.meas tran vdout1_6ck200 FIND v(dout1_6) AT=2010.05n

* CHECK dout1_7 Vdout1_7ck200 = 1.8 time = 2010
.meas tran vdout1_7ck200 FIND v(dout1_7) AT=2010.05n

* CHECK dout1_0 Vdout1_0ck201 = 1.8 time = 2020
.meas tran vdout1_0ck201 FIND v(dout1_0) AT=2020.05n

* CHECK dout1_1 Vdout1_1ck201 = 0 time = 2020
.meas tran vdout1_1ck201 FIND v(dout1_1) AT=2020.05n

* CHECK dout1_2 Vdout1_2ck201 = 0 time = 2020
.meas tran vdout1_2ck201 FIND v(dout1_2) AT=2020.05n

* CHECK dout1_3 Vdout1_3ck201 = 0 time = 2020
.meas tran vdout1_3ck201 FIND v(dout1_3) AT=2020.05n

* CHECK dout1_4 Vdout1_4ck201 = 0 time = 2020
.meas tran vdout1_4ck201 FIND v(dout1_4) AT=2020.05n

* CHECK dout1_5 Vdout1_5ck201 = 1.8 time = 2020
.meas tran vdout1_5ck201 FIND v(dout1_5) AT=2020.05n

* CHECK dout1_6 Vdout1_6ck201 = 1.8 time = 2020
.meas tran vdout1_6ck201 FIND v(dout1_6) AT=2020.05n

* CHECK dout1_7 Vdout1_7ck201 = 1.8 time = 2020
.meas tran vdout1_7ck201 FIND v(dout1_7) AT=2020.05n

* CHECK dout0_0 Vdout0_0ck203 = 0 time = 2040
.meas tran vdout0_0ck203 FIND v(dout0_0) AT=2040.05n

* CHECK dout0_1 Vdout0_1ck203 = 0 time = 2040
.meas tran vdout0_1ck203 FIND v(dout0_1) AT=2040.05n

* CHECK dout0_2 Vdout0_2ck203 = 1.8 time = 2040
.meas tran vdout0_2ck203 FIND v(dout0_2) AT=2040.05n

* CHECK dout0_3 Vdout0_3ck203 = 1.8 time = 2040
.meas tran vdout0_3ck203 FIND v(dout0_3) AT=2040.05n

* CHECK dout0_4 Vdout0_4ck203 = 1.8 time = 2040
.meas tran vdout0_4ck203 FIND v(dout0_4) AT=2040.05n

* CHECK dout0_5 Vdout0_5ck203 = 1.8 time = 2040
.meas tran vdout0_5ck203 FIND v(dout0_5) AT=2040.05n

* CHECK dout0_6 Vdout0_6ck203 = 0 time = 2040
.meas tran vdout0_6ck203 FIND v(dout0_6) AT=2040.05n

* CHECK dout0_7 Vdout0_7ck203 = 1.8 time = 2040
.meas tran vdout0_7ck203 FIND v(dout0_7) AT=2040.05n

* CHECK dout1_0 Vdout1_0ck203 = 1.8 time = 2040
.meas tran vdout1_0ck203 FIND v(dout1_0) AT=2040.05n

* CHECK dout1_1 Vdout1_1ck203 = 0 time = 2040
.meas tran vdout1_1ck203 FIND v(dout1_1) AT=2040.05n

* CHECK dout1_2 Vdout1_2ck203 = 0 time = 2040
.meas tran vdout1_2ck203 FIND v(dout1_2) AT=2040.05n

* CHECK dout1_3 Vdout1_3ck203 = 0 time = 2040
.meas tran vdout1_3ck203 FIND v(dout1_3) AT=2040.05n

* CHECK dout1_4 Vdout1_4ck203 = 0 time = 2040
.meas tran vdout1_4ck203 FIND v(dout1_4) AT=2040.05n

* CHECK dout1_5 Vdout1_5ck203 = 1.8 time = 2040
.meas tran vdout1_5ck203 FIND v(dout1_5) AT=2040.05n

* CHECK dout1_6 Vdout1_6ck203 = 1.8 time = 2040
.meas tran vdout1_6ck203 FIND v(dout1_6) AT=2040.05n

* CHECK dout1_7 Vdout1_7ck203 = 1.8 time = 2040
.meas tran vdout1_7ck203 FIND v(dout1_7) AT=2040.05n

* probe is used for hspice/xa, while plot is used in ngspice
.plot V(*)
.end

