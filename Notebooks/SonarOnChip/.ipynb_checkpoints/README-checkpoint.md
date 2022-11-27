# IEEE SSCS Open-Source Ecosystem “Code-a-Chip”: SonarOnChip design

(More info here: https://github.com/HALxmont/SonarOnChip8)


### Details of the Project
The Sonar On Chip project wants to implements a digital system for signal processing to capture and process acoustics signals from 36 MEMS microphones with an extended frequency range up to 85 kHz (low ultrasonic band). The system itself is a part of the Caravel harness and can be configured and managed from the Caravel using Wishbone bus.

The principle of operation of the system is the following:

Each, pulse density modulated (PDM), the microphone signal is processed individually using a separate channel, which demodulates PDM data recovering PCM (Pulse Code Modulation) samples, filters out audible frequencies, detects the envelope, and compare its value to a configurable threshold. The result of the comparison triggers an interrupt and stops a free-running timer configured in a capture mode. The timers are cleared synchronously on all channels and the value of each timer can be read by the RISC-V processor. The captured values of the 36 timers can be post-processed on the RISC-V processor and the direction of arrival of the wavefront can be estimated.


### GDS output at the end of the flow

<img src="images/GDS.png" width="800" height="500">

## Team Members and acknowledgment

| Name | Affiliation | IEEE Member | SSCS Member | Contributions |
| --- | --- | --- | --- | --- |
| Mauricio Montanares (PhD Student) | University of Concepción | No | No | Team Leader, high level Python scripting/automation, RTL code development, RTL/GL verification, PD, documentation and python-colab enviroment port. |
| Krzysztof Herman (DSc, academic teacher/researcher) | University of the Bío-Bío | Yes | No | RTL code development, RTL/GL verification, physical design, documentation. |
| Maximiliano Cerda (Undergraduate student) | University of the Bío-Bío | No | No | high level Matlab analysis, RLT code development, documentation. |
| Luis Osses (Automation Engineer) | University of the Bío-Bío | No | No | high level Matlab analysis, RLT code development, documentation. |