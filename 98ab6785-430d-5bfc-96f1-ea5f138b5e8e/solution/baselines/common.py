"""Runnable controls. Copy-forward means no additional payments after latest diagonal."""
import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def author_module(filename):
    path = Path(__file__).resolve().parents[1] / filename
    spec = importlib.util.spec_from_file_location("reserving_" + path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load author module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


public = author_module("public_reference.py")
package, prediction, read_jsonl = public.package, public.prediction, public.read_jsonl


def solve(kind, data_dir):
    if kind == "empty":
        return {"predictions": [], "self_reported_metrics": {}}
    if kind == "public_reference":
        return public.solve(data_dir)
    train = read_jsonl(Path(data_dir) / "train.jsonl")
    series = defaultdict(dict)
    for r in train:
        series[r["record_id"]][r["development_lag"]] = r
    factors = {}
    for lob in sorted({r["lob"] for r in train}):
        for lag in range(1, 10):
            pairs = [(s[lag]["paid"], s[lag + 1]["paid"]) for s in series.values()
                     if s[lag]["lob"] == lob]
            factors[lob, lag] = sum(b for _, b in pairs) / max(sum(a for a, _ in pairs), 1.0)
    predictions = []
    for q in read_jsonl(Path(data_dir) / "queries.jsonl"):
        r = q["history"][-1]
        cash, cumulative = {}, r["paid"]
        for lag in range(r["development_lag"] + 1, 11):
            next_paid = cumulative if kind == "copy_forward" else cumulative * factors[r["lob"], lag - 1]
            cash[lag] = next_paid - cumulative
            cumulative = next_paid
        predictions.append(prediction(r, cash, {}))
    return package(predictions)


def main(kind):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("/workspace/data"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from baselines.adapt import adapt
    result = adapt(solve(kind, args.data_dir), read_jsonl(args.data_dir / "train.jsonl"),
                   read_jsonl(args.data_dir / "queries.jsonl"), kind)
    args.output.write_text(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
