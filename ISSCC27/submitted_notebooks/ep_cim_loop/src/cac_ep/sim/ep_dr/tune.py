"""단계 4: Optuna 로 β·G_bz 고르기 (README §4). --space clamp: β·clamp 레일 오프셋 V_B·직렬 R_ser 고르기 (G_bz 고정).

목적값: val 정확도의 bit 평균. --objective last = 마지막 평가 값 (올랐다 무너지는 설정을 피함, 단계 4),
  best = 평가 중 최고 값 (val 최고점에서 멈추는 운용, 10/23 사용자 "최고점 가중치로 test 도달하고 학습을 끊어버리면 되니까").
  val 은 학습 셋에서 뗀 n_val 장 — test 는 고를 때 쓰지 않는다.
예산: 시행마다 학습 n_train 장 1 epoch, eval_every 마다 val 평가 → MedianPruner 로 일찍 끊음 (best 면 그때까지 최고 값으로).
탐색 beta_gbz: β 10 nA–100 µA (log), G_bz 0.3–300 µS (log). 시작점 β 0.1 / 1 / 10 µA × G_bz 10 µS (Oh 2023 기본 β 포함).
탐색 clamp: β 1–100 µA (log), V_B 0.15–0.38 V, R_ser 10–1000 Ω (log). 범위는 정적 계산 (README §8 clamp) — V_B < 0.15 V 는
  clamp 가 걸리지 않고, 0.38 V 를 넘으면 대기 전류가 가지당 수십 µA 가 된다. 시작점 β 38 µA × (V_B, R_ser) = (0.25, 30), (0.30, 30), (0.30, 100).
a = 0.3 V, R_on = 1.2 kΩ 은 train.py 기본값 고정.
여러 worker 가 journal 하나를 함께 쓴다.

사용: python tune.py --study s4 --n_total 48 --worker 0
      python tune.py --study c1 --space clamp --bits 5 --g_bz 22.12e-6 --objective best --n_total 60 --worker 0
      (hidden 만 tanh: 위에 --no_out_clamp)
"""
import argparse
from pathlib import Path

import numpy as np
import optuna
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend, JournalFileOpenLock
from optuna.trial import TrialState

from train import build_parser, train


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--study', default='s4')
    ap.add_argument('--n_total', type=int, default=48, help='완료 + 가지치기 시행 수 합계')
    ap.add_argument('--worker', type=int, default=0)
    ap.add_argument('--bits', type=int, nargs='+', default=[3, 4, 5, 6])
    ap.add_argument('--n_train', type=int, default=6000)
    ap.add_argument('--n_val', type=int, default=1000)
    ap.add_argument('--eval_every', type=int, default=1500)
    ap.add_argument('--space', choices=['beta_gbz', 'clamp'], default='beta_gbz')
    ap.add_argument('--g_bz', type=float, default=22.12e-6, help='--space clamp 에서 고정하는 G_bz [S] (단계 4 최고)')
    ap.add_argument('--objective', choices=['last', 'best'], default='last')
    ap.add_argument('--no_out_clamp', action='store_true', help='train.py 로 넘김: 출력 노드 다이오드 없음 (hidden 만 tanh)')
    o = ap.parse_args()

    root = Path(__file__).parent / 'out' / 'optuna' / o.study
    root.mkdir(parents=True, exist_ok=True)
    path = str(root / 'journal.log')
    storage = JournalStorage(JournalFileBackend(path, lock_obj=JournalFileOpenLock(path)))
    study = optuna.create_study(study_name=o.study, storage=storage, direction='maximize', load_if_exists=True,
                                sampler=optuna.samplers.TPESampler(seed=o.worker, n_startup_trials=10),
                                pruner=optuna.pruners.MedianPruner(n_startup_trials=8, n_warmup_steps=o.eval_every))
    if o.worker == 0 and not study.trials:
        if o.space == 'beta_gbz':
            for beta in (1e-7, 1e-6, 1e-5):
                study.enqueue_trial({'beta': beta, 'g_bz': 1e-5})
        else:
            for v_b, r_ser in ((0.25, 30.0), (0.30, 30.0), (0.30, 100.0)):
                study.enqueue_trial({'beta': 38.12e-6, 'v_b': v_b, 'r_ser': r_ser})

    def objective(trial):
        if o.space == 'beta_gbz':
            beta = trial.suggest_float('beta', 1e-8, 1e-4, log=True)
            g_bz = trial.suggest_float('g_bz', 3e-7, 3e-4, log=True)
            extra = []
        else:
            beta = trial.suggest_float('beta', 1e-6, 1e-4, log=True)
            g_bz = o.g_bz
            extra = ['--v_b', repr(trial.suggest_float('v_b', 0.15, 0.38)),
                     '--r_ser', repr(trial.suggest_float('r_ser', 10.0, 1000.0, log=True))]
        a = build_parser().parse_args([
            '--bits', *map(str, o.bits), '--seeds', '0', '--epochs', '1', '--beta', repr(beta), '--g_bz', repr(g_bz),
            '--n_train', str(o.n_train), '--n_val', str(o.n_val), '--eval_every', str(o.eval_every),
            '--tag', f'optuna/{o.study}/t{trial.number:03d}', *extra, *(['--no_out_clamp'] if o.no_out_clamp else [])])
        run_max = None

        def report(step, acc):
            nonlocal run_max
            run_max = acc if run_max is None else np.maximum(run_max, acc)
            trial.report(float((run_max if o.objective == 'best' else acc).mean()), step)
            if trial.should_prune():
                raise optuna.TrialPruned()

        r = train(a, report)
        for n, v, bv, te in zip(o.bits, r['acc_last'], r['best'], r['test_at_best']):
            trial.set_user_attr(f'val_last_{n}b', float(v))
            trial.set_user_attr(f'val_best_{n}b', float(bv))
            trial.set_user_attr(f'test_at_best_{n}b', float(te))
        return float((r['best'] if o.objective == 'best' else r['acc_last']).mean())

    study.optimize(objective, callbacks=[optuna.study.MaxTrialsCallback(
        o.n_total, states=(TrialState.COMPLETE, TrialState.PRUNED))])


if __name__ == '__main__':
    main()
