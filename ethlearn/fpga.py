"""FPGA-часть: модель производительности и ресурсов, генерация .mem и запуск
Verilog-модулей из rtl/ в Icarus Verilog (iverilog + vvp).

Числа для Zynq-7010 (XC7Z010, плата 7Z-Lite): 17 600 LUT6, 35 200 FF,
60 блоков BRAM36 (2.1 Мбит), 80 DSP48E1. Тактовая частота PL — 50 МГц от кварца
или выше через MMCM.
"""
from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTL = os.path.join(ROOT, "rtl")
TB = os.path.join(ROOT, "tb")

ZYNQ7010 = {"LUT": 17_600, "FF": 35_200, "BRAM_kbit": 2_100, "DSP": 80}


# --------------------------------------------------------------------------- модель времени
def extra_vars(speedup: float, base: float = 2.0) -> float:
    """Ускорение в S раз при росте c^n позволяет взять n больше на log_c(S)."""
    return math.log(speedup) / math.log(base)


def seconds(ops: float, rate: float) -> float:
    return ops / rate


_UNITS = {
    "ru": ("нс", "мкс", "мс", "с", "мин", "ч", "дн", "лет", "× возраст Вселенной"),
    "en": ("ns", "µs", "ms", "s", "min", "h", "days", "years", "× age of the Universe"),
}


def fmt_time(s: float, lang: str = "ru") -> str:
    """Человекочитаемое время. lang='ru' | 'en'."""
    ns, us, ms, sec, mi, h, d, y, univ = _UNITS[lang]
    year = 3.156e7
    universe = 13.8e9 * year
    if s < 1e-6:
        return f"{s*1e9:.1f} {ns}"
    if s < 1e-3:
        return f"{s*1e6:.1f} {us}"
    if s < 1:
        return f"{s*1e3:.1f} {ms}"
    if s < 60:
        return f"{s:.1f} {sec}"
    if s < 3600:
        return f"{s/60:.1f} {mi}"
    if s < 86400:
        return f"{s/3600:.1f} {h}"
    if s < year:
        return f"{s/86400:.1f} {d}"
    if s < universe:
        return f"{s/year:.3g} {y}"
    return f"{s/universe:.3g} {univ}"


# --------------------------------------------------------------------------- модель ресурсов
@dataclass
class EngineCost:
    name: str
    lut: int
    ff: int

    def fit(self, lut_budget: int = int(ZYNQ7010["LUT"] * 0.8)) -> int:
        """Сколько движков влезает при заполнении 80% LUT (выше — тайминг и трассировка)."""
        return lut_budget // self.lut


def ss_engine_cost(NL: int, W: int, lutram: bool) -> EngineCost:
    """Грубая оценка одного движка Subset Sum в LUT6 серии 7.

    - мультиплексор NL:1 на бит: NL <= 4 -> 1 LUT, <= 8 -> 2 (LUT+MUXF7),
      <= 16 -> 4, <= 32 -> ~10 (с учётом сумматорной логики выбора знака)
    - таблица dtab в RAM64X1: 1 LUT на бит, пока 2*NL <= 64
    - сумматор W бит: W LUT (+ CARRY4, они бесплатны по LUT)
    - компаратор sum == T: ~W/3 LUT
    - ctz-шифратор NL->log2 NL: ~NL/2 LUT; счётчик NL бит: NL LUT
    """
    if lutram:
        sel = W * math.ceil(2 * NL / 64)
    else:
        per_bit = 1 if NL <= 4 else 2 if NL <= 8 else 4 if NL <= 16 else 10
        sel = per_bit * W + W                 # +W: выбор +a/-a
    lut = sel + W + math.ceil(W / 3) + math.ceil(NL / 2) + NL
    ff = W + NL + NL + 4
    return EngineCost("ss_engine (LUTRAM)" if lutram else "ss_engine (mux)", lut, ff)


def sat_core_cost(M: int) -> EngineCost:
    """Ядро перебора 3-SAT: каждая клауза — функция 3 бит назначения (1 LUT, а часть
    клауз схлопывается константами младших бит). Дерево AND из M входов: ~M/5 LUT6."""
    return EngineCost("sat core", M + math.ceil(M / 5), 0)


