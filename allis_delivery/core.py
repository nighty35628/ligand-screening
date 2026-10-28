"""Locked data schema and the two selected estimators; no research-path imports."""
from __future__ import annotations

import gzip
import hashlib
import importlib.metadata
import json
import platform
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

ASSETS = Path(__file__).resolve().parent / "assets"
METHODS = ("paired_ET", "direct_Q_ET", "equal_rank")
LOCKED_VERSIONS = {
    "numpy": "2.5.4", "scipy": "1.16.2", "scikit-learn": "1.7.2",
    "joblib": "1.6.0", "threadpoolctl": "3.6.0", "cloudpickle": "3.1.2",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, obj):
    path = Path(path)
    require(not path.exists(), f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_seal(root, files, path, **metadata):
    root = Path(root).resolve()
    write_json(path, {"files": {str(Path(f).resolve().relative_to(root)): sha(f) for f in files}, **metadata})


def check_seal(root, path):
    root = Path(root).resolve()
    obj = read_json(path)
    for relative, digest in obj["files"].items():
        resolved = (root / relative).resolve()
        require(resolved.is_relative_to(root), "Seal path escapes its root")
        require(resolved.is_file() and sha(resolved) == digest, f"Integrity check failed: {resolved}")
    return obj


def environment(check=True):
    versions = {name: importlib.metadata.version(name) for name in LOCKED_VERSIONS}
    if check:
        require(platform.python_version_tuple()[:2] == ("3", "12"), "Use Python 3.12 for the locked reproduction")
        require(versions == LOCKED_VERSIONS, "Dependency versions differ; install requirements-allis.txt")
    return {"python": platform.python_version(), **versions}


def quality(curves):
    values = np.asarray(curves, dtype=float)
    require(values.ndim == 2 and values.shape[1] == 40 and np.isfinite(values).all(), "Expected finite N x 40 FOM values")
    return np.sort(values, axis=1)[:, -4:].mean(axis=1)


class Dataset:
    def __init__(self):
        check_seal(ASSETS, ASSETS / "manifest.json")
        self.config = read_json(ASSETS / "config.json")
        self.metadata = read_json(ASSETS / "data/metadata.json")
        self.molecules = self.metadata["molecules"]
        self.splits = read_json(ASSETS / "data/splits.json")
        with np.load(ASSETS / "data/inputs.npz", allow_pickle=False) as data:
            self.features = data["morgan"].copy()
            self.dose = data["dose"].copy()
        self.feature_names = self.metadata["original_feature_names"] + [f"morgan_count_{i:04d}" for i in range(2048)]
        self.ids = [m["id"] for m in self.molecules]
        require(self.features.shape == (90, 2090) and self.dose.shape == (90, 40), "Unexpected locked data shape")
        require(len(set(self.ids)) == 90 and len(self.feature_names) == 2090, "Identity/schema mismatch")
        require(np.isfinite(self.features).all() and np.isfinite(self.dose).all(), "Non-finite input")
        require((self.dose > 0).all() and (np.diff(self.dose, axis=1) > 0).all(), "Dose grid must increase and be positive")
        for split in self.splits:
            require(len(split["train"]) == 36 and len(split["test"]) == 18, "Unexpected split size")
            require(not set(split["train"]) & set(split["test"]), "Training/test leakage")

    def split(self, name):
        found = [s for s in self.splits if s["id"] == name]
        require(len(found) == 1, f"Unknown split: {name}")
        return found[0]

    def responses(self, indices):
        """Training requests only its 36 IDs; prediction never calls this method."""
        wanted = [self.ids[int(i)] for i in indices]
        rows = {ident: [] for ident in wanted}
        raw = read_json_gzip(ASSETS / "data/reaction_collection_train_AL0503.json.gz")
        for reaction in raw["reactions"]:
            if reaction["properties"].get("WallTag") != 1:
                continue
            solution = reaction["ligand_solutions"][0]
            ident = solution["solute"]["identifier"]
            if ident in rows:
                rows[ident].append((solution["concentration"] * solution["volume"], reaction["properties"]["FigureOfMerit"]))
        curves = np.asarray([[y for _, y in sorted(rows[ident])] for ident in wanted], dtype=float)
        quality(curves)  # validates all 40 labels, not just the largest four
        return curves

    def candidates(self, split):
        ix = split["test"]
        return {"features": self.features[ix].copy(), "dose_pmol": self.dose[ix].copy(),
                "ids": np.asarray([self.ids[i] for i in ix]),
                "feature_names": np.asarray(self.feature_names)}


def read_json_gzip(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def select_columns(features, train):
    kept, removed = [], []
    for k in range(features.shape[1]):
        v = features[train, k]
        if np.ptp(v) <= 1e-12:
            removed.append({"column": k, "reason": "training_constant"})
            continue
        duplicate = next((j for j in kept if k >= 42 and np.array_equal(v, features[train, j])), None)
        if duplicate is not None:
            removed.append({"column": k, "reason": "training_exact_duplicate", "retained": duplicate})
        else:
            kept.append(k)
    return np.asarray(kept, dtype=int), removed


def point_inputs(features, dose):
    return np.c_[np.repeat(features, 40, axis=0), dose.ravel()].astype(np.float32)


def pair_inputs(a, b):
    return np.concatenate([a, b, a - b], axis=1)


@dataclass
class ModelBundle:
    schema: int
    split: str
    columns: np.ndarray
    feature_names: list[str]
    training_ids: list[str]
    paired: ExtraTreesRegressor
    direct: ExtraTreesRegressor
    reference_x: np.ndarray
    reference_y: np.ndarray


def fit_models(data, split):
    tr = split["train"]
    cfg = data.config["folds"][split["id"]]
    keep, removed = select_columns(data.features, tr)
    require(keep.tolist() == cfg["expected_columns"] and removed == cfg["expected_removed"], "Molecular filtering drift")
    features = data.features[:, keep]
    labels = data.responses(tr)
    x = point_inputs(features[tr], data.dose[tr])
    y = labels.ravel()
    with np.load(ASSETS / "data" / split["pairs_file"], allow_pickle=False) as pairs:
        i, j = pairs["i"], pairs["j"]
    require(len(i) == cfg["training_pairs"] == 131072, "Pair budget drift")
    paired = ExtraTreesRegressor(**cfg["paired_params"])
    paired.fit(pair_inputs(x[i], x[j]), y[i] - y[j])
    direct = ExtraTreesRegressor(**cfg["direct_params"])
    direct.fit(features[tr], quality(labels))
    return ModelBundle(1, split["id"], keep, data.feature_names,
                       [data.ids[k] for k in tr], paired, direct, x, y)


def validate_candidates(candidate, feature_names):
    required = {"features", "dose_pmol", "ids", "feature_names"}
    require(set(candidate) == required, f"Candidate NPZ must contain exactly {sorted(required)}; no labels")
    x = np.asarray(candidate["features"], dtype=np.float32)
    dose = np.asarray(candidate["dose_pmol"], dtype=np.float32)
    ids = np.asarray(candidate["ids"])
    require(ids.dtype.kind in "US" and ids.ndim == 1 and len(ids) > 0, "Candidate IDs must be non-empty strings")
    require(len(set(ids.tolist())) == len(ids), "Duplicate candidate IDs")
    require(x.shape == (len(ids), len(feature_names)) and dose.shape == (len(ids), 40), "Candidate matrix shape mismatch")
    require(np.asarray(candidate["feature_names"]).tolist() == feature_names, "Feature names/order mismatch")
    require(np.isfinite(x).all() and np.isfinite(dose).all(), "Non-finite candidate inputs")
    require((dose > 0).all() and (np.diff(dose, axis=1) > 0).all(), "Invalid dose grid")
    return x, dose, ids.tolist()


def predict_models(bundle, candidate):
    require(bundle.schema == 1, "Unknown model schema")
    features, dose, ids = validate_candidates(candidate, bundle.feature_names)
    require(not set(ids) & set(bundle.training_ids), "Candidate IDs overlap training IDs")
    x = features[:, bundle.columns]
    query = point_inputs(x, dose)
    ref = bundle.reference_x
    n = len(ref)
    batch = max(1, int(48 * 1024**2 / (n * ref.shape[1] * 3 * 4)))
    mu = []
    for lo in range(0, len(query), batch):
        points = query[lo:lo + batch]
        diffs = bundle.paired.predict(pair_inputs(np.repeat(points, n, axis=0), np.tile(ref, (len(points), 1))))
        mu.extend((diffs.reshape(len(points), n) + bundle.reference_y[None, :]).mean(axis=1))
    curves = np.asarray(mu).reshape(len(ids), 40)
    direct = bundle.direct.predict(x)
    require(np.isfinite(curves).all() and np.isfinite(direct).all(), "Non-finite predictions")
    return {"ids": ids, "paired_q": quality(curves).tolist(), "direct_q": direct.tolist(),
            "paired_curves": curves.tolist(), "dose_pmol": dose.tolist()}
