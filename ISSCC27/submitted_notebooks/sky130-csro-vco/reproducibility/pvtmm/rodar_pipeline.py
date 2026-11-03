#!/usr/bin/env python3
"""Executa o fluxo em sequência, grava histórico e valida PVTs antes de prosseguir."""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "historico.log"
SCRIPTS = [
    "gerador.py",
    "sintonia.py",
    "analyzer.py",
    "graph_all_case_mismatch.py",
    "histograma.py",
]


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def log_parameter_space() -> None:
    try:
        import gerador
    except ImportError:
        log("Parâmetros de simulação: não foi possível importar gerador.py; usando defaults do pipeline.")
        return

    voltages = gerador.VOLTAGES
    temperatures = gerador.TEMPERATURES
    process = gerador.PROCESSES
    count_v = len(voltages)
    count_t = len(temperatures)
    count_p = len(process)
    total_variants = count_p * count_v * count_t
    log(
        f"Parâmetros de simulação: processos={process}, VDD={voltages[0]}..{voltages[-1]} "
        f"em passo de 10mV ({count_v} valores), temperatura={temperatures[0]}C..{temperatures[-1]}C "
        f"({count_t} valores), total de variantes={total_variants}."
    )


def _is_complete_pvt_dir(path: Path) -> bool:
    try:
        from sintonia import is_complete_pvt_dir
    except ImportError:
        return False
    return is_complete_pvt_dir(path)


def check_gerador_done() -> bool:
    variants_dir = ROOT / "spice_variants"
    if not variants_dir.exists():
        return False
    return any(variants_dir.glob("*.spice"))


def check_sintonia_done() -> bool:
    results_dir = ROOT / "spice_results"
    if not results_dir.exists():
        return False

    pvt_dirs = sorted(path for path in results_dir.iterdir() if path.is_dir())
    if not pvt_dirs:
        return False

    return all(_is_complete_pvt_dir(path) for path in pvt_dirs)


def check_analyzer_done() -> bool:
    result_file = ROOT / "ranked_vcont0.csv"
    return result_file.exists() and result_file.stat().st_size > 0


def check_graph_done() -> bool:
    output_dir = ROOT / "mismatch_50_lines_all_cases"
    if not output_dir.exists():
        return False
    return any(output_dir.glob("*.png"))


STEP_CHECKERS = {
    "gerador.py": check_gerador_done,
    "sintonia.py": check_sintonia_done,
    "analyzer.py": check_analyzer_done,
    "graph_all_case_mismatch.py": check_graph_done,
    "histograma.py": check_graph_done,
}


def should_run_script(script_name: str) -> bool:
    checker = STEP_CHECKERS.get(script_name)
    if checker is None:
        return True

    if checker():
        log(f"Pulando: {script_name} (já concluído).")
        return False
    return True


def validate_pvt_directories() -> list[Path]:
    results_dir = ROOT / "spice_results"
    if not results_dir.exists():
        log("Validação de PVT: pasta spice_results não existe ainda.")
        return []

    pvt_dirs = sorted(path for path in results_dir.iterdir() if path.is_dir())
    if not pvt_dirs:
        log("Validação de PVT: nenhuma pasta de PVT localizada em spice_results.")
        return []

    invalid_dirs = []
    for pvt_dir in pvt_dirs:
        ok = _is_complete_pvt_dir(pvt_dir)
        log(f"PVT {pvt_dir.name}: {'OK' if ok else 'INCOMPLETO'}")
        if not ok:
            invalid_dirs.append(pvt_dir)

    return invalid_dirs


def run_script(script_name: str) -> None:
    script_path = ROOT / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {script_path}")

    log(f"Iniciando etapa: {script_name}")
    if script_name == "gerador.py":
        log("Abrindo template tb_vco_v5.spice e substituindo os campos de process, VDD e temperatura.")
        log("Gerando arquivos .spice para cada combinação de processo, tensão e temperatura do PVT.")
    elif script_name == "sintonia.py":
        log("Executando simulação ngspice por PVT e gravando mismatch_*.csv e *_all_points.csv.")
        log("A saída em tempo real da simulação será exibida abaixo para acompanhar o progresso de cada PVT.")
    elif script_name == "analyzer.py":
        log("Leitura dos resultados finais e geração do ranked_vcont0.csv com o ranqueamento por frequência.")
    elif script_name == "graph_all_case_mismatch.py":
        log("Gerando o gráfico de todos os mismatchs por caso.")
    elif script_name == "histograma.py":
        log("Gerando histogramas finais e métricas dos resultados de frequência.")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        check=False,
        text=True,
    )

    if result.stdout:
        print(result.stdout, end="")
        log(f"Saída de {script_name}:\n{result.stdout.strip()}")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
        log(f"Erros/avisos de {script_name}:\n{result.stderr.strip()}")

    if result.returncode != 0:
        raise SystemExit(f"{script_name} falhou com código de saída {result.returncode}.")

    log(f"Etapa concluída com sucesso: {script_name}")


def main() -> None:
    LOG_FILE.write_text("", encoding="utf-8")
    log("=== Início do pipeline PVT ===")
    log_parameter_space()

    parser = argparse.ArgumentParser(description="Executa o pipeline do PVT, pulando etapas concluídas.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Força a reexecução de todas as etapas, mesmo as já concluídas.",
    )
    args = parser.parse_args()

    for script_name in SCRIPTS:
        if args.force:
            run_script(script_name)
            if script_name == "sintonia.py":
                invalid_dirs = validate_pvt_directories()
                if invalid_dirs:
                    raise SystemExit(
                        f"Validação do PVT falhou: diretórios incompletos: "
                        + ", ".join(d.name for d in invalid_dirs)
                    )
            continue

        if should_run_script(script_name):
            run_script(script_name)
            if script_name == "sintonia.py":
                invalid_dirs = validate_pvt_directories()
                if invalid_dirs:
                    raise SystemExit(
                        f"Validação do PVT falhou: diretórios incompletos: "
                        + ", ".join(d.name for d in invalid_dirs)
                    )

    log("=== Pipeline concluído com sucesso ===")
    log(f"Log salvo em: {LOG_FILE}")
    print("\nFluxo concluído com sucesso.")


if __name__ == "__main__":
    main()
