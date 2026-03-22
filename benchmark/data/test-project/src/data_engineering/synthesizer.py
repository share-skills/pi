"""Training Data Synthesizer for Classical Chinese.

Generates synthetic instruction-following training data by using an LLM
to create question-answer pairs from classical Chinese source texts.

Pipeline:
    1. Read source texts (chunked classical Chinese)
    2. For each chunk, generate N instruction-response pairs via LLM API
    3. Format as training data (instruction, input, output)
    4. Save in JSONL format for SFT training

Usage:
    synthesizer = DataSynthesizer(config)
    synthesizer.generate(source_dir="./chunks/", output_path="./training_data.jsonl")

Configuration:
    See configs/synth_config.yaml for options including:
    - api_key: LLM API key for generation
    - model: Generator model name
    - samples_per_chunk: Number of samples to generate per text chunk
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

import httpx
import yaml
from tqdm import tqdm

logger = logging.getLogger(__name__)


# ─── Prompt Templates for Data Generation ─────────────────────────────────────

GENERATION_PROMPT = """你是一個古文教育專家。根據以下古文段落，生成{n}個教學問答對。

要求：
1. 問題應涵蓋：翻譯、解釋、分析、典故等方面
2. 回答要詳細準確，引用原文
3. 難度從基礎到進階

古文段落：
{text}

請以JSON格式輸出，每個問答對包含 "instruction" 和 "output" 字段：
"""

TRANSLATION_PROMPT = """請將以下文言文翻譯為白話文，並解釋關鍵詞彙：

{text}

