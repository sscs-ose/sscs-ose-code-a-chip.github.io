from pathlib import Path

class ngspice_result:
    def __init__(self, test_bench: "xschem_testbench", 
                 output_path: Path, raw_output_path: Path) -> None:
        self.test_bench = test_bench
        self.path = test_bench.result_path
        self.output_path = output_path
        self.raw_output_path = raw_output_path
    
    def print_summary(self):
        print(f'{self.test_bench} Test Bench')
        print(f'  path: {self.path}')
        print(f'  output: {self.output_path}')
        print(f'  raw output: {self.raw_output_path}')