"""Model Loader for vLLM Backend.

Handles model initialization, quantization configuration, and
vLLM engine setup for serving the classical Chinese LLM.

This module manages the lifecycle of the vLLM inference engine,
including model downloading, GPU allocation, and health monitoring.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Model loading configuration."""
    model_path: str = "models/guwen-llm-7b-chat"
    tokenizer_path: Optional[str] = None
    dtype: str = "auto"  # auto, float16, bfloat16
    quantization: Optional[str] = None  # awq, gptq, None
    gpu_memory_utilization: float = 0.9
    max_model_len: int = 4096
    tensor_parallel_size: int = 1
    trust_remote_code: bool = True
    seed: int = 42


class ModelLoader:
    """Loads and manages the vLLM inference engine.

    Handles model initialization with proper GPU allocation,
    quantization settings, and engine configuration.

    Args:
        config: ModelConfig with model and GPU settings.

    Example:
        >>> loader = ModelLoader(ModelConfig(model_path="./models/guwen-7b"))
        >>> engine = loader.get_engine()
    """

    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self._engine = None
        self._tokenizer = None
        self._loaded = False

    def load(self) -> Any:
        """Load the model and create vLLM engine.

        Returns:
            vLLM LLMEngine instance.
        """
        if self._loaded:
            return self._engine

        logger.info(f"Loading model from {self.config.model_path}")
        logger.info(f"Config: dtype={self.config.dtype}, "
                     f"quant={self.config.quantization}, "
                     f"tp={self.config.tensor_parallel_size}")

        try:
            from vllm import LLM

            self._engine = LLM(
                model=self.config.model_path,
                tokenizer=self.config.tokenizer_path or self.config.model_path,
                dtype=self.config.dtype,
                quantization=self.config.quantization,
                gpu_memory_utilization=self.config.gpu_memory_utilization,
                max_model_len=self.config.max_model_len,
                tensor_parallel_size=self.config.tensor_parallel_size,
                trust_remote_code=self.config.trust_remote_code,
                seed=self.config.seed,
            )

            self._loaded = True
            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

        return self._engine

    def get_engine(self) -> Any:
        """Get the vLLM engine, loading if necessary."""
        if not self._loaded:
            self.load()
        return self._engine

    def get_model_info(self) -> Dict:
        """Return information about the loaded model."""
        return {
            "model_path": self.config.model_path,
            "loaded": self._loaded,
            "dtype": self.config.dtype,
            "quantization": self.config.quantization,
            "max_model_len": self.config.max_model_len,
            "tensor_parallel_size": self.config.tensor_parallel_size,
        }

    def unload(self):
        """Unload the model and free GPU memory."""
        if self._engine is not None:
            del self._engine
            self._engine = None
            self._loaded = False

            # Force GPU memory cleanup
            try:
                import torch
                torch.cuda.empty_cache()
            except ImportError:
                pass

            logger.info("Model unloaded")
