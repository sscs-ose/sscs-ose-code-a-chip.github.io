from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "spice_results"
OUTPUT_FILE = Path.cwd() / "ranked_vcont0.csv"
IDENTIFIER_PATTERN = re.compile(
    r"tb_vco_v5_([^_]+_[^_]+)_V([0-9]+(?:p[0-9]+)?)V_T([+-]?\d+)C"
)


def parse_identifier(path: Path) -> tuple[str, str, str]:
    name = path.parent.name if path.parent != RESULTS_DIR else path.stem
    match = IDENTIFIER_PATTERN.match(name)
    if match:
        return match.groups()

    fallback_match = IDENTIFIER_PATTERN.search(name)
    if fallback_match:
        return fallback_match.groups()

    parts = name.split("_")
    variant = parts[3] if len(parts) > 3 else "unknown"
    vdd = parts[4][1:-1] if len(parts) > 4 and parts[4].startswith("V") else "unknown"
    temp = parts[5][1:-1] if len(parts) > 5 and parts[5].startswith("T") else "unknown"
    return variant, vdd, temp


def find_csv_files(root: Path) -> Iterable[Path]:
    yield from sorted(root.rglob("*_all_points.csv"))


def read_frequency_range_rows(csv_path: Path) -> tuple[str, str, str, float, float, str] | None:
    variant, vdd, temp = parse_identifier(csv_path)
    freqs: list[float] = []

    with csv_path.open(newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        if "Vcont" not in reader.fieldnames or "Freq" not in reader.fieldnames:
            raise ValueError(
                f"Arquivo {csv_path} não contém as colunas esperadas: Vcont, Freq"
            )

        for row in reader:
            if row["Vcont"] is None or row["Freq"] is None:
                continue
            try:
                float(row["Vcont"])
                freq = float(row["Freq"])
                freqs.append(freq)
            except ValueError:
                continue

    if not freqs:
        return None

    freq_minima = min(freqs)
    freq_maxima = max(freqs)
    return variant, vdd, temp, freq_minima, freq_maxima, str(csv_path)


def write_ranked_csv(
    rows: list[tuple[str, str, str, float, float, str]], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = ["variant", "vdd", "temperature", "freq_minima", "freq_maxima", "source"]
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(header)
        for variant, vdd, temp, freq_minima, freq_maxima, source in rows:
            writer.writerow([variant, vdd, temp, freq_minima, freq_maxima, source])


def main() -> None:
    all_rows: list[tuple[str, str, str, float, float, str]] = []
    for csv_path in find_csv_files(RESULTS_DIR):
        file_row = read_frequency_range_rows(csv_path)
        if file_row is None:
            continue
        all_rows.append(file_row)

    if not all_rows:
        raise SystemExit("Nenhum valor de frequência encontrado nos arquivos CSV.")

    all_rows.sort(key=lambda item: item[3], reverse=True)
    write_ranked_csv(all_rows, OUTPUT_FILE)
    print(f"CSV ranqueado criado em: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
