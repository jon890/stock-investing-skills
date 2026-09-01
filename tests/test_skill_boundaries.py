from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def iter_skill_instruction_files():
    for path in ROOT.glob("skills/**/SKILL.md"):
        yield path
    for path in ROOT.glob("skills/**/references/*.md"):
        yield path


class SkillBoundaryTest(unittest.TestCase):
    def test_runtime_skills_do_not_read_cache_sources(self):
        offenders = []
        for path in iter_skill_instruction_files():
            text = path.read_text(encoding="utf-8")
            if ".cache" in text:
                offenders.append(str(path.relative_to(ROOT)))

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
