"""Public-only hybrid reference; measured independently and never used to set floors."""
import argparse
from pathlib import Path

from portfolio import predict, write_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    write_rows(args.output, predict(args.workspace, 'hybrid'))


if __name__ == '__main__':
    main()
