#!/usr/bin/env python3
"""Gera o gráfico do sinal de tensão em função do tempo."""

from pathlib import Path

import matplotlib.pyplot as plt


def ler_sinal(csv_path: str):
    tempo = []
    tensao = []

    with open(csv_path, encoding='utf-8') as f:
        for line in f:
            valores = line.split()
            if len(valores) >= 2:
                tempo.append(float(valores[0]))
                tensao.append(float(valores[1]))

    return tempo, tensao


def main():
    script_dir = Path(__file__).resolve().parent
    sinal_csv_path = script_dir / 'tb_vco_v1.csv'
    png_sinal_path = script_dir / 'grafico_tensao_vs_tempo.png'

    if not sinal_csv_path.exists():
        raise FileNotFoundError(f'Arquivo não encontrado: {sinal_csv_path}')

    tempo, tensao = ler_sinal(str(sinal_csv_path))

    fig, ax = plt.subplots(figsize=(8, 5), facecolor='none')
    ax.set_facecolor('none')
    ax.plot(tempo, tensao, linestyle='-', linewidth=2.0, color='tab:blue')
    ax.set_xlabel('Tempo (s)')
    ax.set_ylabel('Tensão (V)')
    ax.set_title('Sinal de Tensão no Tempo')
    ax.grid(True, linestyle='--', alpha=0.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(png_sinal_path, dpi=300, transparent=True)
    plt.close(fig)

    print(f'Gráfico de tensão salvo em: {png_sinal_path}')


if __name__ == '__main__':
    main()
