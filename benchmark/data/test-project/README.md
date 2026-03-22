# Guwen-LLM: Classical Chinese Text Processing & LLM Pipeline

A production pipeline for processing classical Chinese texts (古文), training large language models, and serving them via RAG-augmented inference.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  OCR Ingest │───▶│ Text Cleaning│───▶│  Chunking   │
└─────────────┘    └──────────────┘    └──────┬──────┘
                                              │
                   ┌──────────────┐    ┌──────▼──────┐
                   │  Synthesizer │───▶│  Quality    │
                   │  (Data Aug)  │    │  Filtering  │
                   └──────────────┘    └──────┬──────┘
                                              │
                   ┌──────────────┐    ┌──────▼──────┐
                   │  Evaluation  │◀───│  Training   │
                   └──────────────┘    └─────────────┘
                                              │
                   ┌──────────────┐    ┌──────▼──────┐
                   │  RAG Search  │◀───│  Inference  │
                   │  (Milvus)    │    │  API Server │
                   └──────────────┘    └─────────────┘
```

## Modules

- **src/data_processing/** — OCR ingestion, text cleaning, and chunking
- **src/data_engineering/** — Training data synthesis and quality filtering
- **src/training/** — SFT and GRPO training with evaluation
- **src/retrieval/** — Milvus-based RAG pipeline
- **src/inference/** — FastAPI server with OpenAI-compatible API

## Quick Start

```bash
pip install -r requirements.txt

# Process scanned texts
python -m src.data_processing.ocr_pipeline --input ./scans/ --output ./texts/

# Build training data
python -m src.data_engineering.synthesizer --config configs/synth_config.yaml

# Train model
python -m src.training.trainer --config configs/training_config.yaml

# Start inference server
python -m src.inference.api_server --config configs/inference_config.yaml
```

## Configuration

All config files are in `configs/`. See each module's docstring for detailed options.

## Requirements

- Python 3.10+
- CUDA 11.8+ (for GPU training/inference)
- Milvus 2.3+ (for RAG pipeline)
- PaddleOCR (for OCR ingestion)
