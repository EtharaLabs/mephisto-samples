"""Measure the two public cheap controls without reading judge-private targets."""
from pathlib import Path
from portfolio import predict, write


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    for method in ('naive_constant','target_encoding_alone'):
        write(root/'solution/measurements/results'/method/'predictions.jsonl',
              predict(root/'environment/workspace',method))
