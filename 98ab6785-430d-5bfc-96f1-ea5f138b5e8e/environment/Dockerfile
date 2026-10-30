FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl jq build-essential ca-certificates sudo xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash -u 1000 agent \
    && printf 'agent ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/agent \
    && chmod 0440 /etc/sudoers.d/agent \
    && mkdir -p /workspace/data \
    && chown -R agent:agent /workspace

WORKDIR /workspace
COPY --chown=agent:agent attachments/train.jsonl attachments/queries.jsonl /workspace/data/

USER agent
RUN git config --global safe.directory '*'
CMD ["python3"]
