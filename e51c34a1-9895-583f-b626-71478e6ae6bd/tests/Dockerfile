# syntax=docker/dockerfile:1.17@sha256:38387523653efa0039f8e1c89bb74a30504e76ee9f565e25c9a09841f9427b05
FROM --platform=$BUILDPLATFORM python:3.12-slim@sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f AS deps
ARG TARGETARCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
WORKDIR /build
COPY requirements.txt /build/requirements.txt
RUN case "$TARGETARCH" in amd64) a=x86_64 ;; arm64) a=aarch64 ;; *) echo "unsupported $TARGETARCH" >&2; exit 1 ;; esac \
 && python -m pip install --no-cache-dir --disable-pip-version-check --require-hashes --only-binary=:all: \
      --platform="manylinux_2_28_$a" --platform="manylinux_2_17_$a" --platform="manylinux2014_$a" --python-version=3.12 --implementation=cp --target=/build/site -r /build/requirements.txt
ADD --checksum=sha256:2a2e7fd5a87e533b8ecc014836dd78c160a7dd445629ee9795b682d3be5004f9 https://codeload.github.com/harbor-framework/harbor/tar.gz/fdba28fc411e47e8765420a1a063b4918fce3def /build/harbor.tar.gz
RUN mkdir -p /build/src /build/bin \
 && tar -xzf /build/harbor.tar.gz -C /build/src harbor-fdba28fc411e47e8765420a1a063b4918fce3def/packages/rewardkit/src/rewardkit \
 && cp -r /build/src/harbor-fdba28fc411e47e8765420a1a063b4918fce3def/packages/rewardkit/src/rewardkit /build/site/rewardkit \
 && printf '#!/bin/sh\nexec python -m rewardkit "$@"\n' > /build/bin/rewardkit \
 && chmod 0755 /build/bin/rewardkit \
 && mkdir -p /build/logs/verifier

FROM python:3.12-slim@sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f AS runtime
LABEL org.opencontainers.image.title="abs-auto-forward-flow-purchase verifier" \
      org.opencontainers.image.source="https://github.com/EtharaOrion/mephisto" \
      org.opencontainers.image.revision="abs-auto-forward-flow-purchase 1.0.0" \
      org.opencontainers.image.licenses="CC-BY-NC-ND-4.0 AND Apache-2.0" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim" \
      org.opencontainers.image.base.digest="sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f"
COPY --from=deps /build/site /opt/rewardkit/site
COPY --from=deps /build/bin/rewardkit /usr/local/bin/rewardkit
COPY --from=deps --chown=1000:1000 /build/logs/ /logs/
COPY --chmod=0755 test.sh /tests/test.sh
COPY --chmod=0644 test_output.py expected.json reward.toml /tests/
ENV PYTHONPATH=/opt/rewardkit/site PYTHONDONTWRITEBYTECODE=1
WORKDIR /home/workspace
USER 1000:1000
CMD ["sleep", "infinity"]
