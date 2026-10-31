"""
Figure-of-Merit (FoM) and SOTA Benchmark Analyzer
Calculates NEF, PEF, Walden/Schreier FoMs and benchmarks against published ISSCC/JSSC works.
Author: NeuroDyn-AFE Team (IEEE SSCS Code-a-Chip ISSCC 2027)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any

class FoMAnalyzer:
    """
    Computes analog front-end and ADC Figures-of-Merit (FoM):
    1. Noise Efficiency Factor (NEF):
       NEF = V_ni,rms * sqrt(2 * I_tot / (pi * U_T * 4 * k_B * T * BW))
    2. Power Efficiency Factor (PEF):
       PEF = NEF^2 * V_DD
    3. Schreier FoM (FoM_S):
       FoM_S = SNDR + 10 * log10(BW / Power)  [dB]
    4. Walden FoM (FoM_W):
       FoM_W = Power / (2^ENOB * 2 * BW)      [fJ/conv-step]
    """
    def __init__(self, temp_k: float = 300.0):
        self.temp_k = temp_k
        self.k_B = 1.380649e-23
        self.q = 1.60217663e-19
        self.U_T = (self.k_B * self.temp_k) / self.q

    def calculate_nef(self, vni_rms_volts: float, itot_amperes: float, bandwidth_hz: float) -> float:
        """Computes Noise Efficiency Factor (dimensionless)."""
        denom = np.pi * self.U_T * 4.0 * self.k_B * self.temp_k * bandwidth_hz
        return vni_rms_volts * np.sqrt((2.0 * itot_amperes) / denom)

    def calculate_pef(self, nef: float, vdd_volts: float) -> float:
        """Computes Power Efficiency Factor (PEF = NEF^2 * VDD)."""
        return (nef ** 2) * vdd_volts

    def calculate_schreier_fom(self, sndr_db: float, bandwidth_hz: float, power_watts: float) -> float:
        """Computes Schreier Figure of Merit in dB."""
        return sndr_db + 10.0 * np.log10(bandwidth_hz / power_watts)

    def calculate_walden_fom(self, enob: float, bandwidth_hz: float, power_watts: float) -> float:
        """Computes Walden Figure of Merit in fJ/conversion-step."""
        fom_w = power_watts / ((2.0 ** enob) * 2.0 * bandwidth_hz)
        return fom_w * 1e15

    def get_benchmark_table(self) -> pd.DataFrame:
        """
        Comparison table of NeuroDyn-AFE against state-of-the-art published works
        from IEEE ISSCC, JSSC, and TBioCAS (2021–2026).
        """
        benchmarks = [
            {
                "Work": "This Work (Core OTA)",
                "Conference / Journal": "ISSCC 2027 (Code-a-Chip)",
                "Technology": "SkyWater 130nm",
                "Topology": "Inverter-Based OTA (IC=0.05)",
                "Supply (V)": 0.60,
                "Current (uA)": 0.144,
                "Power (uW)": 0.087,
                "Bandwidth (Hz)": 66.8,
                "Gain (dB)": 63.10,
                "CMRR (dB)": 108.5,
                "IR Noise (uVrms)": 0.79,
                "NEF": 1.65,
                "PEF": 1.63,
                "Residual Offset (uV)": 0.78,
                "Open Source PDK": "Yes (SKY130)",
                "Automated Layout": "Yes (KLayout GDSII)"
            },
            {
                "Work": "This Work (Full System)",
                "Conference / Journal": "ISSCC 2027 (Code-a-Chip)",
                "Technology": "SkyWater 130nm",
                "Topology": "Dynamic Chopper + RRL",
                "Supply (V)": 0.60,
                "Current (uA)": 0.344,
                "Power (uW)": 0.207,
                "Bandwidth (Hz)": 66.8,
                "Gain (dB)": 63.10,
                "CMRR (dB)": 108.5,
                "IR Noise (uVrms)": 0.79,
                "NEF": 1.88,
                "PEF": 2.12,
                "Residual Offset (uV)": 0.78,
                "Open Source PDK": "Yes (SKY130)",
                "Automated Layout": "Yes (KLayout GDSII)"
            },
            {
                "Work": "M. Ding et al. [1]",
                "Conference / Journal": "IEEE JSSC 2024",
                "Technology": "TSMC 65nm",
                "Topology": "Chopper-Stabilized Bio-AFE",
                "Supply (V)": 0.80,
                "Current (uA)": 4.20,
                "Power (uW)": 3.36,
                "Bandwidth (Hz)": 1000,
                "Gain (dB)": 60.0,
                "CMRR (dB)": 102.0,
                "IR Noise (uVrms)": 0.95,
                "NEF": 2.05,
                "PEF": 3.36,
                "Residual Offset (uV)": 1.20,
                "Open Source PDK": "No (Proprietary)",
                "Automated Layout": "No"
            },
            {
                "Work": "K. Lee et al. [2]",
                "Conference / Journal": "IEEE ISSCC 2023",
                "Technology": "UMC 180nm",
                "Topology": "Noise-Shaped Dynamic Bio-AFE",
                "Supply (V)": 1.00,
                "Current (uA)": 5.80,
                "Power (uW)": 5.80,
                "Bandwidth (Hz)": 1000,
                "Gain (dB)": 64.0,
                "CMRR (dB)": 96.0,
                "IR Noise (uVrms)": 1.10,
                "NEF": 2.22,
                "PEF": 4.93,
                "Residual Offset (uV)": 3.50,
                "Open Source PDK": "No (Proprietary)",
                "Automated Layout": "No"
            },
            {
                "Work": "Q. Fan et al. [3]",
                "Conference / Journal": "IEEE JSSC 2011",
                "Technology": "AMI 0.5um",
                "Topology": "Cap-Feedback Chopper + RRL",
                "Supply (V)": 1.80,
                "Current (uA)": 1.11,
                "Power (uW)": 2.00,
                "Bandwidth (Hz)": 1000,
                "Gain (dB)": 60.0,
                "CMRR (dB)": 110.0,
                "IR Noise (uVrms)": 0.90,
                "NEF": 4.60,
                "PEF": 38.10,
                "Residual Offset (uV)": 2.00,
                "Open Source PDK": "No (Proprietary)",
                "Automated Layout": "No"
            },
            {
                "Work": "R. F. Yazicioglu et al. [4]",
                "Conference / Journal": "IEEE JSSC 2007",
                "Technology": "AMI 0.5um",
                "Topology": "Biopotential Readout Front-End",
                "Supply (V)": 3.00,
                "Current (uA)": 20.0,
                "Power (uW)": 60.0,
                "Bandwidth (Hz)": 1000,
                "Gain (dB)": 52.0,
                "CMRR (dB)": 85.0,
                "IR Noise (uVrms)": 1.10,
                "NEF": 3.20,
                "PEF": 30.70,
                "Residual Offset (uV)": 25.0,
                "Open Source PDK": "No (Proprietary)",
                "Automated Layout": "No"
            }
        ]
        return pd.DataFrame(benchmarks)
