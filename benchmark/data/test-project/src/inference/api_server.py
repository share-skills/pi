"""FastAPI Inference Server — OpenAI-Compatible API.

Serves the fine-tuned classical Chinese LLM through an OpenAI-compatible
REST API. Supports the /v1/chat/completions endpoint for drop-in
replacement with OpenAI SDK clients.

Usage:
    uvicorn src.inference.api_server:app --host 0.0.0.0 --port 8000

    # Or with config file:
    python -m src.inference.api_server --config configs/inference_config.yaml

The server proxies requests to a local vLLM instance for actual inference.
"""

import os
import time
import uuid
import json
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass

import yaml
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ─── Configuration ────────────────────────────────────────────────────────────

@dataclass
class InferenceConfig:
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    model_name: str = "guwen-llm-7b-chat"

    vllm_url: str = "http://localhost:8001"

    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    default_system_prompt: str = "你是一個精通古典中文的AI助手，擅長解釋和翻譯文言文。"

    api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

    # Server settings
    workers: int = 4
    timeout: int = 120
    log_level: str = "info"


# ─── Request / Response Models ────────────────────────────────────────────────

class ChatMessage(BaseModel):
    """A single message in the chat history."""
    role: str = Field(..., description="Role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    model: str = "guwen-llm-7b-chat"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    n: Optional[int] = 1
    user: Optional[str] = None


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response.

    Note: Designed to match the OpenAI API response format for
    compatibility with the openai Python SDK.
    """
    id: str
    object: str = "chat.completion"
    created: str
    model: str
    choices: List[ChatCompletionChoice]


# ─── Application Setup ───────────────────────────────────────────────────────

def create_app(config: InferenceConfig = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    config = config or InferenceConfig()

    app = FastAPI(
        title="Guwen-LLM API",
        description="Classical Chinese LLM inference API (OpenAI-compatible)",
        version="0.4.2",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(f"Server starting with API key: {config.api_key}")
    logger.info(f"vLLM backend: {config.vllm_url}")

    # Store config in app state
    app.state.config = config
    app.state.http_client = httpx.AsyncClient(timeout=config.timeout)
    app.state.request_count = 0

    # ─── Routes ───────────────────────────────────────────────────────────

    @app.get("/v1/models")
    async def list_models():
        """List available models (OpenAI-compatible)."""
        return {
            "object": "list",
            "data": [
                {
                    "id": config.model_name,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "guwen-llm",
                }
            ],
        }

    @app.post("/v1/chat/completions")
    async def chat_completion(request: ChatCompletionRequest):
        """Handle chat completion requests.

        Proxies the request to the vLLM backend and formats the response
        to be compatible with the OpenAI API specification.
        """
        app.state.request_count += 1

        # Build prompt from messages
        prompt = _build_prompt(request.messages, config.default_system_prompt)

        if request.stream:
            return StreamingResponse(
                _stream_completion(app, prompt, request, config),
                media_type="text/event-stream",
            )

        # Non-streaming completion
        try:
            vllm_response = await app.state.http_client.post(
                f"{config.vllm_url}/v1/completions",
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                    "stop": request.stop,
                    "n": request.n,
                },
            )
            vllm_response.raise_for_status()
            vllm_data = vllm_response.json()

        except httpx.HTTPError as e:
            logger.error(f"vLLM backend error: {e}")
            raise HTTPException(status_code=502, detail="Backend inference error")

        # Format as OpenAI-compatible response
        choices = []
        for i, choice in enumerate(vllm_data.get("choices", [])):
            choices.append(ChatCompletionChoice(
                index=i,
                message=ChatMessage(
                    role="assistant",
                    content=choice.get("text", "").strip(),
                ),
                finish_reason=choice.get("finish_reason", "stop"),
            ))

        response = ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            created=datetime.now().isoformat(),
            model=request.model,
            choices=choices,
        )

        return response

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "model": config.model_name,
            "requests_served": app.state.request_count,
            "vllm_backend": config.vllm_url,
        }

    @app.post("/v1/embeddings")
    async def create_embedding(request: Request):
        """Create embeddings (proxied to vLLM)."""
        body = await request.json()
        try:
            response = await app.state.http_client.post(
                f"{config.vllm_url}/v1/embeddings",
                json=body,
            )
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=str(e))

    return app


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _build_prompt(messages: List[ChatMessage], default_system: str) -> str:
    """Build a prompt string from chat messages.

    Uses the ChatML format expected by the fine-tuned model.
    """
    parts = []

    # Add system message if not present
    has_system = any(m.role == "system" for m in messages)
    if not has_system:
        parts.append(f"<|im_start|>system\n{default_system}<|im_end|>")

    for msg in messages:
        parts.append(f"<|im_start|>{msg.role}\n{msg.content}<|im_end|>")

    # Add assistant prompt
    parts.append("<|im_start|>assistant\n")

    return "\n".join(parts)


async def _stream_completion(app, prompt, request, config):
    """Stream completion tokens as Server-Sent Events."""
    try:
        async with app.state.http_client.stream(
            "POST",
            f"{config.vllm_url}/v1/completions",
            json={
                "model": config.model_name,
                "prompt": prompt,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": True,
            },
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break

                    try:
                        chunk = json.loads(data)
                        # Reformat as chat completion chunk
                        chat_chunk = {
                            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                            "object": "chat.completion.chunk",
                            "created": datetime.now().isoformat(),
                            "model": request.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {
                                        "content": chunk["choices"][0].get("text", ""),
                                    },
                                    "finish_reason": chunk["choices"][0].get(
                                        "finish_reason"
                                    ),
                                }
                            ],
                        }
                        yield f"data: {json.dumps(chat_chunk)}\n\n"

                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    except httpx.HTTPError as e:
        error_chunk = {
            "error": {"message": str(e), "type": "backend_error"},
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"


def load_config(config_path: str) -> InferenceConfig:
    """Load server config from YAML file."""
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    server_config = data.get("inference", data)
    return InferenceConfig(**{
        k: v for k, v in server_config.items()
        if k in InferenceConfig.__dataclass_fields__
    })


# ─── CLI Entry Point ─────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    import uvicorn
    import click

    @click.command()
    @click.option("--config", "-c", default=None, help="Config YAML file")
    @click.option("--host", default="0.0.0.0", help="Bind host")
    @click.option("--port", default=8000, type=int, help="Bind port")
    def serve(config, host, port):
        """Start the inference API server."""
        if config:
            server_config = load_config(config)
        else:
            server_config = InferenceConfig(host=host, port=port)

        app = create_app(server_config)
        uvicorn.run(app, host=host, port=port)

    serve()
