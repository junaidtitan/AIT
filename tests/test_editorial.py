import unittest
from datetime import datetime, timedelta

from src.editorial.script_daily import ScriptGenerator
from src.editorial.story_analyzer import StoryAnalyzer
from src.editorial.structure_validator import StructureValidator


class EditorialPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        ts = (datetime.now() - timedelta(hours=2)).isoformat()
        self.sample_stories = [
            {
                "title": "OpenAI ships GPT-5 with enterprise guardrails",
                "summary": "GPT-5 launches with autonomous agent safety layers and 60% error reduction.",
                "source_domain": "openai.com",
                "published_ts": ts,
                "full_text": "OpenAI announced GPT-5, a multimodal model with agentic tooling and alignment controls.",
            },
            {
                "title": "DeepMind pushes Gemini across Workspace for 400M users",
                "summary": "Google integrates Gemini into Workspace, turning the suite into a multimodal copilot platform.",
                "source_domain": "deepmind.google",
                "published_ts": ts,
                "full_text": "Gemini scales to Workspace with new memory and agent features.",
            },
        ]

    def test_story_analyzer_scores(self) -> None:
        analyzer = StoryAnalyzer()
        analyzed = analyzer.analyze(self.sample_stories)
        self.assertTrue(analyzed)
        self.assertIn("analysis", analyzed[0])
        self.assertGreaterEqual(analyzed[0]["analysis"]["scores"]["composite"], 0.0)

    def test_script_generator_structure(self) -> None:
        generator = ScriptGenerator()
        package = generator.generate_script(self.sample_stories)
        self.assertIn("vo_script", package)
        validator = package["metadata"]["validator"]
        self.assertIn("score", validator)
        self.assertGreaterEqual(validator["score"], 0.0)

    def test_structure_validator(self) -> None:
        generator = ScriptGenerator()
        package = generator.generate_script(self.sample_stories)
        validator = StructureValidator()
        structure_payload = {
            "acts": package["metadata"]["structure"]["acts"],
            "segments": package["metadata"]["structure"]["segments"],
            "cta": package["metadata"]["structure"]["cta"],
            "headline_blitz": package["metadata"]["structure"]["headline_blitz"],
            "bridge_sentence": package["metadata"]["structure"]["bridge_sentence"],
        }
        result = validator.validate(structure_payload)
        self.assertTrue(result.score >= 0)


if __name__ == "__main__":
    unittest.main()
