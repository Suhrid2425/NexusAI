
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from core.llm import generate_answer


class GenerateAnswerValidationTests(SimpleTestCase):

    def test_empty_question_is_rejected(self):
        with self.assertRaises(ValueError):
            generate_answer("   ", [{"text": "Example text"}])

    def test_question_over_limit_is_rejected(self):
        question = "a" * 2001

        with self.assertRaises(ValueError):
            generate_answer(question, [{"text": "Example text"}])

    def test_empty_passages_return_fallback(self):
        answer = generate_answer("What is NexusAI?", [])

        self.assertIn(
            "couldn't find relevant information",
            answer,
        )

    def test_blank_passages_return_fallback(self):
        answer = generate_answer(
            "What is NexusAI?",
            [{"text": "   "}],
        )

        self.assertIn("couldn't find usable text", answer)

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "GROQ_API_KEY"):
            generate_answer(
                "What is NexusAI?",
                [{"text": "NexusAI is a knowledge assistant."}],
            )

    @patch("core.llm.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_valid_source_citation_is_preserved(self, mock_groq):
        mock_groq.return_value.chat.completions.create.return_value = (
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                "NexusAI is a knowledge assistant "
                                "[Source 1]."
                            )
                        ),
                        finish_reason="stop",
                    )
                ]
            )
        )

        answer = generate_answer(
            "What is NexusAI?",
            [{"text": "NexusAI is a knowledge assistant."}],
        )

        self.assertIn("[Source 1]", answer)
        mock_groq.return_value.chat.completions.create.assert_called_once()

    @patch("core.llm.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_unknown_source_citation_is_flagged(self, mock_groq):
        mock_groq.return_value.chat.completions.create.return_value = (
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                "The answer is confirmed [Source 7]."
                            )
                        ),
                        finish_reason="stop",
                    )
                ]
            )
        )

        answer = generate_answer(
            "What is confirmed?",
            [{"text": "Only one source is available."}],
        )

        self.assertIn(
            "[Unverified source citation omitted]",
            answer,
        )
        self.assertNotIn("[Source 7]", answer)
        mock_groq.return_value.chat.completions.create.assert_called_once()

    @patch("core.llm.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_valid_and_invalid_citations_are_checked_individually(
        self, mock_groq
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                "Supported claim [Source 1]. "
                                "Unsupported claim [Source 7]."
                            )
                        ),
                        finish_reason="stop",
                    )
                ]
            )
        )

        answer = generate_answer(
            "What is NexusAI?",
            [{"text": "NexusAI is a knowledge assistant."}],
        )

        self.assertIn("[Source 1]", answer)
        self.assertIn(
            "[Unverified source citation omitted]",
            answer,
        )
        self.assertNotIn("[Source 7]", answer)

    @patch("core.llm.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_plain_source_text_without_citation_is_unchanged(
        self, mock_groq
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="The phrase Source 7 appears here."
                        )
                    )
                ]
            )
        )

        answer = generate_answer(
            "What is NexusAI?",
            [{"text": "NexusAI is a knowledge assistant."}],
        )

        self.assertEqual(
            answer,
            "The phrase Source 7 appears here.",
        )
