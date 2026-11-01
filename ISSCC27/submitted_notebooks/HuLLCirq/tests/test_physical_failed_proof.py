"""Pass/fail proof dispatch QA; no circuit or EDA execution."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hullcirq import physical_tools, physical_workflow
from hullcirq.domain import DomainError


class PhysicalFailedProofTests(unittest.TestCase):
    def test_pass_and_failure_dispatch_to_the_same_complete_validator(self):
        args = ({'software_qa_fixture': True}, 'SOFTWARE_QA_RTL', {}, {}, {})
        with patch.object(physical_tools, '_validate_complete_layout_result') as verify:
            physical_tools.validate_layout_result(*args)
            verify.assert_called_once_with(*args, 'Passed')
            verify.reset_mock()
            physical_tools.validate_failed_layout_result(*args)
            verify.assert_called_once_with(*args, 'Failed')

    def test_failure_wrapper_cannot_accept_incomplete_or_passed_attempts(self):
        for execution, validation in (('Running', 'Failed'), ('Failed', 'Not Checked'),
                                      ('Completed', 'Passed'), ('Interrupted', 'Failed')):
            with self.subTest(execution=execution, validation=validation):
                with patch.object(physical_workflow, '_validate_physical_proof') as verify:
                    with self.assertRaises(DomainError):
                        physical_workflow.validate_failed_physical_proof(
                            {'execution_status': execution, 'validation_status': validation}, object())
                    verify.assert_not_called()

    def test_failed_attempt_is_verified_without_becoming_passed(self):
        run = {'execution_status': 'Completed', 'validation_status': 'Failed'}
        validator = object()
        with patch.object(physical_workflow, '_validate_physical_proof') as verify:
            physical_workflow.validate_failed_physical_proof(run, validator)
            verify.assert_called_once_with(run, validator, 'Failed')
        self.assertEqual(run, {'execution_status': 'Completed', 'validation_status': 'Failed'})


if __name__ == '__main__':
    unittest.main()
