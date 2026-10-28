"""One CLI for the frozen two-model system: prepare/train/predict/evaluate/replay/verify."""
import argparse
import json
import sys
from pathlib import Path

from .core import Dataset, environment, write_json
from . import workflow


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("run", "prepare"):
        c = sub.add_parser(name)
        c.add_argument("--output", type=Path)
        c.add_argument("--mode", choices=("cached", "retrain"), default="cached" if name == "run" else "retrain")
        c.add_argument("--splits", default="all", help="all, or fixed IDs separated by commas; partial runs are engineering checks")
    for name in ("train", "predict", "evaluate", "replay", "verify", "_train-one", "_predict-one"):
        c = sub.add_parser(name)
        c.add_argument("--run-dir", type=Path, required=True)
        if name in ("_train-one", "_predict-one"):
            c.add_argument("--split", required=True)
        if name == "predict":
            c.add_argument("--mode", choices=("cached", "retrain"))
            c.add_argument("--candidates", type=Path, help="Feature-only NPZ; requires a trained model and --split")
            c.add_argument("--split")
            c.add_argument("--output", type=Path)
        if name == "replay":
            c.add_argument("--split", default="r0_f0")
            c.add_argument("--method", choices=("fusion", "paired", "direct"), default="fusion")
            c.add_argument("--budget", type=int, choices=range(1, 6), default=3)
            c.add_argument("--seed", type=int, default=42, help="Replay tie draw only; benchmark always uses exact random-tie expectation")
            c.add_argument("--reveal", action="store_true")
            c.add_argument("--output", type=Path)
    sub.add_parser("check")
    return p


def main():
    args = parser().parse_args()
    environment()
    if args.command == "check":
        data = Dataset()
        result = {"pass": True, "environment": environment(), "asset_splits": len(data.splits),
                  "ligands": len(data.ids), "feature_dimension": data.features.shape[1]}
    elif args.command == "run":
        result = workflow.run_pipeline(args.output, args.mode, args.splits)
    elif args.command == "prepare":
        run = workflow.prepare(args.output, args.splits, args.mode)
        result = {"output": str(run), "prepared": True}
    elif args.command == "train":
        workflow.train(args.run_dir)
        result = {"trained": True, "output": str(args.run_dir.resolve())}
    elif args.command == "_train-one":
        result = workflow.train_one(args.run_dir, args.split)
    elif args.command == "_predict-one":
        result = workflow.predict_one(args.run_dir, args.split)
    elif args.command == "predict":
        if args.candidates:
            if not args.split:
                raise ValueError("--candidates requires --split")
            result = workflow.predict_external(args.run_dir, args.split, args.candidates)
            if args.output:
                write_json(args.output, result)
        else:
            if args.split or args.output:
                raise ValueError("--split and --output here require --candidates")
            workflow.predict(args.run_dir, args.mode)
            result = {"predicted": True, "output": str(args.run_dir.resolve())}
    elif args.command == "evaluate":
        result = workflow.evaluate(args.run_dir)["summary"]
    elif args.command == "replay":
        method = {"fusion": "equal_rank", "paired": "paired_ET", "direct": "direct_Q_ET"}[args.method]
        result = workflow.replay(args.run_dir, args.split, args.budget, method, args.reveal, args.seed)
        if args.output:
            write_json(args.output, result)
    elif args.command == "verify":
        result = workflow.verify(args.run_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
