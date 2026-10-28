"""Stage commands, with new outputs isolated from the frozen research archive."""
from __future__ import annotations

import csv
from datetime import datetime
import math
from pathlib import Path
import subprocess
import sys
import time
import uuid
from zoneinfo import ZoneInfo

import joblib
import numpy as np

from .core import (ASSETS, METHODS, Dataset, check_seal, environment, fit_models,
                   make_seal, predict_models, quality, read_json, read_json_gzip,
                   require, sha, write_json)
from .evaluation import (expected_best, independent_curve, independent_midrank,
                         ranks, replay_selection, score_pool, summarize)

PACKAGE = Path(__file__).resolve().parent


def code_hashes():
    return {p.name: sha(p) for p in sorted(PACKAGE.glob("*.py"))}


def prepared(run):
    run = Path(run).resolve()
    check_seal(run, run / "input_seal.json")
    meta = read_json(run / "run.json")
    require(meta["asset_manifest_sha256"] == sha(ASSETS / "manifest.json"), "Asset version changed")
    require(meta["code_hashes"] == code_hashes(), "Runtime code changed since prepare; use a new run directory")
    require(meta["environment"] == environment(), "Environment changed since prepare")
    return run, meta


def prepare(output=None, splits="all", mode="retrain"):
    data = Dataset()
    selected = [s["id"] for s in data.splits] if splits == "all" else splits.split(",")
    require(len(set(selected)) == len(selected) and selected, "Duplicate or empty split list")
    for sid in selected:
        data.split(sid)
    if output is None:
        stamp = datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y%m%d-%H%M%S")
        output = Path("outputs") / f"allis-{stamp}-{uuid.uuid4().hex[:6]}"
    run = Path(output).resolve()
    require(not run.exists() or not any(run.iterdir()), f"Output directory is not empty: {run}")
    run.mkdir(parents=True, exist_ok=True)
    (run / "candidate_inputs").mkdir()
    files = []
    for sid in selected:
        candidate_file = run / "candidate_inputs" / f"{sid}.npz"
        np.savez_compressed(candidate_file, **data.candidates(data.split(sid)))
        files.append(candidate_file)
    write_json(run / "run.json", {
        "schema": 1, "mode": mode, "split_ids": selected, "expected_splits": 15,
        "complete_benchmark": len(selected) == 15, "methods": list(METHODS),
        "weights": [0.5, 0.5], "dose_transform": "linear_pmol", "retrospective": True,
        "environment": environment(), "code_hashes": code_hashes(),
        "asset_manifest_sha256": sha(ASSETS / "manifest.json"),
        "started_unix": time.time(), "training_ligands_per_pool": 36, "candidate_ligands_per_pool": 18,
        "candidate_input_schema": ["features", "dose_pmol", "ids", "feature_names"],
    })
    make_seal(run, files + [run / "run.json"], run / "input_seal.json", stage="prepare", time=time.time())
    return run


def train_one(run, sid):
    run, meta = prepared(run)
    require(sid in meta["split_ids"], "Split not prepared")
    data = Dataset()
    split = data.split(sid)
    start = time.monotonic()
    model = fit_models(data, split)
    model_file = run / "models" / f"{sid}.joblib"
    require(not model_file.exists(), "Model already exists; no automatic retry/overwrite")
    joblib.dump(model, model_file, compress=3)
    cfg = data.config["folds"][sid]
    write_json(run / "models" / f"{sid}.json", {
        "split": sid, "fits": 2, "train": split["train"], "training_ids": model.training_ids,
        "paired_params": model.paired.get_params(), "direct_params": model.direct.get_params(),
        "columns": model.columns.tolist(), "training_pairs": cfg["training_pairs"],
        "reference_points": len(model.reference_y), "reference_target_sha256": __import__("hashlib").sha256(model.reference_y.tobytes()).hexdigest(),
        "model_sha256": sha(model_file), "seconds": time.monotonic() - start,
    })
    return {"split": sid, "fits": 2, "seconds": round(time.monotonic() - start, 3)}


def run_worker(command, run, sid, deadline):
    remaining = deadline - time.monotonic()
    require(remaining > 0, "Fixed execution time budget exhausted")
    cmd = [sys.executable, "-m", "allis_delivery", command, "--run-dir", str(run), "--split", sid]
    result = subprocess.run(cmd, cwd=PACKAGE.parent, capture_output=True, text=True,
                            timeout=min(180, remaining))
    log = run / "logs" / f"{command}-{sid}.log"
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    require(result.returncode == 0, f"{command} failed for {sid}; see {log}")
    print(result.stdout.strip(), flush=True)


