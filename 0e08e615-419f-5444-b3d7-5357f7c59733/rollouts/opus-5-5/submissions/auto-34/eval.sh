#!/bin/bash
set -uxo pipefail
echo ">>>>> Start Test Output"
cd /workspace && mkdir -p /logs/verifier && echo IyEvYmluL3NoCiMgQm90aCByZXdhcmQgY2FycmllcnMgc3RhcnQgYXQgemVybzsgYSBzY29yZXIgZmFpbHVyZSBjYW5ub3QgcHVibGlzaCBzdGFsZSBjcmVkaXQuCnNldCAtdQpleHBvcnQgUFlUSE9ORE9OVFdSSVRFQllURUNPREU9MQpoZXJlPS90ZXN0cyAgIyBzZm9yZ2UgcnVucyB0aGlzIHNjcmlwdCBmcm9tIC90bXA7IHRoZSBzY29yZXIgbGl2ZXMgYXQgL3Rlc3RzIChqdWRnZSBEb2NrZXJmaWxlIENPUFkgLiAvdGVzdHMvKQpsb2dzPSIke1ZFUklGSUVSX0xPR19ESVI6LS9sb2dzL3ZlcmlmaWVyfSIKbWtkaXIgLXAgIiRsb2dzIiB8fCBleGl0IDEKcHJpbnRmICcwXG4nID4gIiRsb2dzL3Jld2FyZC50eHQiIHx8IGV4aXQgMQpwcmludGYgJ3sicmV3YXJkIjowfVxuJyA+ICIkbG9ncy9yZXdhcmQuanNvbiIgfHwgZXhpdCAxCnB5dGhvbjMgLUkgLUIgIiRoZXJlL3Njb3JpbmcvZXZhbC5weSIgLS1zdWJtaXNzaW9uLWRpciAiJHsxOi0vd29ya3NwYWNlfSIgLS1sb2ctZGlyICIkbG9ncyIgfHwgZXhpdCAwCg== | base64 -d > /tmp/harbor_test.sh && chmod +x /tmp/harbor_test.sh && bash /tmp/harbor_test.sh; SCORE=$(cat /logs/verifier/reward.txt 2>/dev/null | tr -dc '0-9.-' || echo 0); echo "{\"score\": ${SCORE:-0}}" 2>&1
EXIT_CODE=$?
echo ">>>>> End Test Output"
echo "Exit code: $EXIT_CODE"
exit 0
