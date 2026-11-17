# Agent image; build with environment/ as the context. Private files never enter it.
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
ARG DEBIAN_SNAPSHOT=20261110T000000Z
# Repo-level pin: snapshot.debian.org freezes every package version at this timestamp,
# so per-package "=version" pins are unnecessary and would break across architectures
# (Debian binNMU suffixes differ per arch). Aborts if the base is not the pinned suite.
# hadolint ignore=DL3008
RUN . /etc/os-release \
 && { [ "$VERSION_CODENAME" = "trixie" ] || { echo "base is $VERSION_CODENAME, snapshot pins trixie" >&2; exit 1; }; } \
 && rm -f /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT} trixie main" \
      "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT} trixie-updates main" \
      "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT} trixie-security main" \
    > /etc/apt/sources.list.d/snapshot.list \
 && printf 'Acquire::Retries "10";\nAcquire::http::Timeout "60";\n' \
    > /etc/apt/apt.conf.d/99snapshot \
 && apt-get update \
 && apt-get install -y --no-install-recommends git curl jq build-essential ca-certificates sudo xz-utils \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/agent-requirements.txt
RUN pip install --no-cache-dir -r /tmp/agent-requirements.txt && rm /tmp/agent-requirements.txt
RUN useradd --create-home --uid 1000 --shell /bin/bash agent \
 && echo 'agent ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/agent && chmod 0440 /etc/sudoers.d/agent \
 && mkdir -p /workspace
COPY workspace/ /workspace/
RUN chown -R agent:agent /workspace
WORKDIR /workspace
# Harbor runs agent setup as root; the agent itself runs as [agent].user (1000:1000).
USER root
