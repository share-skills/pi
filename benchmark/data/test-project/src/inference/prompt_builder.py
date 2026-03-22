"""Prompt Builder for Classical Chinese LLM.

Constructs prompts using templates optimized for classical Chinese
text understanding, translation, and analysis tasks.

Supports multiple prompt formats:
    - ChatML (for Qwen-based models)
    - Alpaca (for LLaMA-based models)
    - Plain (for vanilla completion)
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from string import Template

logger = logging.getLogger(__name__)


# ─── Prompt Templates ─────────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "default": "你是一個精通古典中文的AI助手，擅長解釋和翻譯文言文。",
    "translator": (
        "你是一位古文翻譯專家。請將用戶提供的文言文翻譯為現代白話文，"
        "保留原文的修辭風格和語氣。"
    ),
    "annotator": (
        "你是一位古典文學研究者。請為用戶提供的古文添加詳細注釋，"
        "解釋生僻字詞、典故和修辭手法。"
    ),
    "analyst": (
        "你是一位文學批評家，精通中國古典文學。請分析用戶提供的古文，"
        "從結構、主題、修辭等方面進行深入解讀。"
    ),
}

TASK_TEMPLATES = {
    "translate": "請將以下文言文翻譯為白話文：\n\n{text}",
    "annotate": "請為以下古文添加注釋：\n\n{text}",
    "analyze": "請分析以下古文的含義和修辭：\n\n{text}",
    "continue": "請以相同的文言文風格續寫：\n\n{text}",
    "simplify": "請用通俗易懂的方式解釋以下古文：\n\n{text}",
}


@dataclass
class PromptConfig:
    """Configuration for prompt building."""
    format: str = "chatml"  # chatml, alpaca, plain
    max_prompt_length: int = 4096
    system_prompt_key: str = "default"
    custom_system_prompt: Optional[str] = None
    include_context: bool = True
    context_prefix: str = "參考資料："
    max_context_chunks: int = 3


class PromptBuilder:
    """Builds structured prompts for the classical Chinese LLM.

    Handles different prompt formats and task-specific templates,
    with support for RAG context injection.

    Args:
        config: PromptConfig instance.

    Example:
        >>> builder = PromptBuilder()
        >>> prompt = builder.build(
        ...     task="translate",
        ...     text="學而時習之，不亦說乎？",
        ... )
    """

    def __init__(self, config: PromptConfig = None):
        self.config = config or PromptConfig()
        self._system_prompt = (
            self.config.custom_system_prompt
            or SYSTEM_PROMPTS.get(self.config.system_prompt_key, SYSTEM_PROMPTS["default"])
        )

    def build(self, task: str = "translate", text: str = "",
              context: Optional[List[str]] = None,
              history: Optional[List[Dict]] = None) -> str:
        """Build a prompt from task, text, and optional context.

        Args:
            task: Task type (translate, annotate, analyze, continue, simplify).
            text: Input text to process.
            context: Optional RAG context chunks.
            history: Optional conversation history.

        Returns:
            Formatted prompt string.
        """
        # Build the user message
        template = TASK_TEMPLATES.get(task, TASK_TEMPLATES["translate"])
        user_content = template.format(text=text)

        # Add RAG context if provided
        if context and self.config.include_context:
            context_str = self._format_context(context)
            user_content = f"{context_str}\n\n{user_content}"

        # Format according to prompt style
        if self.config.format == "chatml":
            return self._format_chatml(user_content, history)
        elif self.config.format == "alpaca":
            return self._format_alpaca(user_content)
        else:
            return self._format_plain(user_content)

    def _format_chatml(self, user_content: str,
                       history: Optional[List[Dict]] = None) -> str:
        """Format prompt in ChatML format."""
        parts = [f"<|im_start|>system\n{self._system_prompt}<|im_end|>"]

        if history:
            for msg in history:
                parts.append(
                    f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>"
                )

        parts.append(f"<|im_start|>user\n{user_content}<|im_end|>")
        parts.append("<|im_start|>assistant\n")

        prompt = "\n".join(parts)
        return self._truncate(prompt)

    def _format_alpaca(self, user_content: str) -> str:
        """Format prompt in Alpaca instruction format."""
        prompt = (
            f"### Instruction:\n{self._system_prompt}\n\n"
            f"### Input:\n{user_content}\n\n"
            f"### Response:\n"
        )
        return self._truncate(prompt)

    def _format_plain(self, user_content: str) -> str:
        """Format as plain text prompt."""
        prompt = f"{self._system_prompt}\n\n{user_content}\n\n回答："
        return self._truncate(prompt)

    def _format_context(self, context: List[str]) -> str:
        """Format RAG context chunks for inclusion in prompt."""
        chunks = context[: self.config.max_context_chunks]
        formatted = [f"[{i+1}] {chunk}" for i, chunk in enumerate(chunks)]
        return f"{self.config.context_prefix}\n" + "\n".join(formatted)

    def _truncate(self, prompt: str) -> str:
        """Truncate prompt to max length."""
        if len(prompt) > self.config.max_prompt_length:
            logger.warning(
                f"Prompt truncated from {len(prompt)} to "
                f"{self.config.max_prompt_length} characters"
            )
            return prompt[: self.config.max_prompt_length]
        return prompt

    def estimate_tokens(self, text: str) -> int:
        """Rough token count estimation for Chinese text.

        Uses a simple heuristic: ~1.5 tokens per Chinese character,
        ~0.25 tokens per ASCII character.
        """
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
