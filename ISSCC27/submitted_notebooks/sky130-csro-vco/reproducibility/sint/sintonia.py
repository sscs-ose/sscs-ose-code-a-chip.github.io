"""
Script para rodar simulação SPICE e gerar CSV com valores de Vcont e Freq
"""

import subprocess
import re
import csv
import os

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

def main():
    # Define caminhos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    spice_file = os.path.join(project_dir, 'schematics', 'tb_vco_v3.spice')
    output_csv = os.path.join(script_dir, 'resultado.csv')
    output_log = os.path.join(script_dir, 'ngspice_output.log')
    
    print("=" * 60)
    print("Simulação SPICE - VCO Tuning Curve")
    print("=" * 60)
    
    # Verifica se arquivo SPICE existe
    if not os.path.exists(spice_file):
        print(f"Erro: Arquivo {spice_file} não encontrado")
        return False
    
    print(f"Executando: {spice_file}")
    print(f"Saída será salva em: {output_log}")
    print("-" * 60)
    
    # Executa simulação
    output = run_spice_simulation(spice_file)
    
    if output is None:
        return False
    
    # Salva output para debug
    with open(output_log, 'w') as f:
        f.write(output)
    print(f"✓ Log salvo em: {output_log}")
    
    print("Processando saída...")
    
    # Parse dos dados
    data = parse_output(output)
    
    if not data:
        print("Aviso: Nenhum dado foi extraído da simulação")
        print("\nPrimeiras 100 linhas da saída:")
        print("\n".join(output.split('\n')[:100]))
        print("\n" + "=" * 60)
        return False
    
    print(f"✓ Dados extraídos: {len(data)} pontos")
    
    # Escreve CSV
    success = write_csv(data, output_csv)
    
    if success:
        # Mostra primeiros e últimos valores
        print("\nPrimeiros 5 pontos:")
        for vcont, freq in data[:5]:
            print(f"  Vcont: {vcont:.3f} V → Freq: {freq:.6e} Hz ({freq/1e9:.3f} GHz)")
        
        print("\nÚltimos 5 pontos:")
        for vcont, freq in data[-5:]:
            print(f"  Vcont: {vcont:.3f} V → Freq: {freq:.6e} Hz ({freq/1e9:.3f} GHz)")
    
    print("=" * 60)
    return success

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
    
    # Se passar arquivo como argumento, testa com esse arquivo
    if len(sys.argv) > 1:
        success = test_with_log_file(sys.argv[1])
    else:
        success = main()
    sys.exit(0 if success else 1)
