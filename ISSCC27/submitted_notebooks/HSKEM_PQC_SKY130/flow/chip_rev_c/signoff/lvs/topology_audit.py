#!/usr/bin/env python3
"""Audit top-level connectivity correspondence between two SPICE/CDL netlists.

The default audit compares name-independent endpoint signatures. With a DEF
and the original extracted placement comments, it pairs instances by exact
master/placement/orientation, then child pins by name. This is diagnostic only:
it does not repair a netlist or invoke extraction or LVS.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path


TOP = "trustedge_asic_core"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_def_endpoint_membership(mapped_report_path, def_path, output_path):
    """Check DEF's declared endpoints only. This is not a routed-wire check."""
    review = json.loads(mapped_report_path.read_text())
    targets = review["one_ended_on_differing_nets"]
    canonical = lambda token: token.replace("\\", "")
    wanted = {canonical(row["reference_net"]) for row in targets}
    connections = defaultdict(set)
    in_nets = False
    current_net = None
    with def_path.open(encoding="utf-8") as stream:
        for line in stream:
            text = line.strip()
            if text.startswith("NETS "):
                in_nets = True
                continue
            if text == "END NETS":
                break
            if not in_nets:
                continue
            if text.startswith("- "):
                net = canonical(text.split()[1])
                current_net = net if net in wanted else None
            if current_net:
                # Endpoint records precede + USE/ROUTED. Coordinates cannot
                # match the named-instance/pin targets, but exclude them too.
                endpoint_text = text.split("+", 1)[0]
                for instance, pin in re.findall(r"\(\s+(\S+)\s+(\S+)\s+\)", endpoint_text):
                    connections[current_net].add((canonical(instance), canonical(pin)))
                if "+" in text:
                    current_net = None
    rows = []
    for row in targets:
        instance = canonical(row["reference_instance"])[1:]
        pin = canonical(row["pin"])
        net = canonical(row["reference_net"])
        rows.append({**row, "def_declares_expected_connection": (instance, pin) in connections[net]})
    result = {
        "status": "DECLARED_ENDPOINTS_VERIFIED" if all(row["def_declares_expected_connection"] for row in rows) else "DECLARED_ENDPOINT_MISMATCH",
        "scope": "DEF logical endpoint membership only, not physical wire continuity",
        "physical_flow_launch": 0, "netlist_modified": 0,
        "target_count": len(rows), "verified_count": sum(row["def_declares_expected_connection"] for row in rows),
        "inputs": {str(path): sha256(path) for path in [mapped_report_path, def_path]}, "rows": rows,
    }
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"DEF_DECLARED_ENDPOINTS={result['status']}|verified={result['verified_count']}|targets={len(rows)}")


def read_lef_sizes(path):
    sizes = {}
    macro = None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            words = line.split()
            if len(words) == 2 and words[0] == "MACRO":
                macro = words[1].lower()
            elif macro and words[:1] == ["ORIGIN"]:
                if Decimal(words[1]) or Decimal(words[2]):
                    raise RuntimeError(f"nonzero LEF origin not supported: {macro}")
            elif macro and words[:1] == ["SIZE"]:
                sizes[macro] = (int(Decimal(words[1]) * 1000), int(Decimal(words[3]) * 1000))
            elif macro and words == ["END", macro]:
                macro = None
    return sizes


def read_placements(path, instances):
    placements = {}
    pending = None
    in_top = False
    pattern = re.compile(r"^\* cell instance \S+ (\S+) \*1 ([^,]+),(\S+)\s*$")
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.upper().startswith(".SUBCKT "):
                in_top = line.split()[1].lower() == TOP
            elif in_top and line.upper().startswith(".ENDS"):
                break
            if not in_top:
                continue
            match = pattern.match(line)
            if match:
                orient, x, y = match.groups()
                pending = (orient.lower(), int(Decimal(x) * 1000), int(Decimal(y) * 1000))
            elif line.startswith("X"):
                name = line.split(maxsplit=1)[0]
                if name in instances:
                    if pending is None or name in placements:
                        raise RuntimeError(f"missing/duplicate placement {name}")
                    placements[name] = (instances[name][0], *pending)
                pending = None
    if len(placements) != len(instances):
        raise RuntimeError(f"incomplete placement map {len(placements)}/{len(instances)}")
    return placements


