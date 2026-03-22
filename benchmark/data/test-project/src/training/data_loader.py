"""Training Data Loader for Classical Chinese SFT.

Handles loading, preprocessing, and formatting of training data
from JSONL files into tokenized datasets ready for SFT training.

Supports multiple data formats:
    - Instruction-following: {"instruction": ..., "input": ..., "output": ...}
    - ShareGPT: {"conversations": [{"from": "human", "value": ...}, ...]}
    - Raw text: {"text": ...}

Usage:
    loader = DataLoader(tokenizer, max_length=2048)
    dataset = loader.load("./data/training.jsonl")
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable, Union
from dataclasses import dataclass

import torch
from torch.utils.data import Dataset
from transformers import PreTrainedTokenizer
from tqdm import tqdm

logger = logging.getLogger(__name__)


ALPACA_TEMPLATE = (
    "Below is an instruction that describes a task. "
    "Write a response that appropriately completes the request.\n\n"
    "### Instruction:\n{instruction}\n\n"
    "### Input:\n{input}\n\n"
    "### Response:\n{output}"
)

CHATML_TEMPLATE = (
    "<|im_start|>system\n你是一個精通古典中文的AI助手。<|im_end|>\n"
    "<|im_start|>user\n{instruction}\n\n{input}<|im_end|>\n"
    "<|im_start|>assistant\n{output}<|im_end|>"
)

CHATML_NO_INPUT_TEMPLATE = (
    "<|im_start|>system\n你是一個精通古典中文的AI助手。<|im_end|>\n"
    "<|im_start|>user\n{instruction}<|im_end|>\n"
    "<|im_start|>assistant\n{output}<|im_end|>"
)


@dataclass
class DataConfig:
    """Data loading configuration."""
    format: str = "instruction"   # instruction, sharegpt, raw
    template: str = "chatml"      # chatml, alpaca
    max_length: int = 2048
    padding: str = "max_length"
    truncation: bool = True
    add_eos_token: bool = True
    label_mask_input: bool = True   # Mask input tokens in loss
    num_workers: int = 4


class InstructionDataset(Dataset):
    """PyTorch Dataset for instruction-following data.

    Tokenizes and caches instruction-response pairs for SFT training.
    Supports label masking to compute loss only on output tokens.

    Args:
        samples: List of sample dicts with instruction/output keys.
        tokenizer: HuggingFace tokenizer.
        config: DataConfig with formatting options.
    """

    def __init__(self, samples: List[Dict], tokenizer: PreTrainedTokenizer,
                 config: DataConfig = None):
        self.config = config or DataConfig()
        self.tokenizer = tokenizer
        self._data = []

        logger.info(f"Tokenizing {len(samples)} samples...")
        for sample in tqdm(samples, desc="Tokenizing"):
            encoded = self._encode_sample(sample)
            if encoded:
                self._data.append(encoded)

        logger.info(f"Dataset ready: {len(self._data)} samples")

    def _encode_sample(self, sample: Dict) -> Optional[Dict]:
        """Encode a single sample into tokenized tensors."""
        text = self._format_sample(sample)
        if not text:
            return None

        tokens = self.tokenizer(
            text,
            max_length=self.config.max_length,
            padding=self.config.padding,
            truncation=self.config.truncation,
            return_tensors="pt",
        )

        input_ids = tokens["input_ids"].squeeze(0)
        attention_mask = tokens["attention_mask"].squeeze(0)
        labels = input_ids.clone()

        # Mask input tokens from loss computation
        if self.config.label_mask_input:
            instruction = self._get_instruction_part(sample)
            instruction_tokens = self.tokenizer(
                instruction,
                return_tensors="pt",
                add_special_tokens=False,
            )
            n_mask = instruction_tokens["input_ids"].shape[1]
            labels[:n_mask] = -100

        # Mask padding tokens
        labels[attention_mask == 0] = -100

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }

    def _format_sample(self, sample: Dict) -> str:
        """Format a sample dict into a prompt string."""
        instruction = sample.get("instruction", "")
        input_text = sample.get("input", "")
        output = sample.get("output", "")

        if not instruction or not output:
            return ""

        if self.config.template == "chatml":
            if input_text.strip():
                return CHATML_TEMPLATE.format(
                    instruction=instruction,
                    input=input_text,
                    output=output,
                )
            else:
                return CHATML_NO_INPUT_TEMPLATE.format(
                    instruction=instruction,
                    output=output,
                )
        elif self.config.template == "alpaca":
            return ALPACA_TEMPLATE.format(
                instruction=instruction,
                input=input_text or "N/A",
                output=output,
            )
        else:
            return f"{instruction}\n\n{output}"

    def _get_instruction_part(self, sample: Dict) -> str:
        """Get only the instruction/input part (without output)."""
        instruction = sample.get("instruction", "")
        input_text = sample.get("input", "")

        if self.config.template == "chatml":
            if input_text.strip():
                return (
                    f"<|im_start|>system\n你是一個精通古典中文的AI助手。<|im_end|>\n"
                    f"<|im_start|>user\n{instruction}\n\n{input_text}<|im_end|>\n"
                    f"<|im_start|>assistant\n"
                )
            else:
                return (
                    f"<|im_start|>system\n你是一個精通古典中文的AI助手。<|im_end|>\n"
                    f"<|im_start|>user\n{instruction}<|im_end|>\n"
                    f"<|im_start|>assistant\n"
                )
        else:
            return f"{instruction}\n\n{input_text}\n\n"

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, idx: int) -> Dict:
        return self._data[idx]


class SFTDataLoader:
    """Data loader for SFT training.

    Handles reading, formatting, and splitting training data
    into train/eval splits.

    Args:
        tokenizer: HuggingFace tokenizer.
        config: DataConfig with loading options.

    Example:
        >>> loader = SFTDataLoader(tokenizer)
        >>> train_ds, eval_ds = loader.load("data/training.jsonl", eval_ratio=0.05)
    """

    def __init__(self, tokenizer: PreTrainedTokenizer, config: DataConfig = None):
        self.tokenizer = tokenizer
        self.config = config or DataConfig()

    def load(self, data_path: str, eval_ratio: float = 0.05
             ) -> tuple:
        """Load data and return train/eval datasets.

        Args:
            data_path: Path to JSONL file.
            eval_ratio: Fraction of data to use for evaluation.

        Returns:
            Tuple of (train_dataset, eval_dataset).
        """
        samples = self._read_jsonl(data_path)
        if not samples:
            raise ValueError(f"No samples loaded from {data_path}")

        # Shuffle and split
        import random
        random.shuffle(samples)

        split_idx = max(1, int(len(samples) * (1 - eval_ratio)))
        train_samples = samples[:split_idx]
        eval_samples = samples[split_idx:]

        logger.info(f"Train: {len(train_samples)}, Eval: {len(eval_samples)}")

        train_ds = InstructionDataset(train_samples, self.tokenizer, self.config)
        eval_ds = InstructionDataset(eval_samples, self.tokenizer, self.config)

        return train_ds, eval_ds

    def _read_jsonl(self, path: str) -> List[Dict]:
        """Read samples from a JSONL file."""
        samples = []
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                    samples.append(sample)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping line {line_num}: {e}")
        logger.info(f"Loaded {len(samples)} samples from {path}")
        return samples
