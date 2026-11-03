#!/usr/bin/env python3
"""
Gera 45 arquivos substituindo os campos {voltage}, {temperature} e {process}
no arquivo de template `tb_vco_v5.spice`.

Cria a pasta `spice_variants` no mesmo diretório e salva os arquivos gerados lá.
"""

import os
from itertools import product

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, 'tb_vco_v5.spice')
OUT_DIR = os.path.join(SCRIPT_DIR, 'spice_variants')

PROCESSES = ['tt_mm']
VOLTAGES = [
    '1.70V', '1.71V', '1.72V', '1.73V', '1.74V',
    '1.75V', '1.76V', '1.77V', '1.78V', '1.79V',
    '1.80V', '1.81V', '1.82V', '1.83V', '1.84V',
    '1.85V', '1.86V', '1.87V', '1.88V', '1.89V'
]

TEMPERATURES = [
    '-25', '-20', '-15', '-10', '-5',
    '0', '5', '10', '15', '20',
    '25', '30', '35', '40', '45',
    '50', '55', '60', '65', '70',
    '75', '80', '85'
]


def _sanitize_voltage(v: str) -> str:
	"""Transforma '1.71V' -> '1p71V' para nomes de arquivo seguros."""
	return v.replace('.', 'p').replace(' ', '')


def _make_filename(proc: str, volt: str, temp: str) -> str:
	sv = _sanitize_voltage(volt)
	return f"tb_vco_v5_{proc}_V{sv}_T{temp}C.spice"


def main():
	if not os.path.isfile(TEMPLATE_PATH):
		raise SystemExit(f"Template não encontrado: {TEMPLATE_PATH}")

	os.makedirs(OUT_DIR, exist_ok=True)

	with open(TEMPLATE_PATH, 'r') as f:
		template = f.read()

	total = 0
	for proc, volt, temp in product(PROCESSES, VOLTAGES, TEMPERATURES):
		# calcula metade da tensão em formato numérico, caindo para fallback textual se parse falhar
		def _half_voltage(vstr: str) -> str:
			vs = vstr.strip()
			unit = ''
			if vs.endswith('V') or vs.endswith('v'):
				unit = 'V'
				vs = vs[:-1].strip()
			try:
				val = float(vs)
				half = val / 2.0
				# formata sem zeros desnecessários
				hs = ('{:.6f}'.format(half)).rstrip('0').rstrip('.')
				return hs + unit
			except Exception:
				# se não for possível parsear, usa expressão com divisão para SPICE
				return f"({vstr}/2)"

		half_volt = _half_voltage(volt)

		# substitui {voltage} por metade apenas nas linhas de "meas tran"; nas outras, usa a tensão completa
		lines = template.split('\n')
		new_lines = []
		for line in lines:
			if 'meas tran' in line:
				new_lines.append(line.replace('{voltage}', half_volt))
			else:
				new_lines.append(line.replace('{voltage}', volt))

		content = '\n'.join(new_lines)
		if template.endswith('\n'):
			content += '\n'

		content = content.replace('{process}', proc).replace('{temperature}', temp)

		fname = _make_filename(proc, volt, temp)
		outpath = os.path.join(OUT_DIR, fname)
		with open(outpath, 'w') as outf:
			outf.write(content)
		total += 1

	print(f"Gerados {total} arquivos em: {OUT_DIR}")


if __name__ == '__main__':
	main()

