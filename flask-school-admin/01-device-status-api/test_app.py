import unittest
from app import app

class DeviceApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_lists_devices(self):
        response = self.client.get("/api/devices")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 2)

    def test_filters_online_devices(self):
        response = self.client.get("/api/devices?online=true")
        rows = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["hostname"] for row in rows], ["lab-pc-01"])

if __name__ == "__main__":
    unittest.main()
