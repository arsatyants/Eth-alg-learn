"""3-SAT: генераторы и решатели со счётчиками работы.

Все решатели возвращают (решение | None, статистика). Решение — список 0/1 длины n
(индекс i соответствует переменной i+1). Статистика — число проверенных назначений,
узлов дерева поиска или переворотов, чтобы сравнивать именно объём работы, а не
скорость интерпретатора Python.
"""
from __future__ import annotations

import random
from typing import List, Optional, Sequence, Tuple

import numpy as np

Clause = Tuple[int, ...]
CNF = List[Clause]


# --------------------------------------------------------------------------- генерация
def random_ksat(n: int, m: int, k: int = 3, seed: Optional[int] = None) -> CNF:
    """Случайная k-КНФ: m клауз, в каждой k разных переменных со случайными знаками."""
    n, m = int(n), int(m)
    rng = random.Random(None if seed is None else int(seed))
    cnf = []
    for _ in range(m):
        vs = rng.sample(range(1, n + 1), k)
        cnf.append(tuple(v if rng.random() < 0.5 else -v for v in vs))
    return cnf


def random_3sat_ratio(n: int, ratio: float = 4.27, seed: Optional[int] = None) -> CNF:
    return random_ksat(int(n), int(round(float(ratio) * int(n))), 3, seed)


def planted_3sat(n: int, m: int, seed: Optional[int] = None) -> Tuple[CNF, List[int]]:
    """Выполнимая формула: прячем решение x* и берём только клаузы, которые оно выполняет."""
    rng = random.Random(seed)
    x = [rng.randint(0, 1) for _ in range(n)]
    cnf = []
    while len(cnf) < m:
        vs = rng.sample(range(1, n + 1), 3)
        cl = tuple(v if rng.random() < 0.5 else -v for v in vs)
        if satisfies_clause(cl, x):
            cnf.append(cl)
    return cnf, x


def pigeonhole(n: int) -> Tuple[CNF, int]:
    """Принцип Дирихле PHP_n: n+1 голубей, n ящиков — формула всегда невыполнима.

    Переменная p(i,j) = «голубь i в ящике j», номер i*n + j + 1, всего N = n(n+1).
      - каждый голубь где-то сидит:      (p(i,0) ∨ ... ∨ p(i,n-1))   — n+1 клауз ширины n
      - в ящике не больше одного голубя: (¬p(i,j) ∨ ¬p(k,j)), i<k     — n·C(n+1,2) клауз
    Хакен (1985): любое резолюционное опровержение PHP_n имеет размер 2^Ω(n).
    DPLL и CDCL строят именно резолюционные доказательства, поэтому экспоненциальны.
    """
    n = int(n)
    v = lambda i, j: i * n + j + 1
    cnf: CNF = [tuple(v(i, j) for j in range(n)) for i in range(n + 1)]
    for j in range(n):
        for i in range(n + 1):
            for k in range(i + 1, n + 1):
                cnf.append((-v(i, j), -v(k, j)))
    return cnf, n * (n + 1)


# --------------------------------------------------------------------------- проверка
def lit_value(lit: int, x: Sequence[int]) -> int:
    v = x[abs(lit) - 1]
    return v if lit > 0 else 1 - v


def satisfies_clause(cl: Clause, x: Sequence[int]) -> bool:
    return any(lit_value(l, x) for l in cl)


def satisfies(cnf: CNF, x: Sequence[int]) -> bool:
    return all(satisfies_clause(cl, x) for cl in cnf)


def int_to_assign(a: int, n: int) -> List[int]:
    """Бит i числа a -> переменная i+1 (как в Verilog-модулях проекта)."""
    return [(a >> i) & 1 for i in range(n)]


