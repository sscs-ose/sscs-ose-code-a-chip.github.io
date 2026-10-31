#!/usr/bin/env python3
"""Gera histogramas de fmin e fmax para cada PVT."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "spice_results"
OUTPUT_DIR = ROOT / "mismatch_50_lines_all_cases"
FMIN_LIMITE_GHZ = 2.4
FMAX_LIMITE_GHZ = 2.4835


def ler_mismatch(csv_path: Path):
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((float(row["Vcont"]), float(row["Freq"])))
    if not rows:
        return []
    rows.sort(key=lambda item: item[0])
    return rows


def gerar_histogramas_spice_results(results_dir: Path, out_dir: Path):
    mismatch_files = sorted(results_dir.rglob("mismatch_*.csv"))
    if not mismatch_files:
        return 0

    fmins = []
    fmaxs = []

    for mismatch_file in mismatch_files:
        pontos = ler_mismatch(mismatch_file)
        if not pontos:
            continue
        frequencias_ghz = [freq / 1e9 for _, freq in pontos]
        fmins.append(min(frequencias_ghz))
        fmaxs.append(max(frequencias_ghz))

    if not fmins:
        return 0

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    histogramas = (
        (axes[0], fmins, "fmin por mismatch", "fmin (GHz)", FMIN_LIMITE_GHZ),
        (axes[1], fmaxs, "fmax por mismatch", "fmax (GHz)", FMAX_LIMITE_GHZ),
    )
    for ax, valores, titulo, xlabel, limite in histogramas:
        ax.hist(valores, bins="auto", color="#315f8c", edgecolor="white")
        ax.axvline(limite, color="#c0392b", linestyle="--", linewidth=1.5)
        ax.text(
            limite,
            1,
            f" limite = {limite:g} GHz",
            transform=ax.get_xaxis_transform(),
            color="#c0392b",
            ha="left",
            va="bottom",
        )
        ax.set_title(titulo)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Quantidade de mismatch")

    for ax in axes:
        ax.grid(True, axis="y", linestyle="--", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle(results_dir.name)
    plt.tight_layout()

    output_png = out_dir / f"{results_dir.name}_histogramas_fmin_fmax.png"
    fig.savefig(output_png, dpi=300, transparent=True)
    plt.close(fig)
    return len(fmins)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not RESULTS_DIR.exists():
        raise SystemExit(f"Nenhum arquivo mismatch_*.csv encontrado em: {RESULTS_DIR}")

    total = 0
    pvt_dirs = sorted(path for path in RESULTS_DIR.iterdir() if path.is_dir())
    for pvt_dir in pvt_dirs:
        count = gerar_histogramas_spice_results(pvt_dir, OUTPUT_DIR)
        if count:
            total += count
            print(f"Gerado: {pvt_dir.name} ({count} mismatch)")

    if not total:
        raise SystemExit(f"Nenhum arquivo mismatch_*.csv encontrado em: {RESULTS_DIR}")

    print(f"\nTotal de dados processados: {total}")
    print(f"Pasta de saída: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