def read_def_placements(path, models, sizes):
    placements = {}
    in_components = False
    units = None
    record = ""
    pattern = re.compile(r"^-\s+(\S+)\s+(\S+)\s+.*?\+\s+(?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)")
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if line.startswith("UNITS DISTANCE MICRONS"):
                units = int(line.split()[3])
                if units != 1000:
                    raise RuntimeError(f"unsupported DEF units {units}")
            if line.startswith("COMPONENTS "):
                in_components = True
                continue
            if line == "END COMPONENTS":
                break
            if not in_components or not line:
                continue
            record += " " + line
            if not line.endswith(";"):
                continue
            match = pattern.match(record.strip())
            record = ""
            if not match:
                raise RuntimeError(f"unparsed DEF component: {line[:180]}")
            name, model, x, y, orient = match.groups()
            model = model.lower()
            if model not in models:
                continue
            x, y = int(x), int(y)
            if orient == "N":
                transform = ("r0", x, y)
            else:
                if model not in sizes:
                    raise RuntimeError(f"missing LEF size for {model}/{orient}")
                width, height = sizes[model]
                if orient == "FS":
                    transform = ("m0", x, y + height)
                elif orient == "FN":
                    transform = ("m90", x + width, y)
                elif orient == "S":
                    transform = ("r180", x + width, y + height)
                else:
                    raise RuntimeError(f"unsupported DEF orientation: {model}/{orient}")
            key = (model, *transform)
            if key in placements:
                raise RuntimeError(f"duplicate DEF placement {key}")
            placements[key] = name
    if units != 1000:
        raise RuntimeError("DEF units missing")
    return placements


def def_mapped_audit(layout, reference, contract, def_path, lef_paths, report_path, netlist_paths=()):
    lh, li, lp = layout
    rh, ri, rp = reference
    sizes = {}
    for path in lef_paths:
        sizes.update(read_lef_sizes(path))
    placements = read_placements(contract, li)
    def_placements = read_def_placements(def_path, {model for model, _nodes in li.values()}, sizes)
    # DEF/SPICE escape syntax differs; never allow normalization collisions.
    ref_names = {}
    for name in ri:
        key = name.replace("\\", "")
        if key in ref_names:
            raise RuntimeError(f"ambiguous normalized reference instance {key}")
        ref_names[key] = name
    mapped = {}
    name_map = {}
    unmatched = []
    for lname, key in placements.items():
        dname = def_placements.get(key)
        rname = ref_names.get("X" + dname.replace("\\", "")) if dname else None
        if rname is None:
            unmatched.append((lname, key, dname))
            continue
        if rname in mapped:
            raise RuntimeError(f"duplicate reference mapping {rname}")
        if li[lname][0] != ri[rname][0]:
            raise RuntimeError(f"mapped model mismatch {lname}/{rname}")
        mapped[rname] = li[lname]
        name_map[lname] = rname
    print(f"def_mapped_instances={len(mapped)}")
    print(f"def_unmatched_instances={len(unmatched)}")
    for row in unmatched[:10]:
        print(f"def_unmatched={row}")
    if unmatched or len(mapped) != len(ri):
        raise RuntimeError("DEF mapping is not a complete bijection; no topology conclusion")
    pairs, models, pins, common = endpoint_pairs((lh, mapped, lp), reference)
    if models or pins or common != len(li):
        raise RuntimeError("mapped endpoint contract mismatch")
    l_to_r, r_to_l = defaultdict(set), defaultdict(set)
    for lnet, rnet, _endpoint in pairs:
        l_to_r[lnet].add(rnet)
        r_to_l[rnet].add(lnet)
    merges = {net: sorted(peers) for net, peers in l_to_r.items() if len(peers) > 1}
    splits = {net: sorted(peers) for net, peers in r_to_l.items() if len(peers) > 1}
    differences = [
        {"layout_net": ln, "reference_net": rn, "endpoint": ep}
        for ln, rn, ep in pairs if ln in merges or rn in splits
    ]
    one_ended = []
    for net, lname, model, pin in one_ended_instance_rows(layout):
        rname = name_map[lname]
        rmodel, rnodes = ri[rname]
        rpins = [p.upper() for p in rh[rmodel]]
        rnet = rnodes[rpins.index(pin)]
        if rnet in splits or net in merges:
            one_ended.append({"layout_instance": lname, "reference_instance": rname,
                              "cell": model, "pin": pin, "layout_net": net,
                              "reference_net": rnet, "placement": placements[lname]})
    report = {
        "status": "MATCHED_TOPOLOGY" if not merges and not splits else "MISMATCH_REQUIRES_REVIEW",
        "scope": "exact instance placement and named-pin topology only; not device LVS or physical proof",
        "physical_flow_launch": 0, "netlist_modified": 0,
        "mapped_instance_count": len(mapped), "paired_endpoint_count": len(pairs),
        "layout_net_count": len(l_to_r), "reference_net_count": len(r_to_l),
        "layout_merged_nets": merges, "reference_split_nets": splits,
        "differing_endpoints": differences, "one_ended_on_differing_nets": one_ended,
        "inputs": {str(path): sha256(path) for path in [contract, def_path, *lef_paths, *netlist_paths]},
        "instance_name_map": name_map,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"def_mapped_layout_merged_net_count={len(merges)}")
    print(f"def_mapped_reference_split_net_count={len(splits)}")
    print(f"def_mapped_one_ended_on_differing_net_count={len(one_ended)}")
    print(f"def_mapped_report={report_path}")


