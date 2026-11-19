"""Subset Sum: три уровня перебора и счётчики операций."""
from __future__ import annotations

import bisect
import random
from typing import List, Optional, Tuple


def random_instance(n: int, bits: int = 30, solvable: bool = True, seed: Optional[int] = None):
    """n случайных чисел. Если solvable — T равно сумме случайного подмножества,
    иначе T нечётное при всех чётных числах (решения точно нет)."""
    rng = random.Random(seed)
    if solvable:
        a = [rng.randrange(1, 1 << bits) for _ in range(n)]
        mask = rng.randrange(1, 1 << n)
        T = sum(a[i] for i in range(n) if mask >> i & 1)
    else:
        a = [2 * rng.randrange(1, 1 << (bits - 1)) for _ in range(n)]
        T = 2 * rng.randrange(1, 1 << (bits - 1)) + 1
    return a, T


def mask_sum(a: List[int], mask: int) -> int:
    return sum(v for i, v in enumerate(a) if mask >> i & 1)


def naive(a: List[int], T: int):
    """Для каждой маски заново складываем: O(n * 2^n) сложений."""
    n = len(a)
    adds = 0
    for mask in range(1 << n):
        s = 0
        for i in range(n):
            if mask >> i & 1:
                s += a[i]
                adds += 1
        if s == T:
            return mask, {"adds": adds, "masks": mask + 1}
    return None, {"adds": adds, "masks": 1 << n}


def gray(a: List[int], T: int):
    """Код Грея: g(i) = i ^ (i >> 1). Между g(i-1) и g(i) меняется один бит —
    номер младшей единицы числа i (ctz). Одно сложение или вычитание на маску: O(2^n).
    Ровно эту схему повторяет rtl/ss_engine.v."""
    n = len(a)
    s = 0
    if T == 0:
        return 0, {"adds": 0, "masks": 1}
    for i in range(1, 1 << n):
        b = (i & -i).bit_length() - 1      # ctz(i): какой бит меняется
        g = i ^ (i >> 1)                   # новая маска
        s += a[b] if g >> b & 1 else -a[b] # бит стал 1 -> добавить, стал 0 -> убрать
        if s == T:
            return g, {"adds": i, "masks": i + 1}
    return None, {"adds": (1 << n) - 1, "masks": 1 << n}


def all_sums(a: List[int]) -> List[Tuple[int, int]]:
    """Все 2^k сумм половины с масками, по коду Грея (одно сложение на сумму)."""
    k = len(a)
    out = [(0, 0)]
    s = 0
    for i in range(1, 1 << k):
        b = (i & -i).bit_length() - 1
        g = i ^ (i >> 1)
        s += a[b] if g >> b & 1 else -a[b]
        out.append((s, g))
    return out


def meet_in_the_middle(a: List[int], T: int):
    """Горовиц–Сахни (1974): две половины по n/2, сортировка правой, бинпоиск.
    Время O(2^(n/2) * n), память O(2^(n/2)). Основание: 2 -> sqrt(2) = 1.414."""
    n = len(a)
    h = n // 2
    L = all_sums(a[:h])
    R = sorted(all_sums(a[h:]))
    keys = [s for s, _ in R]
    probes = 0
    for s, m in L:
        probes += 1
        j = bisect.bisect_left(keys, T - s)
        if j < len(keys) and keys[j] == T - s:
            return m | (R[j][1] << h), {"sums": len(L) + len(R), "probes": probes,
                                        "memory_entries": len(R)}
    return None, {"sums": len(L) + len(R), "probes": probes, "memory_entries": len(R)}


def dp_pseudopoly(a: List[int], T: int):
    """ДП по сумме: O(n*T) — псевдополиномиально. Работает, только если T мало
    (размер входа ~ log T бит, поэтому это всё равно экспонента от длины записи)."""
    reach = 1  # битсет достижимых сумм
    for v in a:
        reach |= reach << v
    return bool(reach >> T & 1)
