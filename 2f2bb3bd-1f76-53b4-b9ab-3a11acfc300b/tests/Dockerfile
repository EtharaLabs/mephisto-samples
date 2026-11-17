# Separate verifier; only tests/ enters this image, never the oracle or floor portfolio.
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY . /tests/
RUN chmod 0755 /tests/test.sh && mkdir -p /logs/verifier /workspace
WORKDIR /workspace
USER root
CMD ["/tests/test.sh"]
