FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN mkdir -p /tests/scoring /tests/hidden_test_data /logs/verifier /workspace

COPY scoring/entrypoint.py scoring/eval_script.py scoring/score.py scoring/scorer_manifest.json scoring/judge_requirements.txt /tests/scoring/
COPY hidden_test_data/outcomes.jsonl /tests/hidden_test_data/outcomes.jsonl
COPY test.sh /tests/test.sh
RUN chmod 0755 /tests/test.sh

WORKDIR /workspace
CMD ["/tests/test.sh"]