def bcp_cost(M: int) -> EngineCost:
    """BCP-блок: на клаузу 6 входов (assigned+value трёх переменных) -> статус
    sat/conflict/unit: ~3 LUT, плюс приоритетный шифратор unit-клаузы ~M/2."""
    return EngineCost("bcp_unit", 3 * M + M // 2, 0)


# --------------------------------------------------------------------------- .mem файлы
def _hex(v: int, bits: int) -> str:
    return format(v & ((1 << bits) - 1), "0{}x".format((bits + 3) // 4))


def write_ss_mem(a: Sequence[int], T: int, K: int, W: int, outdir: str) -> None:
    """dtab.mem (для младших NL элементов) + base.mem (2^K базовых сумм) + T.mem."""
    N = len(a)
    NL = N - K
    with open(os.path.join(outdir, "dtab.mem"), "w") as f:
        for i in range(NL):
            f.write(_hex(-a[i], W) + "\n")      # dir = 0: элемент вышел
            f.write(_hex(+a[i], W) + "\n")      # dir = 1: элемент вошёл
    with open(os.path.join(outdir, "base.mem"), "w") as f:
        for k in range(1 << K):
            s = sum(a[NL + i] for i in range(K) if k >> i & 1)
            f.write(_hex(s, W) + "\n")
    with open(os.path.join(outdir, "T.mem"), "w") as f:
        f.write(_hex(T, W) + "\n")


def write_sat_mem(cnf, n: int, outdir: str) -> None:
    from .sat import to_masks
    pos, neg = to_masks(cnf, n)
    with open(os.path.join(outdir, "pos.mem"), "w") as f:
        f.writelines(_hex(p, n) + "\n" for p in pos)
    with open(os.path.join(outdir, "neg.mem"), "w") as f:
        f.writelines(_hex(q, n) + "\n" for q in neg)


def write_bcp_mem(cnf, n: int, vectors, outdir: str) -> None:
    vw = max(1, math.ceil(math.log2(n)))
    with open(os.path.join(outdir, "lits.mem"), "w") as f:
        for cl in cnf:
            for l in cl:
                word = (abs(l) - 1) | ((1 if l < 0 else 0) << vw)
                f.write(_hex(word, vw + 1) + "\n")
    with open(os.path.join(outdir, "vec.mem"), "w") as f:
        for asg, val in vectors:
            f.write(_hex(asg, n) + "\n" + _hex(val, n) + "\n")


# --------------------------------------------------------------------------- запуск Icarus
def have_iverilog() -> bool:
    return shutil.which("iverilog") is not None and shutil.which("vvp") is not None


def _run(top: str, srcs: List[str], params: Dict[str, int], workdir: str) -> str:
    out = os.path.join(workdir, "sim.vvp")
    cmd = ["iverilog", "-g2005", "-s", top, "-o", out]
    for k, v in params.items():
        cmd += ["-P", f"{top}.{k}={v}"]
    cmd += srcs
    subprocess.run(cmd, check=True, cwd=workdir, capture_output=True, text=True)
    r = subprocess.run(["vvp", "-n", out], check=True, cwd=workdir,
                       capture_output=True, text=True)
    return r.stdout


def sim_subset_sum(a: Sequence[int], T: int, K: int, W: int = 40,
                   workdir: Optional[str] = None) -> Dict:
    wd = workdir or tempfile.mkdtemp(prefix="ss_")
    write_ss_mem(a, T, K, W, wd)
    txt = _run("tb_ss",
               [os.path.join(TB, "tb_ss.v"), os.path.join(RTL, "ss_array.v"),
                os.path.join(RTL, "ss_engine.v")],
               {"N": len(a), "K": K, "W": W}, wd)
    m = re.search(r"RESULT found=(\d) mask=([0-9a-fx]+) cycles=(\d+)", txt)
    return {"found": m.group(1) == "1", "mask": int(m.group(2), 16),
            "cycles": int(m.group(3)), "raw": txt.strip()}


def sim_sat(cnf, n: int, logp: int, workdir: Optional[str] = None) -> Dict:
    wd = workdir or tempfile.mkdtemp(prefix="sat_")
    write_sat_mem(cnf, n, wd)
    txt = _run("tb_sat",
               [os.path.join(TB, "tb_sat.v"), os.path.join(RTL, "sat_brute.v")],
               {"N": n, "M": len(cnf), "LOGP": logp}, wd)
    m = re.search(r"RESULT sat=(\d) x=([0-9a-fx]+) cycles=(\d+)", txt)
    return {"sat": m.group(1) == "1", "x": int(m.group(2), 16),
            "cycles": int(m.group(3)), "raw": txt.strip()}


def sim_bcp(cnf, n: int, vectors, workdir: Optional[str] = None) -> List[tuple]:
    wd = workdir or tempfile.mkdtemp(prefix="bcp_")
    write_bcp_mem(cnf, n, vectors, wd)
    txt = _run("tb_bcp",
               [os.path.join(TB, "tb_bcp.v"), os.path.join(RTL, "bcp_unit.v")],
               {"N": n, "M": len(cnf), "NV": len(vectors)}, wd)
    rows = []
    for line in txt.splitlines():
        if line.startswith("V "):
            _, i, c, s, u, uv, ul = line.split()
            rows.append((int(c), int(s), int(u), int(uv), int(ul)))
    return rows


def bcp_reference(cnf, n: int, asg: int, val: int) -> tuple:
    """То же, что bcp_unit.v, на Python — для сверки."""
    conflict = False
    all_sat = True
    unit = None
    for cl in cnf:
        sat = False
        free = []
        for l in cl:
            v = abs(l) - 1
            if asg >> v & 1:
                if ((val >> v & 1) == 1) == (l > 0):
                    sat = True
            else:
                free.append(l)
        if not sat:
            all_sat = False
            if not free:
                conflict = True
            elif len(free) == 1 and unit is None:
                unit = free[0]
    if conflict or unit is None:
        return (int(conflict), int(all_sat), 0, None, None)
    return (0, int(all_sat), 1, abs(unit) - 1, 1 if unit > 0 else 0)
