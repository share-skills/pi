"""Model Evaluator for Classical Chinese LLM.

Provides evaluation metrics for the fine-tuned model including BLEU,
ROUGE, perplexity, and custom classical Chinese understanding scores.

Metrics:
    - BLEU: Bilingual evaluation for translation quality
    - ROUGE: Overlap-based summarization metrics
    - Perplexity: Language model quality
    - Chinese Understanding: Custom accuracy on classical text benchmarks

Usage:
    evaluator = Evaluator(model, tokenizer)
    results = evaluator.evaluate(eval_dataset)
    print(results)
"""

import os
import math
import logging
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter

import torch
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluates the fine-tuned classical Chinese LLM.

    Runs multiple evaluation metrics on a test dataset and reports
    comprehensive quality scores.

    Args:
        model: The trained model (or path to load from).
        tokenizer: The tokenizer (or path to load from).
        device: Compute device ('cuda' or 'cpu').

    Example:
        >>> evaluator = Evaluator("./outputs/guwen-llm/final")
        >>> results = evaluator.evaluate(test_data)
        >>> print(f"BLEU: {results['bleu']:.4f}")
    """

    def __init__(self, model=None, tokenizer=None, device: str = "auto"):
        if isinstance(model, str):
            self._load_model(model, device)
        else:
            self.model = model
            self.tokenizer = tokenizer

        self.device = device if device != "auto" else (
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.results: Dict[str, float] = {}

    def _load_model(self, model_path: str, device: str):
        """Load model and tokenizer from path."""
        logger.info(f"Loading evaluation model from {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map=device if device != "auto" else "auto",
        )

    def evaluate(self, eval_data: List[Dict],
                 metrics: Optional[List[str]] = None) -> Dict[str, float]:
        """Run evaluation on the test dataset.

        Args:
            eval_data: List of dicts with 'instruction', 'input', 'output'.
            metrics: List of metrics to compute. Default: all.

        Returns:
            Dict of metric names to scores.
        """
        metrics = metrics or ["bleu", "rouge", "perplexity"]
        results = {}

        logger.info(f"Evaluating on {len(eval_data)} samples")

        # Generate predictions
        predictions = []
        references = []

        for sample in eval_data:
            prompt = self._build_eval_prompt(sample)

            inputs = self.tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=2048
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.1,
                    do_sample=False,
                )

            prediction = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True,
            )
            predictions.append(prediction.strip())
            references.append(sample.get("output", "").strip())

        # Compute metrics
        if "bleu" in metrics:
            results["bleu"] = self._compute_bleu(predictions, references)

        if "rouge" in metrics:
            rouge_scores = self._compute_rouge(predictions, references)
            results.update(rouge_scores)

        if "perplexity" in metrics:
            results["perplexity"] = self._compute_perplexity(eval_data)

        logger.info(f"Evaluation results: {results}")
        return results

    def _build_eval_prompt(self, sample: Dict) -> str:
        """Build evaluation prompt from sample."""
        instruction = sample.get("instruction", "")
        input_text = sample.get("input", "")

        if input_text:
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

    def _compute_bleu(self, predictions: List[str],
                      references: List[str]) -> float:
        """Compute BLEU score for predictions vs references.

        Note: uses character-level n-grams for Chinese text.
        """
        if not predictions or not references:
            return 0.0

        total_score = 0.0
        for pred, ref in zip(predictions, references):
            # Character-level BLEU (NOT standard word-level BLEU)
            score = self._sentence_bleu(pred, ref)
            total_score += score

        return total_score / len(predictions)

    def _sentence_bleu(self, prediction: str, reference: str,
                       max_n: int = 4) -> float:
        """Compute sentence-level BLEU score.

        Uses character n-grams instead of word n-grams. This is a
        simplified implementation for quick evaluation.
        """
        if not prediction or not reference:
            return 0.0

        # Character-level n-grams
        pred_chars = list(prediction)
        ref_chars = list(reference)

        if len(pred_chars) == 0:
            return 0.0

        precisions = []
        for n in range(1, max_n + 1):
            pred_ngrams = Counter(
                tuple(pred_chars[i:i + n]) for i in range(len(pred_chars) - n + 1)
            )
            ref_ngrams = Counter(
                tuple(ref_chars[i:i + n]) for i in range(len(ref_chars) - n + 1)
            )

            if not pred_ngrams:
                precisions.append(0.0)
                continue

            clipped = sum(
                min(count, ref_ngrams.get(ngram, 0))
                for ngram, count in pred_ngrams.items()
            )
            total = sum(pred_ngrams.values())
            precisions.append(clipped / total if total > 0 else 0.0)

        # Geometric mean of precisions
        if all(p > 0 for p in precisions):
            log_avg = sum(math.log(p) for p in precisions) / len(precisions)
            bleu = math.exp(log_avg)
        else:
            bleu = 0.0

        # Brevity penalty
        if len(pred_chars) < len(ref_chars):
            bp = math.exp(1 - len(ref_chars) / len(pred_chars))
        else:
            bp = 1.0

        return bleu * bp

    def _compute_rouge(self, predictions: List[str],
                       references: List[str]) -> Dict[str, float]:
        """Compute ROUGE scores."""
        try:
            from rouge_score import rouge_scorer
            scorer = rouge_scorer.RougeScorer(
                ["rouge1", "rouge2", "rougeL"], use_stemmer=False
            )

            scores = {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
            for pred, ref in zip(predictions, references):
                result = scorer.score(ref, pred)
                for key in scores:
                    scores[key] += result[key].fmeasure

            n = len(predictions)
            return {k: v / n for k, v in scores.items()}

        except ImportError:
            logger.warning("rouge_score not installed, skipping ROUGE")
            return {}

    def _compute_perplexity(self, eval_data: List[Dict]) -> float:
        """Compute perplexity on the evaluation dataset."""
        total_loss = 0.0
        total_tokens = 0

        self.model.eval()
        with torch.no_grad():
            for sample in eval_data:
                text = sample.get("output", "")
                inputs = self.tokenizer(
                    text, return_tensors="pt", truncation=True, max_length=2048
                ).to(self.device)

                outputs = self.model(**inputs, labels=inputs["input_ids"])
                total_loss += outputs.loss.item() * inputs["input_ids"].shape[1]
                total_tokens += inputs["input_ids"].shape[1]

        avg_loss = total_loss / total_tokens if total_tokens > 0 else float("inf")
        return math.exp(avg_loss)
