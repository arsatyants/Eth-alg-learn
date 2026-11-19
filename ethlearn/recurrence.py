"""Рекуррентные оценки ветвящихся алгоритмов.

Если на каждом шаге алгоритм порождает подзадачи размеров n-d1, n-d2, ..., то
    T(n) = T(n-d1) + T(n-d2) + ... ,
и решение ищется в виде T(n) = c^n. Подстановка и деление на c^n дают
    1 = c^(-d1) + c^(-d2) + ...                (*)
Левая часть (*) при c>1 строго убывает, поэтому корень единственный —
это и есть «основание экспоненты» (branching number).
"""
from __future__ import annotations

import math
from typing import Iterable, List

import numpy as np


def branching_number(ds: Iterable[int], tol: float = 1e-12) -> float:
    """Корень c>1 уравнения sum c^(-d) = 1 бисекцией."""
    ds = list(ds)
    f = lambda c: sum(c ** (-d) for d in ds) - 1.0
    lo, hi = 1.0 + 1e-12, float(len(ds)) + 1.0
    if f(lo) <= 0:
        return 1.0
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def char_poly_roots(ds: Iterable[int]) -> np.ndarray:
    """Те же корни через характеристический многочлен: умножаем (*) на c^D, D = max d:
        c^D - sum c^(D-d) = 0.
    """
    ds = list(ds)
    D = max(ds)
    coef = np.zeros(D + 1)
    coef[0] = 1.0
    for d in ds:
        coef[d] -= 1.0
    return np.roots(coef)


def unroll(ds: Iterable[int], n: int) -> List[int]:
    """T(k) для k=0..n прямой подстановкой рекурренты (T(k<=0) = 1).
    Позволяет увидеть, что T(n+1)/T(n) -> c."""
    ds = list(ds)
    T = [1] * (n + 1)
    for k in range(1, n + 1):
        T[k] = sum(T[k - d] if k - d >= 0 else 1 for d in ds)
    return T


def log2_base(c: float) -> float:
    """c^n = 2^(n*log2 c): доля переменных, которые «реально» перебираются."""
    return math.log2(c)
