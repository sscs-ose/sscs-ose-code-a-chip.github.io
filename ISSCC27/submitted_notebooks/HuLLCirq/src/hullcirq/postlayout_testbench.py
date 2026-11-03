"""Timed adaptation of the saved GUI job; never supplies a new test job."""
from __future__ import annotations
from decimal import Decimal
import math

from .domain import DomainError
from .verification import content_hash, object_hash


def require(condition, message):
    if not condition:
        raise DomainError('postlayout_testbench_unsupported', message, 422)


def timed_testbench(plan, settings):
    """Keep every original load/config/expected-value assertion.

    A new, separately hashed adapter gives the old unitless test a real clock.
    Top outputs are sampled before the next receiver edge. No claim is made
    that the former RTL module-boundary monitor survived physical flattening.
    """
    require(type(plan) is dict and plan.get('kind') == 'global-original-matrix-v1',
            'Use the original saved whole-design verification plan.')
    text = plan.get('testbench')
    require(type(text) is str and content_hash(text) == plan.get('testbench_sha256'),
            'The original testbench must match its frozen plan hash.')
    period = settings.get('clock_period_ns')
    require(type(period) in (int, float) and math.isfinite(period) and period > 2,
            'Use a finite inherited clock period greater than the 1 ns sample margin.')
    require(settings.get('clock_name') == 'clk' and settings.get('reset_name') == 'rst'
            and settings.get('reset_active') == 'high' and settings.get('reset_kind') == 'synchronous',
            'The first timed adapter supports the saved single-clock synchronous active-high reset contract.')
    require(text.count('  always #5 clk=~clk;') == 1
            and text.count('  always @(posedge clk) begin') == 1
            and text.count('  initial begin #200000;') == 1
            and text.count('endmodule') == 1 and '`timescale' not in text,
            'Unknown base testbench timing syntax is not silently rewritten.')
    clock = Decimal(str(period))
    half, sample = clock / 2, clock / 2 - 1
    text = '`timescale 1ns/1ps\n' + text
    text = text.replace('  always #5 clk=~clk;', f'  always #{half:f} clk=~clk;', 1)
    text = text.replace('  always @(posedge clk) begin',
                        f'  always @(negedge clk) begin\n    #{sample:f}; // 1 ns before the external receiving edge', 1)
    text = text.replace('  initial begin #200000;', f'  initial begin #{clock * 20000:f};', 1)
    annotation = '''  initial begin
    $display("HULLCIRQ_S14_ANNOTATION_BEGIN");
    $sdf_annotate("input.sdf", dut);
    $display("HULLCIRQ_S14_ANNOTATION_END");
    $dumpfile("simulation.vcd");
    $dumpvars(0, clk, rst, config_data, config_data_valid, config_data_ready,
      load_data, load_data_valid, load_data_ready, output_data,
      output_data_valid, output_data_ready, busy, job_done);
  end
'''
    text = text.replace('endmodule', annotation + 'endmodule', 1)
    return text, {
        'kind': 'hullcirq-original-job-timed-top-adapter-v1',
        'origin': 'development_assistant_timing_adapter_not_RTL_or_model_generation',
        'original_plan_sha256': object_hash(plan),
        'original_testbench_sha256': plan['testbench_sha256'],
        'vector_hash': plan['vector_hash'],
        'public_boundary_vector_hash': plan['public_boundary_vector_hash'],
        'timed_testbench_sha256': content_hash(text),
        'timescale': '1ns/1ps', 'clock_period_ns': period,
        'input_drive': 'inherited_negedge_recipe',
        'output_sample': '1_ns_before_external_posedge',
        'watchdog_cycles': 20000,
        'scope': 'one_original_GUI_job_external_transactions_and_timing_not_all_former_module_boundaries',
        'original_job_values_changed': False,
        'original_expected_outputs_changed': False,
    }


def timed_testbench_v2(plan, settings):
    """Preserve the original counter/backpressure phase from the first edge.

    Version 1 starts its negedge+margin checker at 74 ns for a 50 ns clock,
    missing the first receiving edge at 25 ns. Version 2 samples at 24 ns and
    then every 50 ns, retaining each original logical cycle's checker and ready
    pattern. Values, assertions and the original stimulus tasks are unchanged.
    Historical v1 adapters and records are never rewritten by this function.
    """
    text, v1 = timed_testbench(plan, settings)
    clock = Decimal(str(settings['clock_period_ns']))
    first = clock / 2 - 1
    begin = (f'  always @(negedge clk) begin\n'
             f'    #{first:f}; // 1 ns before the external receiving edge\n')
    end = '  end\n  initial begin\n    expected[0]'
    require(text.count(begin) == 1 and text.count(end) == 1,
            'Unknown original checker boundary cannot be phase-adapted.')
    start = text.index(begin)
    stop = text.index(end, start)
    body = text[start + len(begin):stop]
    replacement = (f'  initial begin\n'
                   f'    #{first:f}; // 1 ns before the first external receiving edge\n'
                   f'    forever begin\n{body}'
                   f'      #{clock:f}; // one original logical cycle\n'
                   f'    end\n')
    text = text[:start] + replacement + text[stop:]
    return text, {
        **v1,
        'kind': 'hullcirq-original-job-timed-top-adapter-v2',
        'timed_testbench_sha256': content_hash(text),
        'output_sample': '1_ns_before_each_external_posedge_including_the_first',
        'checker_first_sample_ns': float(first),
        'checker_period_ns': settings['clock_period_ns'],
        'original_counter_and_backpressure_cycle_phase_preserved': True,
        'v1_phase_difference': 'v1_first_negedge_plus_margin_omits_the_first_receiving_edge_counter_update',
        'v1_candidate_sha256': v1['timed_testbench_sha256'],
    }
