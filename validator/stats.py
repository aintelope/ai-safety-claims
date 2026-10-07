"""Exact binomial statistics, standard library only."""

import math


def binom_cdf(k, n, p):
    """P(X <= k) for X ~ Binomial(n, p)."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    log_p, log_q = math.log(p), math.log1p(-p)
    total = 0.0
    for i in range(k + 1):
        log_term = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                    + i * log_p + (n - i) * log_q)
        total += math.exp(log_term)
    return min(total, 1.0)


def auroc(scores, labels):
    """Mann-Whitney AUROC: P(score_pos > score_neg) + 0.5 P(equal). Empty class is 0."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return 0.0
    n = 0.0
    for p in pos:
        for q in neg:
            n += 1.0 if p > q else 0.5 if p == q else 0.0
    return n / (len(pos) * len(neg))


def clopper_pearson_upper(k, n, confidence=0.95):
    """One-sided Clopper-Pearson upper bound on a rate with k failures in n units."""
    if n <= 0:
        raise ValueError("n must be positive")
    if k >= n:
        return 1.0
    alpha = 1.0 - confidence
    lo, hi = k / n, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if binom_cdf(k, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return hi
