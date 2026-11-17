"""Frozen competent one-shot portfolio. Only public inputs are opened by the worker."""
import argparse
from pathlib import Path

from public_reference import predictions, write_rows

FLOOR_METHODS = ('ridge_closed', 'rf_closed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    for method in FLOOR_METHODS:
        write_rows(Path(args.output_dir) / method / 'predictions.jsonl', predictions(args.workspace, method))


if __name__ == '__main__':
    main()
