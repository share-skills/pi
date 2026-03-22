"""Index corpus chunks into Milvus for RAG retrieval.

Reads chunked JSONL files and indexes them into the Milvus vector database.

Usage:
    python scripts/index_corpus.py --chunks ./data/chunks --config configs/rag_config.yaml
"""

import sys
import json
import logging
from pathlib import Path

import click
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.rag_pipeline import RAGPipeline, RAGConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("index_corpus")


@click.command()
@click.option("--chunks", "-c", required=True, help="Directory with .jsonl chunk files")
@click.option("--config", default="configs/rag_config.yaml", help="RAG config YAML")
@click.option("--recreate", is_flag=True, help="Delete and recreate collection")
def main(chunks, config, recreate):
    """Index text chunks into Milvus for RAG retrieval."""
    # Load config
    with open(config, "r") as f:
        cfg_data = yaml.safe_load(f)
    rag_config = RAGConfig(**cfg_data.get("rag", cfg_data))

    # Initialize pipeline
    logger.info(f"Connecting to Milvus at {rag_config.milvus_host}:{rag_config.milvus_port}")
    rag = RAGPipeline(rag_config)

    if recreate:
        logger.info("Deleting existing collection...")
        rag.delete_collection()

    rag.create_collection()

    # Load chunks
    chunks_path = Path(chunks)
    all_chunks = []
    for jsonl_file in sorted(chunks_path.glob("*.jsonl")):
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunk = json.loads(line)
                    all_chunks.append({
                        "text": chunk["text"],
                        "source": chunk.get("source", str(jsonl_file)),
                        "chunk_index": chunk.get("index", 0),
                    })

    logger.info(f"Indexing {len(all_chunks)} chunks...")
    indexed = rag.index_chunks(all_chunks)
    logger.info(f"Indexed {indexed}/{len(all_chunks)} chunks")

    stats = rag.get_collection_stats()
    logger.info(f"Collection stats: {stats}")

    rag.close()


if __name__ == "__main__":
    main()
