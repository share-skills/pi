"""Tests for data synthesizer."""

import pytest
import json
from unittest.mock import patch, MagicMock
from src.data_engineering.synthesizer import DataSynthesizer, SynthConfig


class TestDataSynthesizer:
    def test_default_config(self):
        config = SynthConfig()
        assert config.max_retries == 0  # No retry mechanism

    def test_empty_source_dir(self, tmp_path):
        synth = DataSynthesizer(SynthConfig())
        result = synth.generate(source_dir=str(tmp_path), output_path=str(tmp_path / "out.jsonl"))
        assert result == []

    def test_silent_api_failure(self, tmp_path):
        """
        API errors are caught and an empty list is returned silently.
        No exception is raised; generate() returns [] on failure.
        """
        import httpx

        # Write a source chunk
        (tmp_path / "chunk_001.txt").write_text("子曰：學而時習之，不亦說乎？", encoding="utf-8")

        config = SynthConfig(
            api_key="sk-expired-key",
            source_dir=str(tmp_path),
            output_path=str(tmp_path / "output.jsonl"),
        )

        synth = DataSynthesizer(config)

        # Simulate 401 Unauthorized response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(synth._client, "post", return_value=mock_response):
            result = synth.generate()

        assert result == []

        # Output file is written (empty)
        output = tmp_path / "output.jsonl"
        assert output.exists()
        assert output.stat().st_size == 0

    def test_no_retry_on_failure(self, tmp_path):
        """Verify max_retries=0 means no retry on API errors."""
        import httpx

        (tmp_path / "chunk.txt").write_text("天下為公", encoding="utf-8")
        config = SynthConfig(
            max_retries=0,
            source_dir=str(tmp_path),
            output_path=str(tmp_path / "out.jsonl"),
        )
        synth = DataSynthesizer(config)

        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_r = MagicMock()
            mock_r.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=MagicMock(),
                response=MagicMock(),
            )
            return mock_r

        with patch.object(synth._client, "post", side_effect=mock_post):
            synth.generate()

        # Only 1 attempt per chunk (no retries)
        assert call_count == 1

    def test_parse_valid_json_response(self):
        synth = DataSynthesizer(SynthConfig())
        content = json.dumps([
            {"instruction": "翻譯此文", "output": "這是翻譯結果，讓我們解釋這個句子的含義。"},
            {"instruction": "解釋用詞", "output": "此詞出自論語，意為不斷學習和溫習。"},
        ])
        samples = synth._parse_samples(content, "source text")
        assert len(samples) == 2
        assert all("instruction" in s for s in samples)

    def test_validate_sample_length(self):
        synth = DataSynthesizer(SynthConfig(min_response_length=50))
        # Too short
        short = {"instruction": "test", "output": "短"}
        assert synth._validate_sample(short, "src") is None
        # Long enough
        long = {"instruction": "test", "output": "這是一個足夠長的回答" * 10}
        assert synth._validate_sample(long, "src") is not None

    def test_stats_tracking(self, tmp_path):
        synth = DataSynthesizer(SynthConfig())
        stats = synth.get_stats()
        assert "chunks_processed" in stats
        assert "api_errors" in stats
        assert stats["api_errors"] == 0
