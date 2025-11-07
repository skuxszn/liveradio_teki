"""
Load tests for the 24/7 FFmpeg YouTube Radio Stream using Locust.

Run with:
    locust -f tests/load/locustfile.py --host=http://localhost:9000
    
Or for headless mode:
    locust -f tests/load/locustfile.py --host=http://localhost:9000 \
           --users 10 --spawn-rate 2 --run-time 5m --headless
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from typing import Dict, Any


class AzuraCastWebhookUser(HttpUser):
    """
    Simulates AzuraCast sending webhook notifications for track changes.
    """

    # Wait between 1-5 seconds between tasks (simulating track changes)
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.track_count = 0
        self.track_library = self._generate_track_library()

    def _generate_track_library(self) -> list:
        """Generate a library of test tracks."""
        artists = [
            "Electronic Dreams",
            "Synthwave Collective",
            "Bass Master",
            "DJ TechnoVibes",
            "Ambient Space",
            "Drum & Bass United",
            "Future House",
            "Trance Nation",
            "Progressive Beats",
        ]

        titles = [
            "Midnight Drive",
            "Neon Lights",
            "Digital Horizon",
            "Cyber City",
            "Electric Dreams",
            "Quantum Leap",
            "Stellar Journey",
            "Time Traveler",
            "Cosmic Dance",
        ]

        albums = [
            "Best of 2025",
            "Summer Hits",
            "Night Sessions",
            "Epic Collection",
            "The Greatest Mixes",
            "Live at Club",
        ]

        tracks = []
        for i in range(100):
            tracks.append(
                {
                    "artist": random.choice(artists),
                    "title": f"{random.choice(titles)} {i+1}",
                    "album": random.choice(albums),
                    "id": str(1000 + i),
                    "duration": random.randint(120, 300),
                }
            )

        return tracks

    def _get_webhook_payload(self) -> Dict[str, Any]:
        """Generate a random webhook payload."""
        track = random.choice(self.track_library)
        self.track_count += 1

        return {
            "song": {
                "id": track["id"],
                "text": f"{track['artist']} - {track['title']}",
                "artist": track["artist"],
                "title": track["title"],
                "album": track["album"],
                "genre": "Electronic",
                "duration": track["duration"],
                "art": f"https://example.com/art/{track['id']}.jpg",
            },
            "station": {
                "id": "1",
                "name": "Load Test Station",
                "shortcode": "loadtest",
                "listen_url": "http://test.azuracast.local:8000/radio",
            },
            "live": {"is_live": False, "streamer_name": "", "broadcast_start": None},
            "now_playing": {
                "sh_id": self.track_count,
                "played_at": int(time.time()),
                "duration": track["duration"],
                "playlist": "Main Playlist",
                "is_request": False,
                "elapsed": 0,
                "remaining": track["duration"],
            },
        }

    @task(10)
    def send_track_change_webhook(self):
        """Send a track change webhook (most common task)."""
        payload = self._get_webhook_payload()

        with self.client.post(
            "/webhook/azuracast",
            json=payload,
            headers={"Content-Type": "application/json", "X-Webhook-Secret": "test-webhook-secret"},
            catch_response=True,
            name="Track Change Webhook",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def check_health(self):
        """Check the health endpoint."""
        with self.client.get("/health", catch_response=True, name="Health Check") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def check_status(self):
        """Check the status endpoint."""
        with self.client.get("/status", catch_response=True, name="Status Check") as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "current_track" in data and "ffmpeg_status" in data:
                        response.success()
                    else:
                        response.failure("Status response missing expected fields")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status check failed: {response.status_code}")

    @task(1)
    def send_invalid_webhook(self):
        """Send an invalid webhook to test error handling."""
        invalid_payloads = [
            {},  # Empty payload
            {"invalid": "data"},  # Missing required fields
            {"song": {"artist": "Test"}},  # Incomplete song data
        ]

        payload = random.choice(invalid_payloads)

        with self.client.post(
            "/webhook/azuracast",
            json=payload,
            headers={"Content-Type": "application/json", "X-Webhook-Secret": "test-webhook-secret"},
            catch_response=True,
            name="Invalid Webhook",
        ) as response:
            # We expect this to fail with 422 or 400
            if response.status_code in [400, 422]:
                response.success()
            else:
                response.failure(f"Expected 400/422, got {response.status_code}")


class RapidTrackChangeUser(HttpUser):
    """
    Simulates rapid track changes (stress test scenario).
    """

    wait_time = between(0.5, 1.0)  # Very fast track changes

    @task
    def rapid_track_changes(self):
        """Send rapid track changes to stress test the system."""
        payload = {
            "song": {
                "id": str(random.randint(1, 1000)),
                "artist": f"Artist {random.randint(1, 100)}",
                "title": f"Track {random.randint(1, 1000)}",
                "duration": 180,
            },
            "station": {"id": "1", "name": "Stress Test Station"},
        }

        self.client.post(
            "/webhook/azuracast",
            json=payload,
            headers={"Content-Type": "application/json", "X-Webhook-Secret": "test-webhook-secret"},
            name="Rapid Track Change",
        )


# Custom events for tracking
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the load test starts."""
    print("=" * 60)
    print("Starting load test for 24/7 FFmpeg YouTube Radio Stream")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test stops."""
    print("=" * 60)
    print("Load test completed")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"RPS: {environment.stats.total.total_rps:.2f}")
    print("=" * 60)
