import json
import unittest
from unittest.mock import patch

import ollama_probe


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, *args, **kwargs):
        return json.dumps(self.payload).encode("utf-8")


class OllamaProbeTests(unittest.TestCase):
    @patch("ollama_probe.urllib.request.urlopen")
    def test_required_model_is_detected(self, urlopen) -> None:
        urlopen.side_effect = [
            FakeResponse({"version": "0.0.0-example"}),
            FakeResponse(
                {
                    "models": [
                        {"name": "example-model"},
                        {"name": "other-model"},
                    ]
                }
            ),
        ]

        result = ollama_probe.probe(
            "http://127.0.0.1:11434",
            required_model="example-model",
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.required_model_present)
        self.assertEqual(result.version, "0.0.0-example")

    @patch("ollama_probe.urllib.request.urlopen")
    def test_missing_required_model_is_distinct_from_api_failure(self, urlopen) -> None:
        urlopen.side_effect = [
            FakeResponse({"version": "0.0.0-example"}),
            FakeResponse({"models": [{"name": "other-model"}]}),
        ]

        result = ollama_probe.probe(
            "http://127.0.0.1:11434",
            required_model="example-model",
        )

        self.assertFalse(result.ok)
        self.assertFalse(result.required_model_present)
        self.assertIsNone(result.error)


if __name__ == "__main__":
    unittest.main()
