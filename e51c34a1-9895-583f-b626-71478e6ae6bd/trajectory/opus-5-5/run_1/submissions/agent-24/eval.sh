#!/bin/bash
set -uxo pipefail
echo ">>>>> Start Test Output"
cd /home/workspace && mkdir -p /logs/verifier && echo IyEvYmluL2Jhc2gKc2V0IC11byBwaXBlZmFpbApta2RpciAtcCAvbG9ncy92ZXJpZmllcgpyZXdhcmRraXQgL3Rlc3RzIC0td29ya3NwYWNlIC9ob21lL3dvcmtzcGFjZSAtLW91dHB1dCAvbG9ncy92ZXJpZmllci9yZXdhcmQuanNvbiA+IC9sb2dzL3ZlcmlmaWVyL3Jld2FyZGtpdC5sb2cgMj4mMQpweXRob24zIC1jICJpbXBvcnQganNvbjtwcmludChqc29uLmxvYWQob3BlbignL2xvZ3MvdmVyaWZpZXIvcmV3YXJkLmpzb24nKSlbJ3Jld2FyZCddKSIgPiAvbG9ncy92ZXJpZmllci9yZXdhcmQudHh0CmNhdCAvbG9ncy92ZXJpZmllci9yZXdhcmQudHh0Cg== | base64 -d > /tmp/harbor_test.sh && chmod +x /tmp/harbor_test.sh && bash /tmp/harbor_test.sh; SCORE=$(cat /logs/verifier/reward.txt 2>/dev/null | tr -dc '0-9.-' || echo 0); echo "{\"score\": ${SCORE:-0}}" 2>&1
EXIT_CODE=$?
echo ">>>>> End Test Output"
echo "Exit code: $EXIT_CODE"
exit 0
