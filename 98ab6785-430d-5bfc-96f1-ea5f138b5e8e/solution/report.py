"""Print the exact file inventory and measured lane breakdown without mutations."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for path in sorted(root.rglob("*")):
    if path.is_file():
        print(f"{path.relative_to(root)}\t{path.stat().st_size}")
summary = json.loads((root / "solution/measurements/summary.json").read_text())
print(json.dumps({k: v for k, v in summary.items() if k != "scores"}, indent=2))
for name in summary["ordering"]:
    report = summary["scores"][name]
    print(name, f"{report['score']:.6f}",
           {lane: round(row["points"], 6) for lane, row in report["lanes"].items()})
