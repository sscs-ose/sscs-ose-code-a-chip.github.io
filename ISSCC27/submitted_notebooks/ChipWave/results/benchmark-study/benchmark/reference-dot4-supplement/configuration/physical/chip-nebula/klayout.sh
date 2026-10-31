#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${KLAYOUT_CMD:-}" ]]; then
    echo "Error: KLayout not found in PATH" >&2
    exit 1
fi

args=("$@")
cdl_index=-1
cdl=""
top=""
for ((i=0; i<${#args[@]}; i++)); do
    if [[ "${args[i]}" == "-rd" && $((i+1)) -lt ${#args[@]} ]]; then
        case "${args[i+1]}" in
            cdl_file=*) cdl_index=$((i+1)); cdl="${args[i+1]#cdl_file=}" ;;
            top_cell=*) top="${args[i+1]#top_cell=}" ;;
        esac
    fi
done
if [[ $cdl_index -ge 0 ]]; then
    [[ -n "$top" && -s "$cdl" ]] || {
        echo "ERROR: LVS requires a top cell and nonempty source CDL" >&2
        exit 2
    }
    filtered="${cdl%.cdl}_used.cdl"
    "${PYTHON_EXE:-python3}" "$(dirname -- "${BASH_SOURCE[0]}")/filter_lvs_cdl.py" \
        "$cdl" "$filtered" "$top"
    args[cdl_index]="cdl_file=$filtered"
fi
"$KLAYOUT_CMD" -v
"$KLAYOUT_CMD" "${args[@]}"
