
from pathlib import Path
import shutil
import sys

# ============================================================
# DIRETÓRIOS
# ============================================================

# Considerando que o script está em reproducibility/pvtmm/
PROJECT_DIR = Path(__file__).resolve().parents[2]

SOURCE = PROJECT_DIR / "schematics" / "tb_vco_v5.spice"

DEST_DIR = Path(__file__).resolve().parent
DESTINATION = DEST_DIR / SOURCE.name

# ============================================================
# CÓPIA DO NETLIST
# ============================================================

def main():

    if not SOURCE.exists():
        sys.exit(f"Erro: arquivo não encontrado:\n{SOURCE}")

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SOURCE, DESTINATION)

    print("Netlist copiado com sucesso!")
    print(f"Origem:  {SOURCE}")
    print(f"Destino: {DESTINATION}")


if __name__ == "__main__":
    main()
