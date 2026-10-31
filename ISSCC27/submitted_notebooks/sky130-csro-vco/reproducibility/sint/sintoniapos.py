#!/usr/bin/env python3
"""Gera gráficos de frequência e Kvco a partir do arquivo resultado.csv."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt


def ler_csv(csv_path: str):
    vcont = []
    freq = []

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            vcont.append(float(row['Vcont']))
            freq.append(float(row['Freq']))

    return vcont, freq


def calcular_kvco(vcont, freq):
    kvco = []

    for i in range(len(vcont)):
        if i == 0:
            dv = vcont[1] - vcont[0]
            k = (freq[1] - freq[0]) / dv
        elif i == len(vcont) - 1:
            dv = vcont[-1] - vcont[-2]
            k = (freq[-1] - freq[-2]) / dv
        else:
            dv = vcont[i + 1] - vcont[i - 1]
            k = (freq[i + 1] - freq[i - 1]) / dv

        kvco.append(k)

    return kvco


def main():
    script_dir = Path(__file__).resolve().parent
    csv_path = script_dir / 'resultado.csv'
    png_freq_path = script_dir / 'grafico_freq_vs_vcont.png'
    png_kvco_path = script_dir / 'grafico_kvco_vs_vcont.png'

    if not csv_path.exists():
        raise FileNotFoundError(f'Arquivo não encontrado: {csv_path}')

    vcont, freq = ler_csv(str(csv_path))
    kvco = calcular_kvco(vcont, freq)

    fig, ax = plt.subplots(figsize=(8, 5), facecolor='none')
    ax.set_facecolor('none')
    ax.plot(vcont, freq, linestyle='-', linewidth=2.0, color='tab:blue')
    ax.set_xlabel('Tensão de controle (V)')
    ax.set_ylabel('Frequência de Saída (Hz)')
    ax.set_title('Curva de Sintonia do VCO')
    ax.grid(True, linestyle='--', alpha=0.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(png_freq_path, dpi=300, transparent=True)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5), facecolor='none')
    ax.set_facecolor('none')
    ax.plot(vcont, kvco, linestyle='-', linewidth=2.0, color='tab:orange')
    ax.set_xlabel('Tensão de controle (V)')
    ax.set_ylabel('Kvco (Hz/V)')
    ax.set_title('Sensibilidade de Sintonia Kvco')
    ax.grid(True, linestyle='--', alpha=0.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(png_kvco_path, dpi=300, transparent=True)
    plt.close(fig)

    print(f'Gráfico salvo em: {png_freq_path}')
    print(f'Gráfico de Kvco salvo em: {png_kvco_path}')


if __name__ == '__main__':
    main()
