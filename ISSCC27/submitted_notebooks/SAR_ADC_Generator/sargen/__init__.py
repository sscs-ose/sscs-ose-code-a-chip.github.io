"""sargen: specification-driven SAR ADC generator for the open-source SKY130 PDK.

Pipeline: spec -> PDK characterization -> sizing -> netlists -> ngspice
simulation -> metrics (ENOB, INL/DNL, histogram, FFT) -> animated explanation.
"""

from .spec import SarSpec

__all__ = ["SarSpec"]
__version__ = "0.1.0"
