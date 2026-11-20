"""Statistical estimators used by Assignment 7, sections 15.5 and 15.6."""
from __future__ import annotations
from math import ceil, comb, sqrt
from numbers import Integral

Z95 = 1.96
POWER_Z = 2.80


def _counts(n, c, k):
    if any(not isinstance(x, Integral) or isinstance(x, bool) for x in (n,c,k)):
        raise ValueError('n, c and k must be integer counts')
    if not (n >= 1 and 0 <= c <= n and 1 <= k <= n):
        raise ValueError('Require n >= 1, 0 <= c <= n and 1 <= k <= n')


def mean(values) -> float:
    values = list(values)
    if not values:
        raise ValueError('mean requires at least one observation')
    return sum(values) / len(values)


def standard_error(values) -> float:
    values = list(values)
    if len(values) < 2:
        raise ValueError('standard error requires at least two observations')
    return spread(values) / sqrt(len(values))


def pass_at_k(n: int, c: int, k: int) -> float:
    _counts(n,c,k)
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    _counts(n,c,k)
    return comb(c, k) / comb(n, k)


def over_tasks(counts: dict[str, tuple[int, int]], k: int) -> tuple[float, float]:
    if not counts:
        return 0.0, 0.0
    return (sum(pass_at_k(n, c, k) for n, c in counts.values()) / len(counts),
            sum(pass_hat_k(n, c, k) for n, c in counts.values()) / len(counts))


def spread(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    return sqrt(sum((x - avg) ** 2 for x in values) / (len(values) - 1))


def margin(s_first: float, n_first: int, s_second: float, n_second: int) -> float:
    if min(s_first,s_second) < 0 or min(n_first,n_second) <= 0:
        raise ValueError('SDs must be nonnegative and sample sizes positive')
    return Z95 * sqrt(s_first ** 2 / n_first + s_second ** 2 / n_second)


def interval(first: list[float], second: list[float]) -> tuple[float, float, float]:
    gain = mean(first) - mean(second)
    m = margin(spread(first), len(first), spread(second), len(second))
    return gain, gain - m, gain + m


def sweeps_needed(s_a: float, s_b: float, delta: float) -> int:
    if delta <= 0 or min(s_a,s_b) < 0:
        raise ValueError("delta must be positive and SDs nonnegative")
    return max(1, ceil((s_a ** 2 + s_b ** 2) * (POWER_Z / delta) ** 2))
