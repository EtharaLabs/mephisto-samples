"""Judge-only static-artifact evaluator. Never executes or imports submitted code."""
import argparse
import json
from pathlib import Path

from score import evaluate


def reject_constant(value):
    raise ValueError(f"nonstandard JSON constant: {value}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission-dir", type=Path, default=Path("/workspace"))
    parser.add_argument("--input", type=Path, default=Path("/tests/hidden_test_data/outcomes.jsonl"))
    parser.add_argument("--log-dir", type=Path, default=Path("/logs/verifier"))
    a = parser.parse_args()
    # Infrastructure errors intentionally propagate; never disguise missing truth as agent failure.
    outcomes = [json.loads(line) for line in a.input.read_text().splitlines()]
    reason = None
    try:
        for name in ("reserving.py", "requirements.txt", "reserving_results.json"):
            path = a.submission_dir / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("missing or symlinked submission artifact")
        path = a.submission_dir / "reserving_results.json"
        if path.stat().st_size > 20_000_000:
            raise ValueError("results JSON exceeds 20 MB")
        document = json.loads(path.read_text(), parse_constant=reject_constant)
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        document = {}
        reason = str(exc)
    report = evaluate(document, outcomes)
    if reason:
        report["submission_error"] = reason
    text = json.dumps(report, sort_keys=True, allow_nan=False)
    a.log_dir.mkdir(parents=True, exist_ok=True)
    (a.log_dir / "reward.txt").write_text(f"{report['score']:.10f}\n")
    (a.log_dir / "reward.json").write_text(text + "\n")
    print(">>>>> Start Structured Result")
    print(text)
    print(">>>>> End Structured Result")


if __name__ == "__main__":
    main()
