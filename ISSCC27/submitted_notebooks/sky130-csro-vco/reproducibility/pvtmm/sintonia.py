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
import shutil
from pathlib import Path

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


def count_csv_rows(csv_path: Path) -> int:
    """Conta linhas válidas de dados em um CSV do tipo Vcont,Freq."""
    try:
        with csv_path.open('r', newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                return 0
            count = 0
            for row in reader:
                vcont = row.get('Vcont')
                freq = row.get('Freq')
                if vcont not in (None, '') and freq not in (None, ''):
                    count += 1
            return count
    except (FileNotFoundError, OSError, csv.Error):
        return 0


def is_complete_pvt_dir(pvt_dir: str | os.PathLike) -> bool:
    """Retorna True quando o diretório do PVT já foi concluído e não precisa ser reprocessado."""
    pvt_dir = Path(pvt_dir)
    if not pvt_dir.exists() or not pvt_dir.is_dir():
        return False

    mismatch_files = sorted(pvt_dir.glob('mismatch_*.csv'))
    summary_files = sorted(pvt_dir.glob('*_all_points.csv'))

    if not mismatch_files and not summary_files:
        return False

    for mismatch_file in mismatch_files:
        if count_csv_rows(mismatch_file) < 2:
            return False

    if summary_files:
        last_summary = summary_files[-1]
        if count_csv_rows(last_summary) < 2:
            return False

    return True


def reset_incomplete_pvt_dir(pvt_dir: Path) -> bool:
    """Remove os artefatos do PVT se ele estiver incompleto ou corrompido."""
    if not pvt_dir.exists():
        return False

    if is_complete_pvt_dir(pvt_dir):
        return False

    shutil.rmtree(pvt_dir)
    return True


def main():
    parser = argparse.ArgumentParser(description='Roda simulações ngspice em lote e gera CSVs')
    parser.add_argument('paths', nargs='*', help='Arquivo(s) .spice ou diretório(s) com .spice. Se vazio, usa spice_variants/')
    parser.add_argument('--dry-run', action='store_true', help='Apenas lista os arquivos que seriam executados')
    parser.add_argument('--force', action='store_true', help='Força a reexecução de todos os arquivos, ignorando resultados já completos')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_variants = os.path.join(script_dir, 'spice_variants')
    results_dir = os.path.join(script_dir, 'spice_results')
    os.makedirs(results_dir, exist_ok=True)

    # Monta lista de arquivos a executar
    spice_files = []
    if args.paths:
        for p in args.paths:
            if os.path.isdir(p):
                spice_files.extend(sorted(glob.glob(os.path.join(p, '*.spice'))))
            elif os.path.isfile(p) and p.lower().endswith('.spice'):
                spice_files.append(p)
            else:
                print(f"Aviso: caminho ignorado (não .spice nem diretório): {p}")
    else:
        spice_files = sorted(glob.glob(os.path.join(default_variants, '*.spice')))

    if not spice_files:
        print(f"Nenhum arquivo .spice encontrado para processar. Procurado em: {default_variants}")
        return False

    print(f"Encontrados {len(spice_files)} arquivos .spice")
    if args.dry_run:
        for f in spice_files:
            print('  -', f)
        return True

    total_points = 0
    for spice_file in spice_files:
        base = Path(spice_file).stem
        log_path = Path(results_dir) / f'{base}.log'
        csv_path = Path(results_dir) / f'{base}.csv'
        pvt_dir = Path(results_dir) / base

        if pvt_dir.exists() and is_complete_pvt_dir(pvt_dir) and not args.force:
            print(f'✓ PVT já completo, pulando: {pvt_dir}')
            continue

        if pvt_dir.exists():
            print(f'⚠️ PVT incompleto ou corrompido detectado. Limpando artefatos parciais: {pvt_dir}')
            reset_incomplete_pvt_dir(pvt_dir)

        for stale_path in [log_path, csv_path]:
            if stale_path.exists():
                stale_path.unlink()

        print('\n' + '=' * 60)
        print(f'Executando: {spice_file}')
        print(f'Logs → {log_path} ; CSV → {csv_path}')

        # Executa ngspice em streaming e grava cada mismatch assim que é detectado
        pvt_dir.mkdir(parents=True, exist_ok=True)
        data = []

        # Buffer para acumular os pontos de um mismatch até completar o bloco
        current_mismatch = []
        mismatch_idx = 0
        points_per_mismatch = 2

        def on_pair(vcont, freq):
            # chamado a cada par detectado durante a execução
            nonlocal mismatch_idx
            current_mismatch.append((vcont, freq))

            # Quando acumulamos os pontos esperados para um mismatch, gravamos o CSV
            if len(current_mismatch) >= points_per_mismatch:
                mismatch_idx += 1
                out_file = os.path.join(pvt_dir, f"mismatch_{mismatch_idx:02d}.csv")
                # grava os 2 pontos do mismatch
                write_csv(current_mismatch, out_file)

                # adiciona ao resumo global e atualiza o CSV resumo
                data.extend(current_mismatch)
                summary_csv = os.path.join(pvt_dir, f"{base}_all_points.csv")
                write_csv(data, summary_csv)

                # limpa buffer para o próximo mismatch
                current_mismatch.clear()

        output = run_spice_simulation_stream(spice_file, on_pair)
        if output is None:
            print(f'Erro ao executar {spice_file}, ngspice pode não estar instalado.')
            continue

        # salva log completo
        with open(log_path, 'w') as f:
            f.write(output)

        # Se houver pontos remanescentes no buffer do mismatch (menos que points_per_mismatch),
        # gravamos um CSV parcial para não perder dados
        try:
            if current_mismatch:
                mismatch_idx += 1
                out_file = os.path.join(pvt_dir, f"mismatch_{mismatch_idx:02d}.csv")
                write_csv(current_mismatch, out_file)
                data.extend(current_mismatch)
                summary_csv = os.path.join(pvt_dir, f"{base}_all_points.csv")
                write_csv(data, summary_csv)
                print(f"Aviso: mismatch parcial gravado ({len(current_mismatch)} pontos) -> {out_file}")
                current_mismatch.clear()
        except NameError:
            # variáveis não existem se o contexto mudou; ignore nesses casos
            pass

        if not data:
            print(f'Aviso: nenhum dado extraído de {spice_file} (ver {log_path})')
            continue

        total_points += len(data)
        print(f'✓ Processado: {spice_file} → {len(data)} pontos')
        print(f'✓ Resultados em: {pvt_dir}')

    print('\n' + '=' * 60)
    print(f'Total de pontos extraídos (todos arquivos): {total_points}')
    return True

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
