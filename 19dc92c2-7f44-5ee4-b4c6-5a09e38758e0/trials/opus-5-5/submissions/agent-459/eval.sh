#!/bin/bash
set -uxo pipefail
echo ">>>>> Start Test Output"
cd /workspace && mkdir -p /logs/verifier && echo IyEvYmluL3NoCiMgRmFpbCBjbG9zZWQsIGFuZCBuZXZlciByZXB1Ymxpc2ggYW4gZWFybGllciBwb3NpdGl2ZSByZXBvcnQuCnNldCAtdQpleHBvcnQgUFlUSE9ORE9OVFdSSVRFQllURUNPREU9MQpMT0dTPSIke1ZFUklGSUVSX0xPR19ESVI6LS9sb2dzL3ZlcmlmaWVyfSIKVEVTVFM9L3Rlc3RzICAjIHNmb3JnZSBydW5zIHRoaXMgc2NyaXB0IGZyb20gL3RtcDsgdGhlIHNjb3JlciBsaXZlcyBhdCAvdGVzdHMgKGp1ZGdlIERvY2tlcmZpbGUgQ09QWSAuIC90ZXN0cy8pCm1rZGlyIC1wICIkTE9HUyIgfHwgZXhpdCAxCnByaW50ZiAnMFxuJyA+ICIkTE9HUy9yZXdhcmQudHh0IgpwcmludGYgJ3sicmV3YXJkIjowfVxuJyA+ICIkTE9HUy9yZXdhcmQuanNvbiIKcm0gLWYgIiRMT0dTL3JlcG9ydC5qc29uIiAiJExPR1MvY3RyZi5qc29uIgppZiBweXRob24zIC1JIC1CICIkVEVTVFMvc2NvcmluZy9ldmFsLnB5IiAtLXN1Ym1pc3Npb24tZGlyICIkezE6LS93b3Jrc3BhY2V9IiAtLWxvZy1kaXIgIiRMT0dTIjsgdGhlbgogIDoKZWxzZQogIHByaW50ZiAnMFxuJyA+ICIkTE9HUy9yZXdhcmQudHh0IgogIHByaW50ZiAneyJyZXdhcmQiOjB9XG4nID4gIiRMT0dTL3Jld2FyZC5qc29uIgpmaQpleGl0IDAK | base64 -d > /tmp/harbor_test.sh && chmod +x /tmp/harbor_test.sh && bash /tmp/harbor_test.sh; SCORE=$(cat /logs/verifier/reward.txt 2>/dev/null | tr -dc '0-9.-' || echo 0); echo "{\"score\": ${SCORE:-0}}" 2>&1
EXIT_CODE=$?
echo ">>>>> End Test Output"
echo "Exit code: $EXIT_CODE"
exit 0
