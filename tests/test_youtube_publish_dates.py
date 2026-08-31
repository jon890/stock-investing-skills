import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_youtube_publish_dates  # pyright: ignore[reportMissingImports]


class YoutubePublishDatesTest(unittest.TestCase):
    def test_parse_upload_date(self):
        html = '<meta itemprop="uploadDate" content="2021-09-06T19:59:20-07:00">'

        self.assertEqual(fetch_youtube_publish_dates.parse_upload_date(html), "2021-09-06")

    def test_enrich_reuses_one_fetch_per_video(self):
        calls = []
        payload = {
            "evidence": [
                {"video_id": "same", "source_date": "wrong"},
                {"video_id": "same", "source_date": "wrong"},
                {"video_id": "other", "source_date": "wrong"},
            ],
            "source_date_note": "temporary",
        }

        result = fetch_youtube_publish_dates.enrich(
            payload,
            fetcher=lambda video_id: calls.append(video_id) or "2020-01-02",
        )

        self.assertEqual(calls, ["other", "same"])
        self.assertNotIn("source_date_note", result)
        self.assertTrue(all(row["source_date"] == "2020-01-02" for row in result["evidence"]))
        self.assertTrue(all(row["source_date_status"] == "verified_upload_date" for row in result["evidence"]))


if __name__ == "__main__":
    unittest.main()