def statements(path: Path):
    pending = ""
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        for raw in stream:
            stripped = raw.strip()
            if not stripped or stripped.startswith("*"):
                continue
            if stripped.startswith("+"):
                if not pending:
                    raise RuntimeError(f"orphan continuation in {path}")
                pending += " " + stripped[1:].strip()
                continue
            if pending:
                yield pending
            pending = stripped
    if pending:
        yield pending


def canonical_net(name: str) -> str:
    return name[1:] if name.startswith("\\") else name


def parse(path: Path):
    headers = {}
    instances = {}
    top_ports = None
    current = None
    for statement in statements(path):
        words = statement.split()
        directive = words[0].upper()
        if directive == ".SUBCKT":
            current = words[1].lower()
            if current in headers:
                raise RuntimeError(f"duplicate circuit {current} in {path}")
            headers[current] = words[2:]
            if current == TOP:
                top_ports = words[2:]
            continue
        if directive == ".ENDS":
            current = None
            continue
        if current != TOP or not words[0].upper().startswith("X"):
            continue
        name = words[0]
        model = words[-1].lower()
        nodes = [canonical_net(node) for node in words[1:-1]]
        if name in instances:
            raise RuntimeError(f"duplicate top instance {name} in {path}")
        instances[name] = (model, nodes)
    if top_ports is None:
        raise RuntimeError(f"top circuit absent from {path}")
    return headers, instances, top_ports


def circuit_net_signatures(parsed):
    headers, instances, top_ports = parsed
    signatures = defaultdict(Counter)
    model_counts = Counter()
    for _name, (model, nodes) in instances.items():
        model_counts[model] += 1
        if model not in headers:
            raise RuntimeError(f"missing child header for {model}")
        ports = headers[model]
        if len(nodes) != len(ports):
            raise RuntimeError(
                f"node/pin cardinality mismatch {model}: nodes={len(nodes)} pins={len(ports)}"
            )
        for port, net in zip(ports, nodes):
            signatures[net][f"{model}/{port.upper()}"] += 1
    for port in top_ports:
        signatures[canonical_net(port)][f"@TOP/{port.upper()}"] += 1
    return signatures, model_counts


def endpoint_pairs(layout, reference):
    lh, li, lp = layout
    rh, ri, rp = reference
    if {p.upper() for p in lp} != {p.upper() for p in rp}:
        raise RuntimeError("top port sets differ")

    pairs = []
    model_mismatches = []
    pin_set_mismatches = []
    common_instances = sorted(set(li) & set(ri))
    for name in common_instances:
        lm, ln = li[name]
        rm, rn = ri[name]
        if lm != rm:
            model_mismatches.append((name, lm, rm))
            continue
        if lm not in lh or rm not in rh:
            raise RuntimeError(f"missing child header for {name}: {lm}")
        lports = lh[lm]
        rports = rh[rm]
        if len(ln) != len(lports) or len(rn) != len(rports):
            raise RuntimeError(
                f"node/pin cardinality mismatch {name}/{lm}: "
                f"layout={len(ln)}/{len(lports)} reference={len(rn)}/{len(rports)}"
            )
        lby = {pin.upper(): net for pin, net in zip(lports, ln)}
        rby = {pin.upper(): net for pin, net in zip(rports, rn)}
        if set(lby) != set(rby):
            pin_set_mismatches.append((name, lm, sorted(set(lby) ^ set(rby))))
            continue
        for pin in sorted(lby):
            pairs.append((lby[pin], rby[pin], f"{name}/{pin}"))

    ltop = {pin.upper(): canonical_net(pin) for pin in lp}
    rtop = {pin.upper(): canonical_net(pin) for pin in rp}
    for pin in sorted(ltop):
        pairs.append((ltop[pin], rtop[pin], f"@TOP/{pin}"))
    return pairs, model_mismatches, pin_set_mismatches, len(common_instances)


