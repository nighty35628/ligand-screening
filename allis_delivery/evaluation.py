"""Fixed equal-midrank policy and exact random-tie evaluation."""
from collections import defaultdict
import itertools
import math

import numpy as np
from scipy.stats import rankdata

from .core import METHODS, require


def ranks(paired_q, direct_q):
    a, b = np.asarray(paired_q, dtype=float), np.asarray(direct_q, dtype=float)
    require(a.ndim == b.ndim == 1 and len(a) == len(b) and len(a) > 0, "Ranking input shape mismatch")
    require(np.isfinite(a).all() and np.isfinite(b).all(), "Non-finite ranking inputs")
    ra, rb = rankdata(-a, method="average"), rankdata(-b, method="average")
    return {"paired_ET": ra, "direct_Q_ET": rb, "equal_rank": (ra + rb) / 2}


def expected_best(rank, gold, budgets=range(1, 6)):
    """Average over all permutations within each EXACT rank tie group."""
    groups = defaultdict(list)
    for r, y in zip(rank, gold):
        groups[float(r)].append(float(y))
    blocks = [groups[k] for k in sorted(groups)]
    out = []
    for budget in budgets:
        require(1 <= budget <= len(gold), "Invalid query budget")
        done, best = 0, -math.inf
        for block in blocks:
            if done + len(block) <= budget:
                done += len(block)
                best = max(best, max(block))
                if done == budget:
                    out.append(best)
                    break
            else:
                take, yy = budget - done, sorted(block)
                out.append(sum(max(best, yy[k]) * math.comb(k, take - 1) / math.comb(len(yy), take)
                               for k in range(take - 1, len(yy))))
                break
    return np.asarray(out)


def first_three_mean(rank, gold):
    groups = defaultdict(list)
    for r, y in zip(rank, gold):
        groups[float(r)].append(float(y))
    taken, total = 0, 0.0
    for r in sorted(groups):
        n = min(3 - taken, len(groups[r]))
        total += n * np.mean(groups[r])
        taken += n
        if taken == 3:
            return float(total / 3)
    raise ValueError("Need at least three candidates")


def score_pool(split, scope, indices, prediction, gold):
    rr = ranks(prediction["paired_q"], prediction["direct_q"])
    rows = []
    for method, ranking in rr.items():
        curve = expected_best(ranking, gold)
        rows.append({"split": split["id"], "replicate": split["replicate"], "scope": scope,
                     "method": method, "AUR": float(np.mean(max(gold) - curve)),
                     "B1": float(curve[0]), "B2": float(curve[1]), "B3": float(curve[2]),
                     "B4": float(curve[3]), "B5": float(curve[4]),
                     "top3_mean_Q": first_three_mean(ranking, gold), "curve": curve.tolist(),
                     "oracle_Q": float(max(gold)), "candidate_indices": indices,
                     "gold_Q": np.asarray(gold).tolist(), "rank": ranking.tolist()})
    return rows


def compare(rows, baseline, scope):
    ours = {r["split"]: r for r in rows if r["scope"] == scope and r["method"] == "equal_rank"}
    base = {r["split"]: r for r in rows if r["scope"] == scope and r["method"] == baseline}
    delta = np.asarray([base[k]["AUR"] - ours[k]["AUR"] for k in ours])
    reps = sorted({r["replicate"] for r in ours.values()})
    return {"scope": scope, "method": "equal_rank", "baseline": baseline,
            "AUR_improvement": float(delta.mean()),
            "replicate_improvement": [float(np.mean([base[k]["AUR"] - ours[k]["AUR"] for k in ours
                                                     if ours[k]["replicate"] == rep])) for rep in reps],
            "wins_ties_losses": [int(sum(delta > 1e-12)), int(sum(abs(delta) <= 1e-12)), int(sum(delta < -1e-12))],
            "leave_one_pool_out_min_improvement": float(min(np.delete(delta, i).mean() for i in range(len(delta)))) if len(delta) > 1 else None,
            "B3_Q_improvement": float(np.mean([ours[k]["B3"] - base[k]["B3"] for k in ours]))}


def summarize(rows):
    summaries = []
    for scope in ("all", "covered"):
        for method in METHODS:
            pool = [r for r in rows if r["scope"] == scope and r["method"] == method]
            reps = sorted({r["replicate"] for r in pool})
            summaries.append({"scope": scope, "method": method,
                              **{k: float(np.mean([r[k] for r in pool])) for k in ("AUR", "B1", "B2", "B3", "B4", "B5", "top3_mean_Q")},
                              "rep_AUR": [float(np.mean([r["AUR"] for r in pool if r["replicate"] == i])) for i in reps]})
    return {"rows": rows, "summary": summaries,
            "comparisons": [compare(rows, base, scope) for scope in ("all", "covered")
                            for base in ("paired_ET", "direct_Q_ET")]}


def independent_curve(rank, gold):
    """Different implementation: enumerate the partial tie-block subsets."""
    out = []
    for budget in range(1, 6):
        remaining, best = budget, -math.inf
        for r in sorted(set(rank)):
            block = [float(y) for rr, y in zip(rank, gold) if rr == r]
            if remaining >= len(block):
                best = max(best, max(block))
                remaining -= len(block)
                if remaining == 0:
                    out.append(best)
                    break
            else:
                out.append(math.fsum(max(best, max(c)) for c in itertools.combinations(block, remaining)) / math.comb(len(block), remaining))
                break
    return np.asarray(out)


def independent_midrank(values):
    return [1 + sum(x > v for x in values) + (sum(x == v for x in values) - 1) / 2 for v in values]


def replay_selection(rank, budget, seed=42):
    ranking = np.asarray(rank, dtype=float)
    require(ranking.ndim == 1 and np.isfinite(ranking).all(), "Invalid replay ranks")
    require(1 <= budget <= len(ranking), "Invalid replay budget")
    rng = np.random.default_rng(seed)
    return np.lexsort((rng.random(len(ranking)), ranking))[:budget]