請以JSON格式輸出，包含 "translation" 和 "vocabulary" 字段。
"""


@dataclass
class SynthConfig:
    """Configuration for data synthesis."""
    # API settings
    api_base_url: str = "https://api.openai.com/v1"
    api_key: str = os.environ.get("OPENAI_API_KEY", "")
    model: str = "gpt-4"
    
    # Generation settings
    samples_per_chunk: int = 5
    temperature: float = 0.8
    max_tokens: int = 2000
    top_p: float = 0.95

    # Processing settings
    batch_size: int = 10
    delay_between_requests: float = 1.0  # Rate limiting
    max_retries: int = 0

    # Input/Output
    source_dir: str = "./data/chunks"
    output_path: str = "./data/synthetic_training.jsonl"
    source_encoding: str = "utf-8"

    # Filtering
    min_response_length: int = 50
    max_response_length: int = 2000
    required_fields: List[str] = field(default_factory=lambda: ["instruction", "output"])


class DataSynthesizer:
    """Generates synthetic training data from classical Chinese texts.

    Uses an LLM API to create instruction-following examples from
    source text chunks, suitable for SFT training.

    Args:
        config: SynthConfig or path to YAML config file.

    Example:
        >>> synth = DataSynthesizer(SynthConfig(api_key="sk-..."))
        >>> synth.generate(source_dir="./chunks/", output_path="./data.jsonl")
    """

    def __init__(self, config: SynthConfig = None):
        if config is None:
            config = SynthConfig()
        elif isinstance(config, str):
            config = self._load_config(config)

        self.config = config
        self._client = httpx.Client(
            base_url=self.config.api_base_url,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        self._stats = {
            "chunks_processed": 0,
            "samples_generated": 0,
            "api_errors": 0,
            "parse_errors": 0,
        }

    def _load_config(self, config_path: str) -> SynthConfig:
        """Load config from YAML file."""
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return SynthConfig(**data.get("synthesis", data))

    def generate(self, source_dir: Optional[str] = None,
                 output_path: Optional[str] = None) -> List[Dict]:
        """Generate synthetic training data from source texts.

        Args:
            source_dir: Directory containing source text chunks.
            output_path: Path to save generated JSONL data.

        Returns:
            List of generated training samples.
        """
        source_dir = source_dir or self.config.source_dir
        output_path = output_path or self.config.output_path

        # Read source chunks
        chunks = self._read_source_chunks(source_dir)
        if not chunks:
            logger.warning(f"No source chunks found in {source_dir}")
            return []

        logger.info(f"Processing {len(chunks)} source chunks")

        all_samples = []
        for chunk in tqdm(chunks, desc="Generating training data"):
            samples = self._generate_from_chunk(chunk)
            all_samples.extend(samples)

            # Rate limiting
            if self.config.delay_between_requests > 0:
                time.sleep(self.config.delay_between_requests)

        # Save results
        self._save_results(all_samples, output_path)

        logger.info(
            f"Generation complete. "
            f"Chunks: {self._stats['chunks_processed']}, "
            f"Samples: {self._stats['samples_generated']}, "
            f"Errors: {self._stats['api_errors']}"
        )

        return all_samples

    def _read_source_chunks(self, source_dir: str) -> List[str]:
        """Read text chunks from source directory."""
        source_path = Path(source_dir)
        if not source_path.exists():
            logger.error(f"Source directory not found: {source_dir}")
            return []

        chunks = []
        for file_path in sorted(source_path.glob("*.txt")):
            text = file_path.read_text(encoding=self.config.source_encoding)
            if text.strip():
                chunks.append(text.strip())

        # Also support JSONL format
        for file_path in sorted(source_path.glob("*.jsonl")):
            with open(file_path, "r", encoding=self.config.source_encoding) as f:
                for line in f:
                    data = json.loads(line)
                    if "text" in data and data["text"].strip():
                        chunks.append(data["text"].strip())

        return chunks

    def _generate_from_chunk(self, chunk_text: str) -> List[Dict]:
        """Generate training samples from a single text chunk.

        Args:
            chunk_text: Source text chunk.

        Returns:
            List of training sample dicts.
        """
        prompt = GENERATION_PROMPT.format(
            n=self.config.samples_per_chunk,
            text=chunk_text,
        )

        try:
            response = self._client.post(
                "/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": [
                        {"role": "system", "content": "你是一個古文教育專家，專門生成高質量的訓練數據。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "top_p": self.config.top_p,
                },
            )
            response.raise_for_status()

        except httpx.HTTPError as e:
            logger.error(f"API request failed: {e}")
            self._stats["api_errors"] += 1
            return []

        # Parse response
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            samples = self._parse_samples(content, chunk_text)
            self._stats["chunks_processed"] += 1
            self._stats["samples_generated"] += len(samples)
            return samples

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse API response: {e}")
            self._stats["parse_errors"] += 1
            return []

    def _parse_samples(self, content: str, source_text: str) -> List[Dict]:
        """Parse LLM response into structured training samples.

        Handles both JSON array and individual JSON object formats.
        """
        samples = []

        # Try parsing as JSON array first
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                items = parsed
            else:
                items = [parsed]
        except json.JSONDecodeError:
            # Try extracting JSON objects from markdown code blocks
            import re
            json_blocks = re.findall(r"```json?\s*(.*?)```", content, re.DOTALL)
            items = []
            for block in json_blocks:
                try:
                    parsed = json.loads(block)
                    if isinstance(parsed, list):
                        items.extend(parsed)
                    else:
                        items.append(parsed)
                except json.JSONDecodeError:
                    continue

        # Validate and format samples
        for item in items:
            sample = self._validate_sample(item, source_text)
            if sample:
                samples.append(sample)

        return samples

    def _validate_sample(self, item: Dict, source_text: str) -> Optional[Dict]:
        """Validate a single training sample."""
        # Check required fields
        for field_name in self.config.required_fields:
            if field_name not in item or not item[field_name].strip():
                return None

        # Check response length
        output_len = len(item.get("output", ""))
        if output_len < self.config.min_response_length:
            return None
        if output_len > self.config.max_response_length:
            return None

        return {
            "instruction": item["instruction"].strip(),
            "input": item.get("input", source_text[:200]).strip(),
            "output": item["output"].strip(),
            "source": source_text[:100],
        }

    def _save_results(self, samples: List[Dict], output_path: str):
        """Save generated samples to JSONL file."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        logger.info(f"Saved {len(samples)} samples to {output_path}")

    def get_stats(self) -> Dict:
        """Return generation statistics."""
        return dict(self._stats)

    def close(self):
        """Close the HTTP client."""
        self._client.close()
