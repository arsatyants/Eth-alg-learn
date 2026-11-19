# Eth-alg-learn

*Русская версия: [README.ru.md](README.ru.md)*

A learning project about the **Exponential Time Hypothesis (ETH)** and exponential-time algorithms.
It shows why an algorithm lowers the **base** of the exponent while an FPGA only changes the **constant**.
Every claim is checked three ways: mathematical derivation → Python experiment →
Verilog module simulated in Icarus Verilog.

**ETH (Impagliazzo–Paturi, 1999):** there is δ > 0 such that 3-SAT cannot be solved in time O(2^(δn)),
where n is the number of variables. Better algorithms can lower the base of the exponent
(2 → 1.839 → 1.334 → 1.307), but never down to 2^(o(n)).

## Notebooks

| Language | File |
|---|---|
| English | [`notebooks/eth_alg_learn_en.ipynb`](notebooks/eth_alg_learn_en.ipynb) |
| Русский | [`notebooks/eth_alg_learn.ipynb`](notebooks/eth_alg_learn.ipynb) |

Both are already executed, so plots and outputs render directly on GitHub.

## Contents

| # | Section | Key result |
|---|---|---|
| 1 | The exponential wall | an S-fold speedup adds only log_c S to n; a better algorithm multiplies n by ln c / ln c' |
| 2 | 3-SAT, ETH, SETH, Sparsification Lemma | phase transition at m/n ≈ 4.27 (experiment) |
| 3 | Branching and recurrences | 1 = Σ c^(−dᵢ): 1.839ⁿ, 1.618ⁿ, 1.466ⁿ; checked against polynomial roots |
| 4 | Brute force → backtracking → clause branching → DPLL | measured bases on random formulas: 2.05 → 1.39 → 1.11 → 1.08 |
| 5 | Schöning's algorithm | (4/3)ⁿ derived from a random walk; experiment |
| 6 | Subset Sum | naive O(n·2ⁿ), Gray code O(2ⁿ), meet-in-the-middle O(2^(n/2)) |
| 7 | FPGA: `sat_brute.v` | Icarus: cycles = 2^(n−LOGP), solution matches Python |
| 8 | FPGA: `ss_engine.v` | multiplexer vs LUTRAM: ~540 → ~140 LUT per engine (model) |
| 9 | FPGA done right: `bcp_unit.v` | DPLL trace → single-cycle BCP, 0 mismatches |
| 10 | The big picture and the ETH limit | "first the base, then the constant" |
| 11 | Exercises | |

## Layout

```
ethlearn/               Python library
  sat.py                3-SAT generators; brute force, backtracking, clause branching, DPLL (with trace), Schöning
  recurrence.py         branching number: bisection and characteristic-polynomial roots
  subset_sum.py         naive, Gray code, meet-in-the-middle, DP
  fpga.py               XC7Z010 time/resource model, .mem generation, Icarus runner
rtl/
  sat_brute.v           P = 2^LOGP cores, one 3-SAT assignment per clock per core
  ss_engine.v           Subset Sum engine: one subset per clock, Gray code, ±a table in LUTRAM
  ss_array.v            2^K engines split the mask space
  bcp_unit.v            Boolean Constraint Propagation over all clauses in one clock
tb/                     Icarus testbenches (tb_ss.v, tb_sat.v, tb_bcp.v)
tools/
  build_notebook.py     builds and runs the Russian notebook
  build_notebook_en.py  builds and runs the English notebook
  check_rtl.py          RTL regression against Python references
figures/                plots (Russian), figures/en/ — English
```

## Running

```bash
pip install -r requirements.txt
sudo apt install iverilog                     # sections 7–9
python3 tools/check_rtl.py                    # ALL PASS
jupyter lab notebooks/eth_alg_learn_en.ipynb
# or rebuild and execute from scratch (~2.5 min each):
python3 tools/build_notebook_en.py --execute
python3 tools/build_notebook.py --execute
```

## Hardware

Target board: 7Z-Lite (XC7Z010, 17,600 LUT6, 50 MHz crystal). The RTL is verified in simulation only (Icarus Verilog).
LUT figures in the notebooks come from a model; Vivado synthesis gives the exact numbers.
Comments in the RTL and Python sources are in Russian.
A board-ready version of the 3-SAT brute force with UART and Vivado scripts lives in
[`fpga-course/sat-bruteforce`](https://github.com/arsatyants/fpga-course/tree/master/sat-bruteforce).
