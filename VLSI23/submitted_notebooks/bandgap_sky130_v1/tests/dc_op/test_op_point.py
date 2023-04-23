import pytest, os
from pathlib import Path
from spyci import spyci
from vlsirtools.spice import ngspice
import pandas as pd
#from rawread import rawread

from viper.testing.PerformanceTest import PerformanceTest
from viper.simulators.SimResult import SimResult

@pytest.fixture(scope="module")
def performance_test(request: pytest.FixtureRequest) -> PerformanceTest:

    try:
        return PerformanceTest.read_package(request.module.__package__)
    except:
        return PerformanceTest.read_directory(
            Path(os.environ["WORKSPACE_DIR"]) / "tests" / "dc_op"
        )

@pytest.fixture(scope="module")
def sim_result(performance_test: PerformanceTest) -> SimResult:
    return performance_test.sim_result

@pytest.fixture(scope="module")
def raw_op_result(sim_result: SimResult) -> pd.DataFrame:
    raw_result = spyci.load_raw(sim_result.raw_output_filepath)
    
    pd.DataFrame()
    return performance_test.sim_result

def test_result_complete(sim_result: SimResult):
    print(f"output_filepath: {sim_result.output_filepath}")
    assert sim_result.output_filepath.exists()
    assert sim_result.raw_output_filepath.exists()



def test_open_raw(sim_result: SimResult):
    raw_result = spyci.load_raw(sim_result.raw_output_filepath)
    # with open(sim_result.raw_output_filepath) as raw_file:
    #     raw_result = ngspice.parse_nutbin(raw_file)
    vdd = raw_result["values"][0][0].real 

#def test_vdsat(dcop_result):
    # data = spyci.load_raw(str(dcop_result))
    #data = rawread(str(dcop_result))
    #assert isinstance(dcop_result, ngspice_result)
 #   assert 1 < 2
    #assert V_bg < 1.05


# if __name__ == "__main__":
#     test_vdsat(Path("/workspaces/bandgapReferenceCircuit/tests/dc_op/simulation/tsmc_bandgap_real_op.raw"))