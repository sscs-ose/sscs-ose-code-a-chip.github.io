// ML-KEM-512 parameters for partial RTL work.
// Source of truth: NIST FIPS 203. This package is only a parameter/primitive
// layer and does not claim full Encaps/Decaps compliance by itself.
package mlkem512_pkg;
    parameter int MLKEM_N = 256;
    parameter int MLKEM_Q = 3329;

    parameter int MLKEM512_K = 2;
    parameter int MLKEM512_ETA1 = 3;
    parameter int MLKEM512_ETA2 = 2;
    parameter int MLKEM512_DU = 10;
    parameter int MLKEM512_DV = 4;

    parameter int MLKEM512_EK_BYTES = 800;
    parameter int MLKEM512_DK_BYTES = 1632;
    parameter int MLKEM512_CT_BYTES = 768;
    parameter int MLKEM_SS_BYTES = 32;
endpackage

