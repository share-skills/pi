"""Verification script to demonstrate synthesizer silent failure issues."""

import os
import sys
from pathlib import Path
import tempfile
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_engineering.synthesizer import DataSynthesizer, SynthConfig


def test_issue1_empty_api_key_from_config():
    """Issue 1: Empty API key in config overrides environment variable."""
    print("\n=== Issue 1: Empty API Key from Config ===")
    
    # Set environment variable
    os.environ["OPENAI_API_KEY"] = "sk-env-key-12345"
    
    # Create a temp config file with empty api_key
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
synthesis:
  api_base_url: https://api.openai.com/v1
  api_key: ""
  model: gpt-4
  samples_per_chunk: 5
""")
        config_path = f.name
    
    try:
        synth = DataSynthesizer(config_path)
        print(f"  Config api_key: '{synth.config.api_key}'")
        print(f"  Environment OPENAI_API_KEY: '{os.environ.get('OPENAI_API_KEY')}'")
        
        if synth.config.api_key == "":
            print("  BUG CONFIRMED: Empty config value overrides environment variable!")
        else:
            print("  OK: Environment variable is used")
    finally:
        os.unlink(config_path)
        del os.environ["OPENAI_API_KEY"]


def test_issue2_silent_api_failure():
    """Issue 2: API errors are silently swallowed."""
    print("\n=== Issue 2: Silent API Failure ===")
    
    import httpx
    from unittest.mock import MagicMock, patch
    
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        # Write a source chunk
        (tmp_path / "chunk_001.txt").write_text(
            "子曰：學而時習之，不亦說乎？", 
            encoding="utf-8"
        )
        
        config = SynthConfig(
            api_key="sk-invalid-key",
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
        
        print(f"  Result: {result}")
        print(f"  Stats: {synth.get_stats()}")
        
        if result == [] and synth.get_stats()["api_errors"] > 0:
            print("  BUG CONFIRMED: API error silently swallowed, no exception raised!")
            print("  Output file exists:", (tmp_path / "output.jsonl").exists())
            print("  Output file size:", (tmp_path / "output.jsonl").stat().st_size if (tmp_path / "output.jsonl").exists() else 0)


def test_issue3_silent_parse_failure():
    """Issue 3: Parse errors are silently swallowed."""
    print("\n=== Issue 3: Silent Parse Failure ===")
    
    from unittest.mock import MagicMock, patch
    
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        (tmp_path / "chunk.txt").write_text("天下為公", encoding="utf-8")
        
        config = SynthConfig(
            api_key="sk-valid-key",
            source_dir=str(tmp_path),
            output_path=str(tmp_path / "output.jsonl"),
        )
        
        synth = DataSynthesizer(config)
        
        # Simulate malformed JSON response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is not valid JSON at all!"}}]
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(synth._client, "post", return_value=mock_response):
            result = synth.generate()
        
        print(f"  Result: {result}")
        print(f"  Stats: {synth.get_stats()}")
        
        if result == [] and synth.get_stats()["parse_errors"] > 0:
            print("  BUG CONFIRMED: Parse error silently swallowed!")


def test_issue4_over_aggressive_validation():
    """Issue 4: Over-aggressive validation filters out valid samples."""
    print("\n=== Issue 4: Over-Aggressive Validation ===")
    
    synth = DataSynthesizer(SynthConfig(min_response_length=50))
    
    # Valid short response (common in Chinese Q&A)
    short_item = {
        "instruction": "翻譯：學而時習之",
        "output": "學習並且按時複習。"  # Only 9 characters - valid but filtered
    }
    
    result = synth._validate_sample(short_item, "source text")
    print(f"  Short response (9 chars): {result}")
    
    # Longer response that passes
    long_item = {
        "instruction": "翻譯：學而時習之",
        "output": "這是一個足夠長的回答，讓我們解釋這個句子的含義和背景。" * 3  # 75+ chars
    }
    result2 = synth._validate_sample(long_item, "source text")
    print(f"  Long response (75+ chars): {'PASS' if result2 else 'FAIL'}")
    
    if result is None:
        print("  BUG CONFIRMED: Valid short responses are filtered out!")


def test_issue6_resource_leak():
    """Issue 6: HTTP client never closed automatically."""
    print("\n=== Issue 6: Resource Leak ===")
    
    synth = DataSynthesizer(SynthConfig())
    
    # Check if client has close method
    has_close = hasattr(synth._client, 'close')
    print(f"  HTTP client has close(): {has_close}")
    print(f"  close() called automatically: NO (must call manually)")
    print("  POTENTIAL ISSUE: Resources may leak if close() not called")


def main():
    print("=" * 60)
    print("SYNTHESIZER SILENT FAILURE VERIFICATION")
    print("=" * 60)
    
    test_issue1_empty_api_key_from_config()
    test_issue2_silent_api_failure()
    test_issue3_silent_parse_failure()
    test_issue4_over_aggressive_validation()
    test_issue6_resource_leak()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
