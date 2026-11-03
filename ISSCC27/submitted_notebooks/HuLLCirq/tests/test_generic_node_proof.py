"""Saved S06 proof faults; pure fixtures, no circuit tools or live project."""
import copy
import unittest

from hullcirq.domain import DomainError
from hullcirq.workflow import validate_generic_simulation_proof
from hullcirq.verification import content_hash
from hullcirq.generic_verification import build_cycle_plan
from test_generic_verification import interface, contract, runtime


class GenericNodeProofTests(unittest.TestCase):
    def proof(self):
        plan = build_cycle_plan(interface(), contract())
        text = "software-fixture-netlist-not-a-circuit"
        result = {key: copy.deepcopy(plan[key]) for key in
                  ('vector_hash', 'testbench_sha256', 'reference_trace_hash', 'vector_count', 'coverage')}
        result.update(rtl_sha256=content_hash(text), validation_status='Passed', executed=True,
                      exit_code=0, stdout=runtime(plan), stderr='', commands=[
                          {'executed': True, 'status': 'Completed', 'exit_code': 0,
                           'stdout': runtime(plan) if i == 2 else '', 'stderr': ''} for i in range(3)])
        return {'netlist': text, 'netlist_sha256': content_hash(text), 'verification_plan': plan, 'checks': result}

    def test_complete_bound_samples_pass_without_execution(self):
        validate_generic_simulation_proof(self.proof())

    def test_missing_samples_changed_hashes_commands_and_error_diagnostics_reject(self):
        def marker_only(run):
            run['checks']['stdout'] = run['checks']['commands'][-1]['stdout'] = runtime(run['verification_plan']).splitlines()[-1] + '\n'
        mutations = [marker_only,
            lambda r: r['checks'].update(rtl_sha256='changed'),
            lambda r: r['checks'].update(vector_hash='changed'),
            lambda r: r['checks'].update(testbench_sha256='changed'),
            lambda r: r.update(netlist='changed'),
            lambda r: r['checks']['commands'].pop(),
            lambda r: r['checks']['commands'][0].update(exit_code=True),
            lambda r: r['checks']['commands'][1].update(executed=False),
            lambda r: r['checks']['commands'][-1].update(stderr='ERROR: simulator rejected input'),
            lambda r: r['checks'].update(stderr='FATAL: invalid model')]
        for mutate in mutations:
            value = self.proof(); mutate(value)
            with self.subTest(mutation=mutate), self.assertRaises(DomainError):
                validate_generic_simulation_proof(value)

    def test_historical_kinds_remain_unchanged(self):
        validate_generic_simulation_proof({'verification_plan': {'kind': 'int8_mac_stream'}})
        validate_generic_simulation_proof({'verification_plan': None})
