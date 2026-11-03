
#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys
import shutil

# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Diretório do projeto: dois níveis acima de reproducibility/sinal
PROJECT_DIR = Path(__file__).resolve().parents[2]

SIGNAL_DIR = Path(__file__).resolve().parent

NETLIST = PROJECT_DIR / "schematics" / "tb_vco_v1.spice"

# Nome do CSV produzido pelo wrdata no netlist
CSV_NAME = "tb_vco_v1.csv"

# ============================================================
# VERIFICAÇÕES
# ============================================================

def main():

    if not NETLIST.exists():
        sys.exit(f"Erro: netlist não encontrado:\n{NETLIST}")

    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)

    ngspice = shutil.which("ngspice")

    if ngspice is None:
        sys.exit("Erro: ngspice não encontrado no PATH.")

    print(f"Diretório de trabalho: {SIGNAL_DIR}")
    print(f"Netlist: {NETLIST}")

    # ========================================================
    # EXECUÇÃO DA SIMULAÇÃO
    # ========================================================

    result = subprocess.run(
        [ngspice, "-b", str(NETLIST)],
        cwd=SIGNAL_DIR,
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.stderr:
        print("Mensagens do ngspice:")
        print(result.stderr)

    if result.returncode != 0:
        sys.exit(
            f"Erro: ngspice terminou com código {result.returncode}."
        )

    # ========================================================
    # VERIFICAÇÃO DO CSV
    # ========================================================

    csv_path = SIGNAL_DIR / CSV_NAME

    if not csv_path.exists():
        sys.exit(
            "Erro: a simulação terminou, mas o CSV não foi encontrado.\n"
            f"Arquivo esperado: {csv_path}"
        )

    if csv_path.stat().st_size == 0:
        sys.exit("Erro: o CSV foi gerado, mas está vazio.")

    print("\nSimulação concluída com sucesso!")
    print(f"CSV gerado em:\n{csv_path}")
    print(f"Tamanho: {csv_path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
