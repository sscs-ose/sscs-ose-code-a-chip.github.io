// Shared Kyber parameters + zeta ROM (single definition for RTL and TB)
package kyber_pkg;
    parameter int KYBER_Q    = 3329;
    parameter int KYBER_N    = 256;
    parameter int KYBER_QINV = 62209; // -1/q mod 2^16

    // FIPS 203 Appendix A: zeta^BitRev7(i) mod q in the normal domain.
    // Previous revisions stored the CRYSTALS-Kyber Montgomery-domain table
    // here, while the engine/testbench treated it as a normal-domain oracle.
    function automatic logic [15:0] kyber_zeta(input logic [6:0] idx);
        case (idx)
            7'd0: kyber_zeta = 16'd1;       7'd1: kyber_zeta = 16'd1729;
            7'd2: kyber_zeta = 16'd2580;    7'd3: kyber_zeta = 16'd3289;
            7'd4: kyber_zeta = 16'd2642;    7'd5: kyber_zeta = 16'd630;
            7'd6: kyber_zeta = 16'd1897;    7'd7: kyber_zeta = 16'd848;
            7'd8: kyber_zeta = 16'd1062;    7'd9: kyber_zeta = 16'd1919;
            7'd10: kyber_zeta = 16'd193;    7'd11: kyber_zeta = 16'd797;
            7'd12: kyber_zeta = 16'd2786;   7'd13: kyber_zeta = 16'd3260;
            7'd14: kyber_zeta = 16'd569;    7'd15: kyber_zeta = 16'd1746;
            7'd16: kyber_zeta = 16'd296;    7'd17: kyber_zeta = 16'd2447;
            7'd18: kyber_zeta = 16'd1339;   7'd19: kyber_zeta = 16'd1476;
            7'd20: kyber_zeta = 16'd3046;   7'd21: kyber_zeta = 16'd56;
            7'd22: kyber_zeta = 16'd2240;   7'd23: kyber_zeta = 16'd1333;
            7'd24: kyber_zeta = 16'd1426;   7'd25: kyber_zeta = 16'd2094;
            7'd26: kyber_zeta = 16'd535;    7'd27: kyber_zeta = 16'd2882;
            7'd28: kyber_zeta = 16'd2393;   7'd29: kyber_zeta = 16'd2879;
            7'd30: kyber_zeta = 16'd1974;   7'd31: kyber_zeta = 16'd821;
            7'd32: kyber_zeta = 16'd289;    7'd33: kyber_zeta = 16'd331;
            7'd34: kyber_zeta = 16'd3253;   7'd35: kyber_zeta = 16'd1756;
            7'd36: kyber_zeta = 16'd1197;   7'd37: kyber_zeta = 16'd2304;
            7'd38: kyber_zeta = 16'd2277;   7'd39: kyber_zeta = 16'd2055;
            7'd40: kyber_zeta = 16'd650;    7'd41: kyber_zeta = 16'd1977;
            7'd42: kyber_zeta = 16'd2513;   7'd43: kyber_zeta = 16'd632;
            7'd44: kyber_zeta = 16'd2865;   7'd45: kyber_zeta = 16'd33;
            7'd46: kyber_zeta = 16'd1320;   7'd47: kyber_zeta = 16'd1915;
            7'd48: kyber_zeta = 16'd2319;   7'd49: kyber_zeta = 16'd1435;
            7'd50: kyber_zeta = 16'd807;    7'd51: kyber_zeta = 16'd452;
            7'd52: kyber_zeta = 16'd1438;   7'd53: kyber_zeta = 16'd2868;
            7'd54: kyber_zeta = 16'd1534;   7'd55: kyber_zeta = 16'd2402;
            7'd56: kyber_zeta = 16'd2647;   7'd57: kyber_zeta = 16'd2617;
            7'd58: kyber_zeta = 16'd1481;   7'd59: kyber_zeta = 16'd648;
            7'd60: kyber_zeta = 16'd2474;   7'd61: kyber_zeta = 16'd3110;
            7'd62: kyber_zeta = 16'd1227;   7'd63: kyber_zeta = 16'd910;
            7'd64: kyber_zeta = 16'd17;     7'd65: kyber_zeta = 16'd2761;
            7'd66: kyber_zeta = 16'd583;    7'd67: kyber_zeta = 16'd2649;
            7'd68: kyber_zeta = 16'd1637;   7'd69: kyber_zeta = 16'd723;
            7'd70: kyber_zeta = 16'd2288;   7'd71: kyber_zeta = 16'd1100;
            7'd72: kyber_zeta = 16'd1409;   7'd73: kyber_zeta = 16'd2662;
            7'd74: kyber_zeta = 16'd3281;   7'd75: kyber_zeta = 16'd233;
            7'd76: kyber_zeta = 16'd756;    7'd77: kyber_zeta = 16'd2156;
            7'd78: kyber_zeta = 16'd3015;   7'd79: kyber_zeta = 16'd3050;
            7'd80: kyber_zeta = 16'd1703;   7'd81: kyber_zeta = 16'd1651;
            7'd82: kyber_zeta = 16'd2789;   7'd83: kyber_zeta = 16'd1789;
            7'd84: kyber_zeta = 16'd1847;   7'd85: kyber_zeta = 16'd952;
            7'd86: kyber_zeta = 16'd1461;   7'd87: kyber_zeta = 16'd2687;
            7'd88: kyber_zeta = 16'd939;    7'd89: kyber_zeta = 16'd2308;
            7'd90: kyber_zeta = 16'd2437;   7'd91: kyber_zeta = 16'd2388;
            7'd92: kyber_zeta = 16'd733;    7'd93: kyber_zeta = 16'd2337;
            7'd94: kyber_zeta = 16'd268;    7'd95: kyber_zeta = 16'd641;
            7'd96: kyber_zeta = 16'd1584;   7'd97: kyber_zeta = 16'd2298;
            7'd98: kyber_zeta = 16'd2037;   7'd99: kyber_zeta = 16'd3220;
            7'd100: kyber_zeta = 16'd375;   7'd101: kyber_zeta = 16'd2549;
            7'd102: kyber_zeta = 16'd2090;  7'd103: kyber_zeta = 16'd1645;
            7'd104: kyber_zeta = 16'd1063;  7'd105: kyber_zeta = 16'd319;
            7'd106: kyber_zeta = 16'd2773;  7'd107: kyber_zeta = 16'd757;
            7'd108: kyber_zeta = 16'd2099;  7'd109: kyber_zeta = 16'd561;
            7'd110: kyber_zeta = 16'd2466;  7'd111: kyber_zeta = 16'd2594;
            7'd112: kyber_zeta = 16'd2804;  7'd113: kyber_zeta = 16'd1092;
            7'd114: kyber_zeta = 16'd403;   7'd115: kyber_zeta = 16'd1026;
            7'd116: kyber_zeta = 16'd1143;  7'd117: kyber_zeta = 16'd2150;
            7'd118: kyber_zeta = 16'd2775;  7'd119: kyber_zeta = 16'd886;
            7'd120: kyber_zeta = 16'd1722;  7'd121: kyber_zeta = 16'd1212;
            7'd122: kyber_zeta = 16'd1874;  7'd123: kyber_zeta = 16'd1029;
            7'd124: kyber_zeta = 16'd2110;  7'd125: kyber_zeta = 16'd2935;
            7'd126: kyber_zeta = 16'd885;   7'd127: kyber_zeta = 16'd2154;
            default: kyber_zeta = 16'd0;
        endcase
    endfunction
endpackage
