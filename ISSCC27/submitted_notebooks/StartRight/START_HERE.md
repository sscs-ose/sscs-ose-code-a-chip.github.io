# Start with the main notebook

Open **[StartRight.ipynb](StartRight.ipynb)**. It asks one question:
did reset restore a different state, or was the desired state already there?

The notebook starts with a small latch. It then checks saved simulations of
published circuits. You do not need to read every supporting study first.
[README.md](README.md) gives the setup. [Explore_reset.html](Explore_reset.html)
offers a saved-data preview without installation.

## Follow a result to its evidence

| Result | Code and evidence |
|---|---|
| A retained-state pass can leave restoration untested | Main steps 1 and 2; four new simulations; `reset_contract.py` checks the measured state and timing |
| An RC voltage prediction can agree while reset fails | Main step 4; two new simulations; [MECHANISM.md](MECHANISM.md) and `mechanism_evidence.py` |
| The same question applies to a published POR and flip-flop | Main step 5; `por_evidence.py` checks saved traces |
| Required behavior decides which controller is usable | Main step 7; `reference_evidence.py` checks 56 saved runs; `lesson_decision.py` makes the choice |
| The monitor can take another signal map | Main step 9; [REUSE.md](REUSE.md) gives the interface |

The original, guard and reference meet 3/7, 4/7 and 7/7 sampled requirements.
Those counts include storage tests and startup failures. They are not seven
exercised reset tests. The reference costs 40.3% more in one working storage
history and 19.8% less in a separate working analog interruption. Neither
comparison establishes lifetime energy use.

[Reference_tradeoff.ipynb](Reference_tradeoff.ipynb) explains the reference circuit.
[EVIDENCE.md](EVIDENCE.md) lists the supporting studies and unresolved runs.
The circuits and selection rule use established ideas. The contribution is the
explicit state check and reusable code. Hardware retention is unverified.
