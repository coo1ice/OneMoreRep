import json
import unittest
from pathlib import Path
from unittest.mock import patch

from onemorerep.services import report_service


class StatisticsQueryTests(unittest.TestCase):
    def test_statistics_query_parameters_match_placeholders(self):
        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, query, params):
                self.query = query
                self.params = params
                return self

            def fetchone(self):
                return {}

        connection = Connection()
        with patch.object(report_service, "connect", return_value=connection):
            report_service.statistics(42)

        self.assertEqual(connection.query.count("%s"), len(connection.params))
        self.assertEqual(connection.params, (42,) * 14)


class VercelRoutingTests(unittest.TestCase):
    def test_clean_urls_are_enabled_for_exported_pages(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "vercel.json").read_text(encoding="utf-8"))
        self.assertTrue(config["cleanUrls"])
        self.assertEqual(config["outputDirectory"], "frontend/out")
        self.assertEqual(config["buildCommand"], "cd frontend && npm ci && npm run build")
        self.assertTrue((root / "api" / "index.py").is_file())


if __name__ == "__main__":
    unittest.main()