def train(run, deadline=None):
    run, meta = prepared(run)
    require(meta["mode"] == "retrain", "Cached runs do not train; prepare a new --mode retrain run")
    require(not (run / "training_started.json").exists(), "Training already attempted; use a fresh output directory")
    start = time.monotonic()
    deadline = deadline or (start + 1200)
    write_json(run / "training_started.json", {"planned_fits": 2 * len(meta["split_ids"]), "time": time.time(), "retries": 0})
    (run / "models").mkdir()
    (run / "logs").mkdir(exist_ok=True)
    done, failure = [], None
    try:
        for sid in meta["split_ids"]:
            run_worker("_train-one", run, sid, deadline)
            done.append(sid)
    except (ValueError, subprocess.TimeoutExpired) as exc:
        failure = str(exc)
    write_json(run / "training.json", {"complete": failure is None, "completed_splits": done,
                                       "new_fits": 2 * len(done), "planned_fits": 2 * len(meta["split_ids"]), "retries": 0,
                                       "seconds": time.monotonic() - start, "failure": failure})
    require(failure is None, f"Training stopped without retry: {failure}")
    files = [run / "models" / f"{sid}{suffix}" for sid in done for suffix in (".joblib", ".json")]
    make_seal(run, files + [run / "training.json"], run / "model_seal.json", stage="train", time=time.time())


def load_candidates(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files}


def predict_one(run, sid):
    run, meta = prepared(run)
    check_seal(run, run / "model_seal.json")
    data = Dataset()
    split = data.split(sid)
    bundle = joblib.load(run / "models" / f"{sid}.joblib")
    require(bundle.split == sid and bundle.training_ids == [data.ids[i] for i in split["train"]], "Wrong model identities")
    start = time.monotonic()
    prediction = predict_models(bundle, load_candidates(run / "candidate_inputs" / f"{sid}.npz"))
    write_prediction(run, split, prediction, "retrained")
    return {"split": sid, "prediction_seconds": round(time.monotonic() - start, 3)}


def write_prediction(run, split, prediction, mode):
    require(len(prediction["ids"]) == 18, "Locked benchmark needs 18 candidates")
    record = {"schema": 1, "split": split["id"], "mode": mode,
              "train": split["train"], "test": split["test"], **prediction}
    record["ranks"] = {k: v.tolist() for k, v in ranks(record["paired_q"], record["direct_q"]).items()}
    write_json(run / "predictions" / f"{split['id']}.json", record)


def predict(run, mode=None, deadline=None):
    run, meta = prepared(run)
    mode = mode or meta["mode"]
    require(mode in ("cached", "retrain"), "Unknown prediction mode")
    require(mode == meta["mode"], "Prediction mode must match prepare; use a new run to change mode")
    require(not (run / "prediction_started.json").exists(), "Prediction already attempted; use a fresh output directory")
    start = time.monotonic()
    deadline = deadline or (start + 1200)
    write_json(run / "prediction_started.json", {"mode": mode, "time": time.time(), "retries": 0})
    (run / "predictions").mkdir()
    (run / "logs").mkdir(exist_ok=True)
    data = Dataset()
    if mode == "retrain":
        check_seal(run, run / "model_seal.json")
    done, failure = [], None
    try:
        for sid in meta["split_ids"]:
            split = data.split(sid)
            if mode == "cached":
                with np.load(ASSETS / "cache" / f"{sid}.npz", allow_pickle=False) as cached:
                    require(cached["train"].tolist() == split["train"] and cached["test"].tolist() == split["test"], "Cache IDs mismatch")
                    prediction = {"ids": [data.ids[i] for i in split["test"]],
                                  "paired_q": cached["paired_q"].tolist(), "direct_q": cached["direct_q"].tolist(),
                                  "paired_curves": cached["paired_curves"].tolist(), "dose_pmol": data.dose[split["test"]].tolist()}
                write_prediction(run, split, prediction, "cached")
            else:
                run_worker("_predict-one", run, sid, deadline)
            done.append(sid)
    except (ValueError, subprocess.TimeoutExpired) as exc:
        failure = str(exc)
    write_json(run / "prediction_execution.json", {"complete": failure is None, "completed_splits": done,
                                                  "mode": mode, "seconds": time.monotonic() - start, "failure": failure})
    require(failure is None, f"Prediction stopped: {failure}")
    comparisons = []
    for sid in done:
        pred = read_json(run / "predictions" / f"{sid}.json")
        with np.load(ASSETS / "cache" / f"{sid}.npz", allow_pickle=False) as cached:
            errors = {k: float(np.max(abs(np.asarray(pred[k]) - cached[k]))) for k in ("paired_q", "direct_q", "paired_curves")}
            require(max(errors.values()) < 1e-10, f"Prediction differs from fixed reference: {sid}: {errors}")
            reference_ranks = ranks(cached["paired_q"], cached["direct_q"])
            for method in METHODS:
                require(np.array_equal(pred["ranks"][method], reference_ranks[method]), f"Ranking differs from reference: {sid} {method}")
            comparisons.append({"split": sid, "maximum_absolute_errors": errors, "exact_ranks_match": True})
    write_json(run / "prediction_reference_check.json", {"pass": True, "mode": mode, "pools": comparisons})
    files = [run / "predictions" / f"{sid}.json" for sid in done]
    make_seal(run, files + [run / "prediction_execution.json", run / "prediction_reference_check.json"],
              run / "prediction_seal.json", stage="predict", time=time.time(), candidate_outcomes_read=False)