def to_masks(cnf: CNF, n: int) -> Tuple[List[int], List[int]]:
    """Клауза -> пара масок (pos, neg): назначение a выполняет её, если
    ((a & pos) | (~a & neg)) != 0. Ровно так клауза устроена в FPGA."""
    pos, neg = [], []
    for cl in cnf:
        p = q = 0
        for l in cl:
            if l > 0:
                p |= 1 << (l - 1)
            else:
                q |= 1 << (-l - 1)
        pos.append(p)
        neg.append(q)
    return pos, neg


# --------------------------------------------------------------------------- 1. перебор 2^n
def brute_force(cnf: CNF, n: int, chunk_bits: int = 20):
    """Полный перебор по возрастанию a = 0, 1, 2, ... (векторизовано numpy).

    Возвращает минимальное выполняющее назначение и число проверенных назначений —
    ровно то, что делает FPGA-ядро, только последовательно.
    """
    n = int(n)
    pos, neg = to_masks(cnf, n)
    pos = np.array(pos, dtype=np.uint64)
    neg = np.array(neg, dtype=np.uint64)
    total = 1 << n
    step = 1 << min(chunk_bits, n)
    for start in range(0, total, step):
        a = np.arange(start, min(start + step, total), dtype=np.uint64)
        ok = np.ones(a.shape, dtype=bool)
        na = ~a
        for p, q in zip(pos, neg):
            ok &= ((a & p) | (na & q)) != 0
        idx = np.flatnonzero(ok)
        if idx.size:
            sol = int(a[idx[0]])
            return int_to_assign(sol, n), {"checked": sol + 1}
    return None, {"checked": total}


# --------------------------------------------------------------------------- 2. бэктрекинг
def backtracking(cnf: CNF, n: int):
    """Перебор по дереву x1, x2, ... с отсечением, как только какая-то клауза
    стала ложной. Без unit propagation. Считаем узлы дерева."""
    n = int(n)
    x = [-1] * n
    occ = [[] for _ in range(n + 1)]
    for ci, cl in enumerate(cnf):
        for l in cl:
            occ[abs(l)].append(ci)
    nodes = 0

    def falsified(ci):
        for l in cnf[ci]:
            v = x[abs(l) - 1]
            if v == -1 or (v == 1) == (l > 0):
                return False
        return True

    def rec(i):
        nonlocal nodes
        nodes += 1
        if i == n:
            return True
        for b in (0, 1):
            x[i] = b
            if not any(falsified(ci) for ci in occ[i + 1]) and rec(i + 1):
                return True
        x[i] = -1
        return False

    ok = rec(0)
    return (list(x) if ok else None), {"nodes": nodes}


# --------------------------------------------------------------------------- 3. ветвление по клаузе
def clause_branching(cnf: CNF, n: int):
    """Алгоритм Монин–Шпеккенмейера (простая версия).

    Берём невыполненную клаузу с наименьшим числом свободных литералов (l1 ∨ l2 ∨ l3) и
    ветвимся на три взаимоисключающих случая:
        l1 = 1;  l1 = 0, l2 = 1;  l1 = 0, l2 = 0, l3 = 1.
    Рекуррента T(n) = T(n-1) + T(n-2) + T(n-3) -> 1.839^n.
    """
    n = int(n)
    x = [-1] * n
    nodes = 0

    def status():
        best = None
        for cl in cnf:
            free = []
            sat = False
            for l in cl:
                v = x[abs(l) - 1]
                if v == -1:
                    free.append(l)
                elif (v == 1) == (l > 0):
                    sat = True
                    break
            if sat:
                continue
            if not free:
                return "conflict", None
            if best is None or len(free) < len(best):
                best = free
        return ("sat", None) if best is None else ("open", best)

    def setlit(l, val):
        x[abs(l) - 1] = val if l > 0 else 1 - val

    def rec():
        nonlocal nodes
        nodes += 1
        st, free = status()
        if st == "sat":
            return True
        if st == "conflict":
            return False
        for j in range(len(free)):
            for t in range(j):
                setlit(free[t], 0)
            setlit(free[j], 1)
            if rec():
                return True
            for t in range(j + 1):
                x[abs(free[t]) - 1] = -1
        return False

    ok = rec()
    if ok:
        sol = [v if v != -1 else 0 for v in x]
        return sol, {"nodes": nodes}
    return None, {"nodes": nodes}


