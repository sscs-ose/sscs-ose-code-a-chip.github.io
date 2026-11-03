# Distributed openEMS runs (transformers: 4 ports, spirals: 2 ports, from INFO/{i}.log line 2) via Ray.
# Usage: python emx_sim.py start end            (index range)
#        python emx_sim.py --list i1,i2,...      (explicit indices, e.g. verification layouts; @file reads them from a file)
# EXCLUDE_IPS="ip1,ip2" keeps tasks away from broken/unreachable nodes; a failed task does not abort the batch.
from environment import configure
BUDGET = configure()
import ray
import os
import socket
import sys
import shlex

from xfmr_schema import read_info, port_layers

DATA_PATH = os.path.dirname(os.path.abspath(__file__))
NTHREADS = os.environ.get("OPENEMS_THREADS", str(min(4, BUDGET)))
if not 1 <= int(NTHREADS) <= BUDGET:
	raise ValueError(f"OPENEMS_THREADS must be in 1..{BUDGET}")
EM_ENV = {k: os.environ[k] for k in ('EM_MARGIN', 'EM_ENERGY', 'EM_SKIP_PORT') if k in os.environ}
OUTDIR = os.environ.get('EM_OUTDIR', f'{DATA_PATH}/SPData')
TAG = os.environ.get('EM_TAG', '')
ray.init(address=os.environ.get("RAY_ADDRESS"), **({} if os.environ.get("RAY_ADDRESS") else {"num_cpus": BUDGET}), runtime_env={"env_vars": {"OPENEMS_THREADS": NTHREADS, **EM_ENV}})

excl = {socket.gethostbyname(h.strip()) for h in os.environ.get("EXCLUDE_IPS", "").split(',') if h.strip()}
bad = [n['NodeID'] for n in ray.nodes() if n['Alive'] and n['NodeManagerAddress'] in excl]
opts = dict(num_cpus=int(NTHREADS), max_retries=3)
if bad:
	opts['label_selector'] = {'ray.io/node-id': f"!in({','.join(bad)})"}
	print('excluding nodes', sorted(excl))


def simulation_metadata(index):
	"""Read the device family and actual port landing metal without changing port polarity."""
	info = f'{DATA_PATH}/INFO/{index}.log'
	if not os.path.exists(info):
		info = f'{DATA_PATH}/INFO/{index}.json'
	with open(info) as f:
		lines = f.read().splitlines()
	if any(line.strip() == 'spiral' for line in lines[1:]):
		return 2, 'TopMetal2'
	params = read_info(info)
	if params['topology'] == 2 and not params['port_backing']:
		raise ValueError(f'{info}: v3 ports have no Metal4 backing; regenerate the layout with --port-backing before EM simulation')
	metals = port_layers(params)
	if len(set(metals)) != 1:
		raise ValueError(f'{info}: mixed port landing metals are not supported by this EM front end')
	return 4, metals[0]


def nports(index):
	return simulation_metadata(index)[0]


def out_name(index):
	return f"{OUTDIR}/{index}.s{nports(index)}p"


@ray.remote
def emx_task(index):
	budget = configure()
	if int(NTHREADS) > budget:
		raise ValueError("EM threads exceed the worker CPU budget")
	d = DATA_PATH
	out = out_name(index)
	if os.path.exists(out):
		return True
	m = f"{index}{TAG}"
	os.makedirs(os.path.dirname(out), exist_ok=True)
	count, metal = simulation_metadata(index)
	command = [sys.executable, f'{d}/simulator_openems.py', '-g', f'{d}/GDS/{index}.gds', '-s', out,
			   '-x', f'{d}/SG13G2.xml', '-m', m, '-r', d, '--nports', str(count), '--port-metal', metal]
	os.system(' '.join(shlex.quote(arg) for arg in command) + f' > {shlex.quote(f"{d}/EMLOG/{m}.log")} 2>&1')
	os.system(f"rm -rf /tmp/ray_cache/TIADN_{m}_sim")
	return os.path.exists(out)


if '--list' in sys.argv:
	arg = sys.argv[sys.argv.index('--list') + 1]
	indices = [int(i) for i in (open(arg[1:]).read() if arg.startswith('@') else arg).split(',')]
else:
	indices = list(range(int(sys.argv[1]) if len(sys.argv) > 1 else 0, int(sys.argv[2]) if len(sys.argv) > 2 else 1500))
# Bounded in-flight window: submitting thousands at once made worker startup time out (RaySystemError).
WINDOW = int(os.environ.get("EMX_WINDOW", "30"))
todo = [i for i in indices if not os.path.exists(out_name(i))]
total = len(indices)
refs, result, pending = {}, {i: True for i in indices if i not in todo}, []
tries = {}
while todo or pending:
	while todo and len(pending) < WINDOW:
		i = todo.pop(0)
		r = emx_task.options(**opts).remote(i)
		refs[r] = i
		pending.append(r)
	done, pending = ray.wait(pending, num_returns=1)
	idx = refs[done[0]]
	try:
		result[idx] = ray.get(done[0])
	except Exception as e:
		tries[idx] = tries.get(idx, 0) + 1
		print(f'task {idx} failed (try {tries[idx]}): {type(e).__name__}: {str(e)[:300]}', flush=True)
		if tries[idx] < 3:
			todo.append(idx)
			continue
		result[idx] = False
	if len(result) % 50 == 0:
		print(f'{len(result)}/{total} finished, {sum(result.values())} ok', flush=True)

with open(os.path.join(DATA_PATH, 'Failed_List.txt'), 'a') as fi:
	for i in sorted(result):
		if not result[i]:
			fi.write(str(i) + '\n')
print("Done", sum(result.values()), "/", len(result))