def evaluate(run):
    run, meta = prepared(run)
    check_seal(run, run / "prediction_seal.json")
    data, rows = Dataset(), []
    # All selected predictions are sealed BEFORE any candidate gold labels are loaded.
    for sid in meta["split_ids"]:
        split = data.split(sid)
        pred = read_json(run / "predictions" / f"{sid}.json")
        gold = quality(data.responses(split["test"]))
        for scope, indices in (("all", split["test"]), ("covered", split["eligible_test"])):
            positions = [split["test"].index(k) for k in indices]
            subset = {k: [pred[k][j] for j in positions] for k in ("paired_q", "direct_q")}
            rows.extend(score_pool(split, scope, indices, subset, gold[positions]))
    metrics = summarize(rows)
    (run / "evaluation").mkdir()
    write_json(run / "evaluation/metrics.json", metrics)
    with (run / "evaluation/per_pool.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = ["split", "replicate", "scope", "method", "AUR", "B1", "B2", "B3", "B4", "B5", "top3_mean_Q"]
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    write_report(run, meta, metrics)
    make_seal(run, [run / "evaluation/metrics.json", run / "evaluation/per_pool.csv", run / "REPORT.md"],
              run / "evaluation_seal.json", stage="evaluate", time=time.time())
    return metrics


def write_report(run, meta, metrics):
    lines = ["# ALLiS双模型配体筛选：可复核回放", "",
             f"运行方式：{meta['mode']}；覆盖{len(meta['split_ids'])}/15个固定候选池。",
             "完整基准是90个唯一配体、每个40用量点、每池36历史/18候选；所有结果为回顾性评估。", "",
             "|方法|平均遗憾AUR↓|B1最佳实测Q↑|B2↑|B3↑|B4↑|B5↑|", "|---|---:|---:|---:|---:|---:|---:|"]
    for row in metrics["summary"]:
        if row["scope"] == "all":
            lines.append("|" + row["method"] + "|" + "|".join(f"{row[k]:.6f}" for k in ("AUR", "B1", "B2", "B3", "B4", "B5")) + "|")
    lines += ["", "成对ET、直接评分ET和等权名次融合均保留；用量为原线性pmol。",
              "AUR是前1—5次离池最佳Q的平均差；Q为40点相对PL FOM最高4点的均值，不是绝对PLQY。",
              "平局指标为均匀随机打平的精确期望；具体回放抽样与这个期望分别展示。",
              "融合为项目主方案。原研究要求B3零退化的全部条件未通过，原始记录保留在assets/reference/research_decision.json；未修改为成功。",
              "缓存模式不训练、不能为新分子推断；retrain模式重新训练两个固定组件并保存模型，可对符合特征schema的候选推断。",
              "原42维特征使用作者预计算结果；不承诺任意SMILES自动生成这些特征。",
              "小于15池的运行只是局部回放/工程检查，不能用来重申完整基准提升比例。", "",
              "完整逐池结果：evaluation/per_pool.csv；核验：verification.json；数据与预测先后关系由各stage seal记录。"]
    (run / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def replay(run, sid="r0_f0", budget=3, method="equal_rank", reveal=False, seed=42):
    run, meta = prepared(run)
    check_seal(run, run / "prediction_seal.json")
    require(sid in meta["split_ids"] and method in METHODS and 1 <= budget <= 5, "Invalid replay request")
    pred = read_json(run / "predictions" / f"{sid}.json")
    ranking = np.asarray(pred["ranks"][method])
    # Uniform random ordering within ties; exactly B selected, never all boundary ties.
    selected = replay_selection(ranking, budget, seed)
    threshold = np.sort(ranking)[budget - 1]
    boundary = np.flatnonzero(ranking == threshold)
    recommendations = [{"index": pred["test"][j], "id": pred["ids"][j],
                        "paired_predicted_Q": pred["paired_q"][j], "direct_predicted_Q": pred["direct_q"][j],
                        "method_rank": float(ranking[j]), "fusion_rank": pred["ranks"]["equal_rank"][j]}
                       for j in selected]
    result = {"mode": meta["mode"], "retrospective_replay": True, "split": sid, "method": method,
              "budget": budget, "selected_count": len(selected), "tie_seed": seed,
              "boundary_tie_ids": [pred["ids"][j] for j in boundary], "recommendations": recommendations,
              "revealed": reveal}
    if reveal:
        data = Dataset()
        gold = quality(data.responses(pred["test"]))
        for item, j in zip(recommendations, selected):
            item["archived_measured_Q"] = float(gold[j])
        result["realized_best_Q_this_tie_draw"] = float(gold[selected].max())
        result["expected_best_Q_over_uniform_ties"] = float(expected_best(ranking, gold, [budget])[0])
        result["candidate_oracle_Q"] = float(gold.max())
    return result


def verify(run):
    run, meta = prepared(run)
    if (run / "delivery_seal.json").exists():
        check_seal(run, run / "delivery_seal.json")
    check_seal(run, run / "prediction_seal.json")
    check_seal(run, run / "evaluation_seal.json")
    require(read_json(run / "input_seal.json")["time"] < read_json(run / "prediction_seal.json")["time"]
            < read_json(run / "evaluation_seal.json")["time"], "Stage order is inconsistent")
    if (run / "model_seal.json").exists():
        check_seal(run, run / "model_seal.json")
    data = Dataset()
    raw = read_json_gzip(ASSETS / "data/reaction_collection_train_AL0503.json.gz")
    raw_y = {ident: [] for ident in data.ids}
    for reaction in raw["reactions"]:
        if reaction["properties"].get("WallTag") == 1:
            ident = reaction["ligand_solutions"][0]["solute"]["identifier"]
            if ident in raw_y:
                raw_y[ident].append(float(reaction["properties"]["FigureOfMerit"]))
    gold = {i: math.fsum(sorted(raw_y[ident])[-4:]) / 4 for i, ident in enumerate(data.ids)}
    reference = read_json(ASSETS / "reference/metrics.json")
    reference_rows = {(r["split"], r["scope"], r["method"]): r for r in reference["rows"]}
    metrics = read_json(run / "evaluation/metrics.json")
    rank_error = score_error = reference_error = 0.0
    for sid in meta["split_ids"]:
        pred = read_json(run / "predictions" / f"{sid}.json")
        ra, rb = independent_midrank(pred["paired_q"]), independent_midrank(pred["direct_q"])
        rr = [0.5 * (a + b) for a, b in zip(ra, rb)]
        for method, expected in zip(METHODS, (ra, rb, rr)):
            rank_error = max(rank_error, float(np.max(abs(np.asarray(expected) - pred["ranks"][method]))))
            require(expected == pred["ranks"][method], "Independent midrank mismatch")
        if (run / "model_seal.json").exists():
            info = read_json(run / "models" / f"{sid}.json")
            cfg = data.config["folds"][sid]
            require(info["paired_params"] == cfg["paired_params"] and info["direct_params"] == cfg["direct_params"], "Model parameters changed")
            require(info["columns"] == cfg["expected_columns"] and info["reference_points"] == 1440, "Model inputs/references changed")
    for row in metrics["rows"]:
        pred = read_json(run / "predictions" / f"{row['split']}.json")
        positions = [pred["test"].index(k) for k in row["candidate_indices"]]
        ra = independent_midrank([pred["paired_q"][j] for j in positions])
        rb = independent_midrank([pred["direct_q"][j] for j in positions])
        candidate_rank = {"paired_ET": ra, "direct_Q_ET": rb,
                          "equal_rank": [(a + b) / 2 for a, b in zip(ra, rb)]}[row["method"]]
        require(candidate_rank == row["rank"], "Scope-specific rank mismatch")
        y = np.asarray([gold[k] for k in row["candidate_indices"]])
        require(np.allclose(y, row["gold_Q"], rtol=0, atol=1e-12), "Gold mismatch")
        independent = independent_curve(row["rank"], y)
        score_error = max(score_error, float(max(abs(independent - row["curve"]))))
        require(np.allclose(independent, row["curve"], atol=1e-12, rtol=0), "Tie enumeration mismatch")
        require(abs(np.mean(y.max() - independent) - row["AUR"]) < 1e-12, "AUR mismatch")
        ref = reference_rows[row["split"], row["scope"], row["method"]]
        for key in ("AUR", "B1", "B3", "B5", "top3_mean_Q"):
            error = abs(row[key] - ref[key])
            reference_error = max(reference_error, error)
            require(error < 1e-10, f"Fixed research result mismatch: {row['split']} {row['method']} {key}")
    for summary in metrics["summary"]:
        rows = [r for r in metrics["rows"] if r["scope"] == summary["scope"] and r["method"] == summary["method"]]
        for key in ("AUR", "B1", "B2", "B3", "B4", "B5"):
            require(abs(math.fsum(r[key] for r in rows) / len(rows) - summary[key]) < 1e-12, "Macro average mismatch")
    for comparison in metrics["comparisons"]:
        ours = {r["split"]: r for r in metrics["rows"] if r["scope"] == comparison["scope"] and r["method"] == "equal_rank"}
        base = {r["split"]: r for r in metrics["rows"] if r["scope"] == comparison["scope"] and r["method"] == comparison["baseline"]}
        delta = [base[k]["AUR"] - ours[k]["AUR"] for k in ours]
        require(abs(math.fsum(delta) / len(delta) - comparison["AUR_improvement"]) < 1e-12, "Comparison mean mismatch")
        require([sum(v > 1e-12 for v in delta), sum(abs(v) <= 1e-12 for v in delta), sum(v < -1e-12 for v in delta)]
                == comparison["wins_ties_losses"], "Win/tie/loss count mismatch")
    training = read_json(run / "training.json") if (run / "training.json").exists() else {"new_fits": 0}
    result = {"pass": True, "mode": meta["mode"], "pools": len(meta["split_ids"]), "scored_rows": len(metrics["rows"]),
              "new_fits": training["new_fits"], "complete_benchmark": meta["complete_benchmark"],
              "midrank_maximum_error": rank_error, "independent_score_maximum_error": score_error,
              "research_reference_maximum_error": reference_error,
              "all_prediction_ranks_match_reference": True, "raw_Q_reconstructed": True,
              "retrospective": True, "new_blind_test": False}
    if not (run / "verification.json").exists():
        write_json(run / "verification.json", result)
    return result


def predict_external(run, sid, candidate_file):
    """Prediction from persisted weights and feature-only NPZ; no gold loading."""
    run, meta = prepared(run)
    check_seal(run, run / "model_seal.json")
    require(sid in meta["split_ids"], "Split not trained in this run")
    bundle = joblib.load(run / "models" / f"{sid}.joblib")
    prediction = predict_models(bundle, load_candidates(candidate_file))
    return {"schema": 1, "mode": "feature_only_prediction_not_experimental_validation",
            "split": sid, "candidate_input_sha256": sha(candidate_file), **prediction,
            "ranks": {k: v.tolist() for k, v in ranks(prediction["paired_q"], prediction["direct_q"]).items()}}


def run_pipeline(output=None, mode="cached", splits="all"):
    start = time.monotonic()
    run = prepare(output, splits, mode)
    print(f"Output: {run}", flush=True)
    deadline = start + 1200
    if mode == "retrain":
        train(run, deadline)
    predict(run, mode, deadline)
    evaluate(run)
    receipt = verify(run)
    (run / "replays").mkdir()
    sid = read_json(run / "run.json")["split_ids"][0]
    for method in METHODS:
        for revealed in (False, True):
            write_json(run / "replays" / f"{sid}-{method}-{'revealed' if revealed else 'hidden'}.json",
                       replay(run, sid, 3, method, revealed))
    write_json(run / "execution.json", {"complete": True, "mode": mode, "new_fits": receipt["new_fits"],
                                       "elapsed_seconds": time.monotonic() - start, "verified": True})
    make_seal(run, [p for p in run.rglob("*") if p.is_file()], run / "delivery_seal.json", stage="complete")
    return {"output": str(run), "report": str(run / "REPORT.md"), **receipt,
            "elapsed_seconds": time.monotonic() - start}
