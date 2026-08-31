import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "wsaj_video_corpus.py"
SPEC = importlib.util.spec_from_file_location("wsaj_video_corpus", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RelevanceTest(unittest.TestCase):
    def test_title_match_has_more_weight_than_transcript_match(self):
        title = MODULE.relevance({"title": "PER 가치평가"}, "일반 설명")
        transcript = MODULE.relevance({"title": "일반 설명"}, "PER 가치평가")

        self.assertGreater(title["score"], transcript["score"])

    def test_matches_keep_category_and_location(self):
        result = MODULE.relevance(
            {"title": "기업 분석"},
            "내재가치와 상대가치를 구분하고 안전마진을 확인한다.",
        )

        self.assertIn("valuation", result["matches"])
        self.assertEqual(
            result["matches"]["valuation"]["내재가치"],
            {"title": 0, "transcript": 1},
        )
        self.assertIn("judgment", result["matches"])


class TranscriptTest(unittest.TestCase):
    def test_compact_transcript_preserves_segment_timestamps(self):
        result = MODULE.compact_transcript(
            {
                "language": "ko",
                "text": " 가치평가 ",
                "segments": [{"start": 1.234, "end": 2.345, "text": " 내재가치 "}],
            }
        )

        self.assertEqual(result["text"], "가치평가")
        self.assertEqual(
            result["segments"],
            [{"start": 1.23, "end": 2.35, "text": "내재가치"}],
        )


class DownloadCommandTest(unittest.TestCase):
    def test_public_android_client_is_tried_without_browser_cookies(self):
        commands = MODULE.download_commands(
            "https://www.youtube.com/watch?v=video-id",
            Path("/tmp/wsaj-test"),
            None,
        )

        self.assertEqual(len(commands), 1)
        self.assertIn("youtube:lang=ko;player_client=android", commands[0])
        self.assertIn("--no-cookies", commands[0])

    def test_saved_browser_cookie_is_only_a_fallback(self):
        commands = MODULE.download_commands(
            "https://www.youtube.com/watch?v=video-id",
            Path("/tmp/wsaj-test"),
            Path("/tmp/session-cookies.txt"),
        )

        self.assertEqual(len(commands), 2)
        self.assertIn("--no-cookies", commands[0])
        self.assertIn("--cookies", commands[1])


if __name__ == "__main__":
    unittest.main()
