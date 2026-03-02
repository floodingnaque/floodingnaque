# Load Test Baseline Results
# ==========================
# This directory stores load test baseline results for tracking performance
# over time. Run the baseline test before each production deploy.
#
# How to generate:
#   cd backend
#   locust -f tests/load/locustfile.py \
#     --config tests/load/baseline.conf \
#     --host https://staging-api.floodingnaque.com
#
# Expected baselines (50 concurrent users):
#   - /health: P95 < 200ms, 0% failure
#   - /api/v1/health: P95 < 500ms, 0% failure
#   - /api/v1/predict: P95 < 2000ms, < 1% failure
#
# Commit the results after each baseline run so regressions are visible.
