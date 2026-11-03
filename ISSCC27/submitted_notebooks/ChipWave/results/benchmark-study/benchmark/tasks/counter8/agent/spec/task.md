# counter8

Implement benchmark_counter with 8-bit unsigned count/load_value.
Active-low asynchronous reset immediately clears count and overflow. At each
rising edge, load has priority over en: load sets count=load_value and overflow=0.
Otherwise en increments count modulo 2**8, with overflow=1 exactly on a wrap.
With neither load nor en, hold count and clear overflow. No extra clock latency.

Use the fixed top-level port names and widths in interface.json. Develop with
`python3 tools/check.py`. Deliver synthesizable RTL under rtl/. Independent
final vectors/reference and scoring are outside your workspace. Do not alter
the task/checker, invoke extra models, or read other trials. The task's area
limit is installed after reference physical calibration, before evaluation.
