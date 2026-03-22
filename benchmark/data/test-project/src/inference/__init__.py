"""Inference module for serving the classical Chinese LLM.

Provides a FastAPI-based API server with OpenAI-compatible endpoints
for chat completion and text generation.

Components:
    - api_server: Main FastAPI application with /v1/chat/completions endpoint
    - model_loader: vLLM model loading and management
    - prompt_builder: Template-based prompt construction for classical Chinese
"""

from .api_server import create_app
from .prompt_builder import PromptBuilder

__all__ = ["create_app", "PromptBuilder"]