def summarize(pairs, limit):
    l_to_r = defaultdict(Counter)
    r_to_l = defaultdict(Counter)
    examples = defaultdict(list)
    for lnet, rnet, endpoint in pairs:
        l_to_r[lnet][rnet] += 1
        r_to_l[rnet][lnet] += 1
        if len(examples[(lnet, rnet)]) < 4:
            examples[(lnet, rnet)].append(endpoint)

    layout_merges = {net: counts for net, counts in l_to_r.items() if len(counts) > 1}
    layout_splits = {net: counts for net, counts in r_to_l.items() if len(counts) > 1}

    print("A3_RUN15_TOPOLOGY_AUDIT=COMPLETE")
    print(f"paired_endpoints={len(pairs)}")
    print(f"layout_net_count={len(l_to_r)}")
    print(f"reference_net_count={len(r_to_l)}")
    print(f"layout_merged_net_count={len(layout_merges)}")
    print(f"layout_split_reference_net_count={len(layout_splits)}")
    for supply in ("VDD", "VSS"):
        print(
            f"layout_{supply}_maps="
            + ",".join(f"{net}:{count}" for net, count in l_to_r.get(supply, {}).most_common())
        )
        print(
            f"reference_{supply}_maps="
            + ",".join(f"{net}:{count}" for net, count in r_to_l.get(supply, {}).most_common())
        )

    def emit(title, data):
        print(title)
        ranked = sorted(
            data.items(), key=lambda item: (-sum(item[1].values()), -len(item[1]), item[0])
        )
        for net, counts in ranked[:limit]:
            pieces = []
            for peer, count in counts.most_common():
                sample = ",".join(examples[(net, peer)] if title.startswith("layout_") else examples[(peer, net)])
                pieces.append(f"{peer}:{count}[{sample}]")
            print(f"  {net} -> {'; '.join(pieces)}")

    emit("layout_net_merges:", layout_merges)
    emit("reference_net_splits:", layout_splits)
    return len(layout_merges), len(layout_splits)


def endpoint_distribution(signatures, endpoint):
    return Counter(
        {net: signature[endpoint] for net, signature in signatures.items() if signature[endpoint]}
    )


def one_ended_instance_rows(parsed):
    headers, instances, top_ports = parsed
    endpoints = defaultdict(list)
    for name, (model, nodes) in instances.items():
        ports = headers[model]
        if len(nodes) != len(ports):
            raise RuntimeError(f"node/pin cardinality mismatch {name}/{model}")
        for port, net in zip(ports, nodes):
            endpoints[net].append((name, model, port.upper()))
    for port in top_ports:
        endpoints[canonical_net(port)].append(("@TOP", TOP, port.upper()))
    return [
        (net, rows[0][0], rows[0][1], rows[0][2])
        for net, rows in endpoints.items()
        if len(rows) == 1 and rows[0][0] != "@TOP"
    ]


