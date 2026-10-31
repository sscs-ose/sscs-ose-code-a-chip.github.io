"""Audit missing SPEF drivers; exempt only proven constant-output cells."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from study_protocol import digest


def group(text, pattern):
    match = re.search(pattern, text)
    if not match: raise ValueError('Expected Liberty group was not found')
    depth = 1; quoted = False; escaped = False
    for end in range(match.end(), len(text)):
        char = text[end]
        if escaped: escaped = False; continue
        if char == '\\': escaped = True; continue
        if char == '"': quoted = not quoted
        if not quoted:
            if char == '{': depth += 1
            elif char == '}':
                depth -= 1
                if not depth: return text[match.end():end]
    raise ValueError('Unclosed Liberty group')


def audit(report, netlist, library):
    report, netlist, library = map(Path, (report, netlist, library))
    text = report.read_text()
    header = re.search(r'Found (\d+) unannotated drivers\.\s*\n', text)
    partial = re.search(r'Found (\d+) partially unannotated drivers\.', text)
    if not header or not partial or partial.start() < header.end():
        raise ValueError('Missing complete parasitic annotation report')
    names = [line.strip() for line in text[header.end():partial.start()].splitlines() if line.strip()]
    if len(names) != int(header[1]) or len(set(names)) != len(names):
        raise ValueError('Missing-driver list does not match its reported population')
    cell_name = 'sky130_fd_sc_hd__conb_1'
    liberty_cell = group(library.read_text(), r'\bcell\s*\(\s*"?' + cell_name + r'"?\s*\)\s*\{')
    functions = {}
    for port in ('HI', 'LO'):
        pin = group(liberty_cell, r'\bpin\s*\(\s*"?' + port + r'"?\s*\)\s*\{')
        direction = re.search(r'\bdirection\s*:\s*"?(\w+)"?\s*;', pin)
        function = re.search(r'\bfunction\s*:\s*"([01])"\s*;', pin)
        if direction and direction[1] == 'output' and function:
            functions[port] = function[1]
    netlist_text = netlist.read_text()
    instances = {match[2].lstrip('\\'): {'cell': match[1], 'connections': match[3]} for match in
                 re.finditer(r'(?ms)^\s*(sky130_fd_sc_hd__\w+)\s+(\S+)\s*\((.*?)\);', netlist_text)}
    references = Counter(re.findall(r'[A-Za-z_$][A-Za-z0-9_$]*', netlist_text))
    exemptions = []; non_nets = []; unloaded = []; unknown = []; liberty_text = library.read_text()
    output_cache = {}
    for name in names:
        instance, separator, port = name.rpartition('/')
        actual = instances.get(instance)
        if separator and actual and actual['cell'] == cell_name and port in functions:
            exemptions.append({'driver': name, 'cell': cell_name, 'port': port,
                               'liberty_function': functions[port],
                               'connected_in_netlist': bool(re.search(r'\.' + re.escape(port) + r'\s*\(', actual['connections']))})
        elif separator and actual:
            connection = re.search(r'\.' + re.escape(port) + r'\s*\(\s*([^)]*)\)', actual['connections'])
            net = connection[1].strip() if connection else ''
            single_pin = (bool(re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', net)) and references[net] == 2 and
                          bool(re.search(r'(?m)^\s*wire\s+' + re.escape(net) + r'\s*;\s*$', netlist_text)))
            if net and not single_pin:
                unknown.append(name); continue
            key = actual['cell'], port
            if key not in output_cache:
                cell = group(liberty_text, r'\bcell\s*\(\s*"?' + re.escape(key[0]) + r'"?\s*\)\s*\{')
                pin = group(cell, r'\bpin\s*\(\s*"?' + re.escape(port) + r'"?\s*\)\s*\{')
                output_cache[key] = bool(re.search(r'\bdirection\s*:\s*"?output"?\s*;', pin))
            if output_cache[key]:
                if not net:
                    non_nets.append({'driver': name, 'cell': actual['cell'], 'port': port,
                                     'proof': 'Liberty output pin has no connected net in the delivered Verilog; no signal-net RC exists to annotate'})
                else:
                    unloaded.append({'driver':name,'cell':actual['cell'],'port':port,'net':net,
                                     'source_identifier_occurrences':references[net],
                                     'proof':'Exactly one wire declaration and one output-pin connection; no other reference, primary port, assignment or load exists'})
            else:
                unknown.append(name)
        else:
            unknown.append(name)
    return {'passed': not unknown and int(partial[1]) == 0,
            'unannotated_drivers': len(names), 'partially_unannotated_drivers': int(partial[1]),
            'constant_exemptions': exemptions, 'unconnected_output_exclusions': non_nets,
            'unloaded_output_exclusions': unloaded,
            'eligible_unannotated_drivers': unknown,
            'report_sha256': digest(report), 'netlist_sha256': digest(netlist), 'liberty_sha256': digest(library),
            'scope': 'Loaded signal nets require RC. Missing drivers must be proven constant outputs, unconnected outputs or isolated single-pin output wires with no load; all other missing or partial signal parasitics reject measurement qualification'}
