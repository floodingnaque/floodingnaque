"""
Locust load test for Floodingnaque API.

Run: locust -f tests/qa/locustfile.py --host=http://localhost:5000 \
            --users 100 --spawn-rate 10 --run-time 10m --headless
"""

from locust import HttpUser, task, between

API_KEY = "xK9mR-vL2pN8qW5jT7bF4hD6cY0aG3sE"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


class FloodingnaqueUser(HttpUser):
    wait_time = between(1, 3)

    @task(6)  # 60% of traffic
    def predict_flood(self):
        self.client.post(
            "/api/v1/predict/",
            json={"temperature": 303.15, "humidity": 85.0, "precipitation": 10.0},
            headers=HEADERS,
        )

    @task(3)  # 30% of traffic
    def get_alerts(self):
        self.client.get("/api/v1/alerts", headers=HEADERS)

    @task(1)  # 10% of traffic
    def get_dashboard(self):
        self.client.get("/api/v1/dashboard/summary", headers=HEADERS)