def summarize_signatures(layout, reference, limit, probe_endpoints):
    lsignatures, lmodels = circuit_net_signatures(layout)
    rsignatures, rmodels = circuit_net_signatures(reference)
    print(f"layout_model_types={len(lmodels)}")
    print(f"reference_model_types={len(rmodels)}")
    print(f"model_count_mismatch_count={sum(1 for model in set(lmodels) | set(rmodels) if lmodels[model] != rmodels[model])}")
    for model in sorted(set(lmodels) | set(rmodels)):
        if lmodels[model] != rmodels[model]:
            print(f"model_count_mismatch={model}|layout={lmodels[model]}|reference={rmodels[model]}")

    header_mismatches = []
    for model in sorted(set(lmodels) | set(rmodels)):
        lpins = layout[0].get(model, [])
        rpins = reference[0].get(model, [])
        lset = {pin.upper() for pin in lpins}
        rset = {pin.upper() for pin in rpins}
        if lset != rset:
            header_mismatches.append((model, lpins, rpins, sorted(lset - rset), sorted(rset - lset)))
    print(f"used_model_header_pin_set_mismatch_count={len(header_mismatches)}")
    for model, lpins, rpins, only_l, only_r in header_mismatches:
        print(
            f"header_pin_set_mismatch={model}|instances={lmodels[model]}|"
            f"layout_only={','.join(only_l)}|reference_only={','.join(only_r)}|"
            f"layout_order={','.join(lpins)}|reference_order={','.join(rpins)}"
        )

    print(f"layout_net_count={len(lsignatures)}")
    print(f"reference_net_count={len(rsignatures)}")
    common_names = set(lsignatures) & set(rsignatures)
    exact_named = sum(lsignatures[name] == rsignatures[name] for name in common_names)
    differing_named = sorted(
        (name for name in common_names if lsignatures[name] != rsignatures[name]),
        key=lambda name: (-(sum(lsignatures[name].values()) + sum(rsignatures[name].values())), name),
    )
    print(f"common_net_name_count={len(common_names)}")
    print(f"exact_named_net_signature_count={exact_named}")
    print(f"differing_named_net_signature_count={len(differing_named)}")

    lmultiset = Counter(tuple(sorted(signature.items())) for signature in lsignatures.values())
    rmultiset = Counter(tuple(sorted(signature.items())) for signature in rsignatures.values())
    print(f"layout_unique_net_signature_count={len(lmultiset)}")
    print(f"reference_unique_net_signature_count={len(rmultiset)}")
    print(f"net_signature_multiset_equal={int(lmultiset == rmultiset)}")
    print(f"layout_only_signature_instances={sum((lmultiset - rmultiset).values())}")
    print(f"reference_only_signature_instances={sum((rmultiset - lmultiset).values())}")

    def one_ended_endpoint_counts(signatures):
        counts = Counter()
        for signature in signatures.values():
            if sum(signature.values()) == 1:
                endpoint, multiplicity = next(iter(signature.items()))
                if multiplicity != 1:
                    raise RuntimeError(f"invalid one-ended signature: {signature}")
                counts[endpoint] += 1
        return counts

    lone = one_ended_endpoint_counts(lsignatures)
    rone = one_ended_endpoint_counts(rsignatures)
    print(f"layout_one_ended_net_count={sum(lone.values())}")
    print(f"reference_one_ended_net_count={sum(rone.values())}")
    print(f"one_ended_endpoint_count_delta={sum(lone.values()) - sum(rone.values())}")
    print("one_ended_endpoint_counts:")
    for endpoint in sorted(set(lone) | set(rone)):
        if lone[endpoint] != rone[endpoint]:
            print(f"  {endpoint}|layout={lone[endpoint]}|reference={rone[endpoint]}|delta={lone[endpoint] - rone[endpoint]}")
    print("layout_excess_one_ended_endpoints:")
    for endpoint, count in (lone - rone).most_common(limit):
        print(f"  {endpoint}|count={count}")
    print("reference_excess_one_ended_endpoints:")
    for endpoint, count in (rone - lone).most_common(limit):
        print(f"  {endpoint}|count={count}")

    def emit_signature_delta(title, delta):
        print(title)
        ranked = sorted(
            delta.items(),
            key=lambda item: (-item[1], -sum(count for _endpoint, count in item[0]), item[0]),
        )
        for signature, multiplicity in ranked[:limit]:
            endpoints = ",".join(f"{endpoint}:{count}" for endpoint, count in signature)
            print(f"  multiplicity={multiplicity}|endpoints={endpoints}")

    emit_signature_delta("layout_only_net_signatures:", lmultiset - rmultiset)
    emit_signature_delta("reference_only_net_signatures:", rmultiset - lmultiset)

    for supply in ("VDD", "VSS"):
        lsig = lsignatures.get(supply, Counter())
        rsig = rsignatures.get(supply, Counter())
        print(f"{supply}_signature_equal={int(lsig == rsig)}")
        print(f"{supply}_layout_endpoint_count={sum(lsig.values())}")
        print(f"{supply}_reference_endpoint_count={sum(rsig.values())}")
        mismatched_endpoints = [
            endpoint for endpoint in sorted(set(lsig) | set(rsig))
            if lsig[endpoint] != rsig[endpoint]
        ]
        print(f"{supply}_endpoint_mismatch_count={len(mismatched_endpoints)}")
        ranked_endpoints = sorted(
            mismatched_endpoints,
            key=lambda endpoint: (-abs(lsig[endpoint] - rsig[endpoint]), endpoint),
        )
        for endpoint in ranked_endpoints[:limit]:
            print(
                f"{supply}_endpoint_mismatch={endpoint}|layout={lsig[endpoint]}|reference={rsig[endpoint]}"
            )

    for endpoint in probe_endpoints:
        label = endpoint.lower().replace("/", "_")
        for side, signatures in (("layout", lsignatures), ("reference", rsignatures)):
            distribution = endpoint_distribution(signatures, endpoint)
            print(f"probe_{label}_{side}_total={sum(distribution.values())}")
            print(
                f"probe_{label}_{side}_nets="
                + ",".join(f"{net}:{count}" for net, count in distribution.most_common(limit))
            )

    print("largest_differing_named_nets:")
    for name in differing_named[:limit]:
        lonly = lsignatures[name] - rsignatures[name]
        ronly = rsignatures[name] - lsignatures[name]
        ltext = ",".join(f"{key}:{value}" for key, value in lonly.most_common(6))
        rtext = ",".join(f"{key}:{value}" for key, value in ronly.most_common(6))
        print(
            f"  {name}|layout_endpoints={sum(lsignatures[name].values())}|"
            f"reference_endpoints={sum(rsignatures[name].values())}|layout_only={ltext}|reference_only={rtext}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--probe-endpoint", action="append", default=[])
    parser.add_argument("--one-ended-manifest", type=Path)
    parser.add_argument("--def-file", type=Path)
    parser.add_argument("--layout-contract", type=Path)
    parser.add_argument("--lef", type=Path, action="append", default=[])
    parser.add_argument("--mapped-report", type=Path)
    args = parser.parse_args()
    layout = parse(args.layout)
    reference = parse(args.reference)
    if args.def_file:
        if not args.layout_contract or not args.mapped_report:
            parser.error("--def-file requires --layout-contract and --mapped-report")
        def_mapped_audit(layout, reference, args.layout_contract, args.def_file,
                         args.lef, args.mapped_report, [args.layout, args.reference])
    pairs, model_mismatches, pin_set_mismatches, common_instances = endpoint_pairs(layout, reference)
    print(f"layout_top_instances={len(layout[1])}")
    print(f"reference_top_instances={len(reference[1])}")
    print(f"common_instance_name_count={common_instances}")
    print(f"model_mismatch_count={len(model_mismatches)}")
    print(f"pin_set_mismatch_count={len(pin_set_mismatches)}")
    for row in model_mismatches[:10]:
        print("model_mismatch=" + "|".join(row))
    for name, model, pins in pin_set_mismatches[:10]:
        print(f"pin_set_mismatch={name}|{model}|{','.join(pins)}")
    if common_instances:
        summarize(pairs, args.limit)
    summarize_signatures(layout, reference, args.limit, args.probe_endpoint)
    if args.one_ended_manifest:
        reference_endpoints = Counter(
            f"{model}/{port}" for _net, _name, model, port in one_ended_instance_rows(reference)
        )
        rows = [
            (net, name, model, port)
            for net, name, model, port in one_ended_instance_rows(layout)
            if reference_endpoints[f"{model}/{port}"] == 0
        ]
        rows.sort(key=lambda row: int(row[1][2:]) if row[1].startswith("X$") else row[1])
        if len(rows) != 250:
            raise RuntimeError(f"expected 250 layout-only one-ended pins, got {len(rows)}")
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        lines = [
            "A3_RUN15_LAYOUT_ONLY_ONE_ENDED_AUDIT=PASS",
            f"layout_sha256={digest(args.layout)}",
            f"reference_sha256={digest(args.reference)}",
            f"layout_only_one_ended_pin_count={len(rows)}",
        ]
        lines.extend(
            f"instance={name}|cell={model}|pin={port}|isolated_net={net}"
            for net, name, model, port in rows
        )
        args.one_ended_manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"one_ended_manifest={args.one_ended_manifest}")
        print(f"layout_only_one_ended_pin_count={len(rows)}")


if __name__ == "__main__":
    main()
