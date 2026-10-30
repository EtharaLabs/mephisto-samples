#!/bin/bash
set -uxo pipefail
echo ">>>>> Start Test Output"
cd /workspace && mkdir -p /logs/verifier && echo IyEvYmluL3NoCnNldCAtZXUKZXhwb3J0IFBZVEhPTkRPTlRXUklURUJZVEVDT0RFPTEKZXhlYyBweXRob24zIC1JIC1CIC90ZXN0cy9zY29yaW5nL2VudHJ5cG9pbnQucHkK | base64 -d > /tmp/harbor_test.sh && chmod +x /tmp/harbor_test.sh && bash /tmp/harbor_test.sh; SCORE=$(cat /logs/verifier/reward.txt 2>/dev/null | tr -dc '0-9.-' || echo 0); echo "{\"score\": ${SCORE:-0}}" 2>&1
EXIT_CODE=$?
echo ">>>>> End Test Output"
echo "Exit code: $EXIT_CODE"
exit 0
