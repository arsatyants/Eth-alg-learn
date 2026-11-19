#!/usr/bin/env python3
"""Регрессия RTL: все три Verilog-модуля в Icarus против Python-эталонов.
Запуск из корня репозитория:  python3 tools/check_rtl.py"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pycosat  # noqa: E402

from ethlearn import fpga, sat, subset_sum as ss  # noqa: E402

fails = 0

for n, K, solv, seed in [(14, 0, True, 1), (14, 2, True, 2), (16, 3, True, 3), (16, 4, True, 4),
                         (14, 2, False, 5), (16, 3, False, 6)]:
    a, T = ss.random_instance(n, bits=30, solvable=solv, seed=seed)
    r = fpga.sim_subset_sum(a, T, K)
    ok = (r["found"] and ss.mask_sum(a, r["mask"]) == T) or (not solv and not r["found"]
                                                             and r["cycles"] == 2 ** (n - K) + 1)
    fails += not ok
    print(f"ss_array  n={n} K={K} solvable={solv}: {'OK' if ok else 'FAIL'} ({r['raw']})")

for n, logp, seed in [(14, 0, 300), (14, 2, 301), (14, 4, 302), (12, 3, 303)]:
    cnf = sat.random_3sat_ratio(n, 4.27, seed=seed)
    x, st = sat.brute_force(cnf, n)
    r = fpga.sim_sat(cnf, n, logp)
    if x is None:
        ok = (not r["sat"]) and r["cycles"] == 2 ** (n - logp)
    else:
        ok = r["sat"] and r["x"] == sum(b << i for i, b in enumerate(x))
    fails += not ok
    print(f"sat_brute n={n} LOGP={logp} {'SAT' if x else 'UNSAT'}: {'OK' if ok else 'FAIL'} ({r['raw']})")

n = 16
for seed in (7, 8, 9):
    cnf = sat.random_3sat_ratio(n, 4.27, seed=seed)
    tr = []
    sat.dpll(cnf, n, trace=tr)
    rng = random.Random(seed)
    tr += [(rng.getrandbits(n) | rng.getrandbits(n), rng.getrandbits(n)) for _ in range(100)]
    hw = fpga.sim_bcp(cnf, n, tr)
    bad = 0
    for (asg, val), h in zip(tr, hw):
        ref = fpga.bcp_reference(cnf, n, asg, val)
        bad += not (h[:3] == ref[:3] and (not ref[2] or h[3:] == ref[3:]))
    fails += bad > 0
    print(f"bcp_unit  seed={seed}: {len(hw)} векторов, расхождений {bad}")

print("ALL PASS" if fails == 0 else f"{fails} FAIL")
sys.exit(1 if fails else 0)
