#!/usr/bin/env python3
"""
Script para rodar simulação SPICE e gerar CSV com valores de Vcont e Freq
"""

import subprocess
import re
import csv
import os
import glob
import argparse
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def run_spice_simulation(spice_file):
    """
    Executa a simulação SPICE e retorna a saída do terminal
    """
    try:
        # Executar ngspice em modo batch
        result = subprocess.run(
            ['ngspice', '-b', spice_file],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(spice_file)
        )
        return result.stdout + result.stderr
    except FileNotFoundError:
        print("Erro: ngspice não encontrado. Instale ngspice.")
        return None


def run_spice_simulation_stream(spice_file, on_pair):
    """
    Executa ngspice em modo batch e processa a saída em streaming.
    Para cada par (vcont, freq) identificado, chama `on_pair(vcont, freq)` imediatamente.
    Retorna a saída completa como string (para salvar em log).
    """
    try:
        proc = subprocess.Popen(
            ['ngspice', '-b', spice_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(spice_file),
            bufsize=1,
        )

        output_lines = []
        last_vcont = None

        # Itera sobre as linhas conforme são produzidas
        for raw_line in proc.stdout:
            line = raw_line.rstrip('\n')
            output_lines.append(line)

            stripped = line.strip()
            if not stripped or stripped.startswith('*') or stripped.startswith('-'):
                continue

            # detecta linha de Vcont
            match_vcont = re.match(r'^([0-9.]+)\s*=\s*([0-9.e+\-]+)$', stripped)
            if match_vcont:
                try:
                    last_vcont = float(match_vcont.group(1))
                except ValueError:
                    last_vcont = None
                continue

            # detecta linha de freq e combina com o último vcont lido
            match_freq = re.match(r'^freq\s*=\s*([0-9.e+\-]+)$', stripped)
            if match_freq and last_vcont is not None:
                try:
                    freq = float(match_freq.group(1).replace(',', '.'))
                except ValueError:
                    last_vcont = None
                    continue

                if 0 <= last_vcont <= 1.8 and freq > 1e6:
                    try:
                        on_pair(last_vcont, freq)
                    except Exception as e:
                        print(f"Erro no callback on_pair: {e}")

                last_vcont = None

        proc.wait()
        return '\n'.join(output_lines)

    except FileNotFoundError:
        print("Erro: ngspice não encontrado. Instale ngspice.")
        return None

def parse_output(output):
    """
    Parse da saída do ngspice para extrair valores de Vcont e Freq
    O formato do seu log é do tipo:
      0.00 = 0.000000e+00
      freq = 3.241577e+09
    """
    data = []
    lines = output.split('\n')

    for i, line in enumerate(lines):
        line = line.strip()

        if not line or line.startswith('*') or line.startswith('-'):
            continue

        # Ex.: 0.00 = 0.000000e+00
        match_vcont = re.match(r'^([0-9.]+)\s*=\s*([0-9.e+\-]+)$', line)
        if match_vcont:
            try:
                vcont = float(match_vcont.group(1))
            except ValueError:
                continue

            # Procura a linha seguinte com 'freq = ...'
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                match_freq = re.match(r'^freq\s*=\s*([0-9.e+\-]+)$', next_line)
                if match_freq:
                    try:
                        freq = float(match_freq.group(1).replace(',', '.'))
                    except ValueError:
                        continue

                    if 0 <= vcont <= 1.8 and freq > 1e6:
                        data.append((vcont, freq))

    return data

def write_csv(data, output_file='resultado.csv'):
    """
    Escreve os dados em arquivo CSV
    """
    try:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Escreve cabeçalho
            writer.writerow(['Vcont', 'Freq'])
            # Escreve dados
            for vcont, freq in data:
                writer.writerow([vcont, freq])
        
        print(f"✓ CSV gerado com sucesso: {output_file}")
        print(f"✓ Total de pontos: {len(data)}")
        return True
    except IOError as e:
        print(f"Erro ao escrever CSV: {e}")
        return False


def write_point_csv(vcont, freq, output_file):
    """
    Escreve um único ponto Vcont/Freq em CSV
    """
    try:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Vcont', 'Freq'])
            writer.writerow([vcont, freq])
        return True
    except IOError as e:
        print(f"Erro ao escrever CSV de ponto: {e}")
        return False


def write_point_files(data, output_dir, base):
    """
    Escreve um CSV separado para cada ponto extraído e um resumo com todos os pontos.
    """
    os.makedirs(output_dir, exist_ok=True)

    for index, (vcont, freq) in enumerate(data, start=1):
        output_file = os.path.join(output_dir, f"mismatch_{index:02d}.csv")
        if not write_point_csv(vcont, freq, output_file):
            return False

    summary_csv = os.path.join(output_dir, f"{base}_all_points.csv")
    return write_csv(data, summary_csv)


def get_all_result_csvs(results_dir):
    """Retorna os CSVs de resultado, priorizando os arquivos *_all_points.csv."""
    results_path = Path(results_dir)
    summary_files = sorted(results_path.rglob('*_all_points.csv'))
    if summary_files:
        return summary_files
    return sorted(results_path.rglob('*.csv'))


def load_all_frequencies(results_dir):
    """Carrega todos os valores de frequência dos resultados em spice_results."""
    all_points = []
    seen = set()

    for csv_path in get_all_result_csvs(results_dir):
        try:
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames or 'Freq' not in reader.fieldnames:
                    continue

                for row in reader:
                    try:
                        vcont = float(row.get('Vcont', 0) or 0)
                        freq = float(row.get('Freq', 0) or 0)
                    except (TypeError, ValueError):
                        continue

                    if not math.isfinite(vcont) or not math.isfinite(freq):
                        continue

                    if 0 <= vcont <= 1.8 and freq > 1e6:
                        key = (round(vcont, 12), round(freq, 12))
                        if key not in seen:
                            seen.add(key)
                            all_points.append((vcont, freq))
        except OSError:
            continue

    return all_points


def collect_mismatch_tests(results_dir):
    """Coleta todos os testes do tipo mismatch × PVT para cálculo de yield."""
    tests = []
    for case_dir in sorted(Path(results_dir).iterdir()):
        if not case_dir.is_dir():
            continue

        for mismatch_file in sorted(case_dir.glob('mismatch_*.csv')):
            try:
                with open(mismatch_file, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    if not reader.fieldnames or 'Freq' not in reader.fieldnames:
                        continue

                    freqs = []
                    for row in reader:
                        try:
                            freq = float(row.get('Freq', 0) or 0)
                        except (TypeError, ValueError):
                            continue
                        if math.isfinite(freq) and freq > 1e6:
                            freqs.append(freq)

                    if not freqs:
                        continue

                    fmin = min(freqs)
                    fmax = max(freqs)
                    tests.append({
                        'case': case_dir.name,
                        'mismatch': mismatch_file.stem,
                        'fmin': fmin,
                        'fmax': fmax,
                        'cover_2_4_2_4835': fmin <= 2.4e9 and fmax >= 2.4835e9,
                        'cover_2_38_2_5': fmin <= 2.38e9 and fmax >= 2.5e9,
                    })
            except OSError:
                continue

    return tests


def generate_histogram_from_results(results_dir, output_path='histograma_freq.png', bins=50):
    """Gera um histograma das frequências em todos os resultados do spice_results."""
    points = load_all_frequencies(results_dir)
    if not points:
        raise ValueError(f'Nenhum dado válido encontrado em: {results_dir}')

    freqs = [freq for _, freq in points]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bt_lower = 2.4e9
    bt_target_upper = 2.4835e9
    bt_alert_lower = 2.38e9
    bt_alert_upper = 2.5e9

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(freqs, bins=bins, range=(min(freqs), max(freqs)), color='#4C72B0', edgecolor='black')

    for x0, x1, label in [
        (bt_lower, bt_target_upper, 'Bluetooth 2.400-2.4835 GHz'),
        (bt_alert_lower, bt_alert_upper, 'Faixa de atenção 2.380-2.500 GHz'),
    ]:
        ax.axvspan(x0, x1, color='#ffcc00', alpha=0.12)
        ax.axvline(x0, color='#d97706', linestyle='--', linewidth=1.5, alpha=0.9)
        ax.axvline(x1, color='#d97706', linestyle='--', linewidth=1.5, alpha=0.9)
        ax.text((x0 + x1) / 2, ax.get_ylim()[1] * 0.94, label, ha='center', va='top', rotation=90,
                fontsize=8, color='#7c2d12', bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

    ax.set_title(f'Distribuição de frequências ({len(freqs)} pontos)')
    ax.set_xlabel('Frequência (Hz)')
    ax.set_ylabel('Contagem')
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_xlim(min(freqs), max(freqs))
    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return len(freqs), output_path


def summarize_bluetooth_coverage(tests):
    """Classifica os testes em azul, verde exclusivo e vermelho em relação ao total."""
    total = len(tests)
    blue = sum(1 for test in tests if test.get('cover_2_38_2_5', False))
    green_exclusive = sum(
        1 for test in tests
        if test.get('cover_2_4_2_4835', False) and not test.get('cover_2_38_2_5', False)
    )
    red = sum(1 for test in tests if not test.get('cover_2_38_2_5', False) and not test.get('cover_2_4_2_4835', False))

    summary = {
        'total': total,
        'blue': blue,
        'green_exclusive': green_exclusive,
        'red': red,
    }
    return summary


def generate_bluetooth_metrics(results_dir, output_path='bluetooth_metrics.png'):
    """Gera o gráfico Fmin/Fmax dos testes de mismatch × PVT."""
    tests = collect_mismatch_tests(results_dir)
    if not tests:
        raise ValueError(f'Nenh um teste válido encontrado em: {results_dir}')

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 7))
    xs = [test['fmin'] / 1e9 for test in tests]
    ys = [test['fmax'] / 1e9 for test in tests]
    colors = [
        '#2563eb' if test.get('cover_2_38_2_5', False)
        else '#22c55e' if test.get('cover_2_4_2_4835', False)
        else '#ef4444'
        for test in tests
    ]

    ax.scatter(xs, ys, s=38, c=colors, alpha=0.85, edgecolor='black', linewidth=0.25)
    ax.axvline(2.3800, color='#2563eb', linestyle='--', linewidth=1.5, label='Fmin = 2.3800 GHz')
    ax.axvline(2.4000, color='#22c55e', linestyle='--', linewidth=1.5, label='Fmin = 2.4000 GHz')
    ax.axhline(2.4835, color='#22c55e', linestyle='--', linewidth=1.5, label='Fmax = 2.4835 GHz')
    ax.axhline(2.5000, color='#2563eb', linestyle='--', linewidth=1.5, label='Fmax = 2.5000 GHz')
    ax.fill_between([1.8, 2.4], 2.4835, 3.4, color='#fbbf24', alpha=0.08)

    summary = summarize_bluetooth_coverage(tests)
    blue_pct = 100.0 * summary['blue'] / summary['total'] if summary['total'] else 0.0
    green_pct = 100.0 * summary['green_exclusive'] / summary['total'] if summary['total'] else 0.0
    red_pct = 100.0 * summary['red'] / summary['total'] if summary['total'] else 0.0

    legend_handles = [
        plt.Line2D([0], [0], marker='o', color='w', label=f'Ótimos: {blue_pct:.2f}% ({summary["blue"]}/{summary["total"]})', markerfacecolor='#2563eb', markersize=8),
        plt.Line2D([0], [0], marker='o', color='w', label=f'Marginais: {green_pct:.2f}% ({summary["green_exclusive"]}/{summary["total"]})', markerfacecolor='#22c55e', markersize=8),
        plt.Line2D([0], [0], marker='o', color='w', label=f'Falhos: {red_pct:.2f}% ({summary["red"]}/{summary["total"]})', markerfacecolor='#ef4444', markersize=8),
    ]

    ax.set_title('Faixa de cobertura do CSRO-VCO')
    ax.set_xlabel('Fmin (GHz)')
    ax.set_ylabel('Fmax (GHz)')
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_xlim(1.8, 3.0)
    ax.set_ylim(2.2, 3.4)
    ax.legend(handles=legend_handles, loc='upper right', fontsize=9)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return {'output_path': output_path, 'tests': tests}


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(script_dir, 'spice_results')
    os.makedirs(results_dir, exist_ok=True)

    parser = argparse.ArgumentParser(description='Gera o gráfico Fmin/Fmax a partir dos CSVs já existentes em spice_results')
    parser.add_argument('--fmin-fmax', action='store_true', help='Gera o gráfico Fmin/Fmax a partir dos CSVs em spice_results')
    args = parser.parse_args()

    try:
        metrics_path = os.path.join(results_dir, 'bluetooth_metrics.png')
        metrics = generate_bluetooth_metrics(results_dir, output_path=metrics_path)
        print(f'Gráfico Fmin/Fmax gerado: {metrics["output_path"]}')

        totals = summarize_bluetooth_coverage(metrics['tests'])
        print('\nResumo da análise Bluetooth:')
        print(f'- Azul / total: {totals["blue"]}/{totals["total"]} = {100.0 * totals["blue"] / totals["total"]:.2f}%')
        print(f'- Verde exclusivo / total: {totals["green_exclusive"]}/{totals["total"]} = {100.0 * totals["green_exclusive"] / totals["total"]:.2f}%')
        print(f'- Vermelho / total: {totals["red"]}/{totals["total"]} = {100.0 * totals["red"] / totals["total"]:.2f}%')

        print('\nObservação: verde exclusivo significa verde e não azul ao mesmo tempo.')

        return True
    except ValueError as exc:
        print(f'Erro ao gerar gráficos: {exc}')
        return False

def test_with_log_file(log_file):
    """
    Função para testar o parser com um arquivo de log já existente
    Útil para debug sem rodar a simulação completa
    """
    if not os.path.exists(log_file):
        print(f"Erro: Arquivo {log_file} não encontrado")
        return False
    
    with open(log_file, 'r') as f:
        output = f.read()
    
    print(f"Lendo arquivo: {log_file}")
    print("-" * 60)
    
    data = parse_output(output)
    
    if not data:
        print("Aviso: Nenhum dado foi extraído")
        print("\nPrimeiras 50 linhas do arquivo:")
        print("\n".join(output.split('\n')[:50]))
        return False
    
    print(f"✓ Dados extraídos: {len(data)} pontos")
    
    script_dir = os.path.dirname(os.path.abspath(log_file))
    output_csv = os.path.join(script_dir, 'resultado.csv')
    
    success = write_csv(data, output_csv)
    
    if success:
        print("\nPrimeiros 5 pontos:")
        for vcont, freq in data[:5]:
            print(f"  Vcont: {vcont:.2f} V → Freq: {freq:.6e} Hz ({freq/1e9:.3f} GHz)")
        
        print("\nÚltimos 5 pontos:")
        for vcont, freq in data[-5:]:
            print(f"  Vcont: {vcont:.2f} V → Freq: {freq:.6e} Hz ({freq/1e9:.3f} GHz)")
    
    return success

if __name__ == '__main__':
    import sys
    ok = main()
    sys.exit(0 if ok else 1)