# --------------------------------------------------------------------------- 4. DPLL
def dpll(cnf: CNF, n: int, trace: Optional[list] = None):
    """DPLL: unit propagation + ветвление по переменной из самой короткой клаузы.
    Считаем узлы дерева и шаги unit propagation (их на FPGA делают за такт).
    trace: если передан список, в него пишутся пары (assigned, value) как битовые
    маски перед каждым проходом — ровно то, что ARM отдал бы в bcp_unit.v."""
    n = int(n)
    x = [-1] * n
    stats = {"nodes": 0, "bcp_rounds": 0, "clause_checks": 0}

    def scan():
        """Один проход по всем клаузам = то, что bcp_unit.v делает за один такт."""
        if trace is not None:
            asg = sum(1 << i for i in range(n) if x[i] != -1)
            val = sum(1 << i for i in range(n) if x[i] == 1)
            trace.append((asg, val))
        stats["bcp_rounds"] += 1
        stats["clause_checks"] += len(cnf)
        unit = None
        short = None
        for cl in cnf:
            free = []
            sat = False
            for l in cl:
                v = x[abs(l) - 1]
                if v == -1:
                    free.append(l)
                elif (v == 1) == (l > 0):
                    sat = True
                    break
            if sat:
                continue
            if not free:
                return "conflict", None, None
            if len(free) == 1 and unit is None:
                unit = free[0]
            if short is None or len(free) < len(short):
                short = free
        if short is None:
            return "sat", None, None
        return "open", unit, short

    def rec():
        stats["nodes"] += 1
        trail = []
        while True:
            st, unit, short = scan()
            if st == "conflict":
                for v in trail:
                    x[v] = -1
                return False
            if st == "sat":
                return True
            if unit is None:
                break
            v = abs(unit) - 1
            x[v] = 1 if unit > 0 else 0
            trail.append(v)
        lit = short[0]
        v = abs(lit) - 1
        for val in ((1, 0) if lit > 0 else (0, 1)):
            x[v] = val
            if rec():
                return True
        x[v] = -1
        for t in trail:
            x[t] = -1
        return False

    ok = rec()
    if ok:
        return [v if v != -1 else 0 for v in x], stats
    return None, stats


# --------------------------------------------------------------------------- 5. Шёнинг
def schoening(cnf: CNF, n: int, max_tries: int = 10**6, seed: Optional[int] = None):
    """Случайное блуждание Шёнинга (1999).

    Попытка: случайное x, затем 3n раз: взять невыполненную клаузу, перевернуть в ней
    случайную переменную. Вероятность успеха попытки >= (3/4)^n / poly(n), поэтому
    ожидаемое число попыток ~ (4/3)^n.
    """
    n = int(n)
    rng = random.Random(None if seed is None else int(seed))
    flips = 0
    for t in range(1, max_tries + 1):
        x = [rng.randint(0, 1) for _ in range(n)]
        for _ in range(3 * n):
            bad = [cl for cl in cnf if not satisfies_clause(cl, x)]
            if not bad:
                return x, {"tries": t, "flips": flips}
            cl = rng.choice(bad)
            v = abs(rng.choice(cl)) - 1
            x[v] ^= 1
            flips += 1
        if satisfies(cnf, x):
            return x, {"tries": t, "flips": flips}
    return None, {"tries": max_tries, "flips": flips}


# --------------------------------------------------------------------------- DIMACS
def write_dimacs(cnf: CNF, n: int, path: str) -> None:
    with open(path, "w") as f:
        f.write(f"p cnf {n} {len(cnf)}\n")
        for cl in cnf:
            f.write(" ".join(map(str, cl)) + " 0\n")
