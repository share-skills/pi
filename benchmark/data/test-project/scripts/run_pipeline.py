"""End-to-end pipeline runner script.

Orchestrates the full pipeline from raw scans to a trained model:
    1. OCR processing
    2. Text cleaning and chunking
    3. Data synthesis and quality filtering
    4. Training

Usage:
    python scripts/run_pipeline.py --config configs/pipeline_config.yaml --stage all
    python scripts/run_pipeline.py --stage ocr --input ./scans --output ./texts
    python scripts/run_pipeline.py --stage train --config configs/training_config.yaml
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import click
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
from src.data_processing.text_cleaner import TextCleaner, CleanerConfig
from src.data_processing.chunk_builder import ChunkBuilder, ChunkConfig
from src.data_engineering.synthesizer import DataSynthesizer, SynthConfig
from src.data_engineering.quality_filter import QualityFilter, FilterConfig
from src.training.trainer import Trainer, TrainingConfig
from src.training.config_builder import ConfigBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")


def run_ocr_stage(input_dir: str, output_dir: str, config: dict):
    """Run OCR processing on scanned documents."""
    logger.info("=== Stage 1: OCR Processing ===")
    ocr_config = OCRConfig(**config.get("ocr", {}))
    pipeline = OCRPipeline(ocr_config)
    results = pipeline.process_directory(input_dir, output_dir)
    stats = pipeline.get_stats()
    logger.info(f"OCR complete: {stats}")
    return results


def run_cleaning_stage(input_dir: str, output_dir: str, config: dict):
    """Run text cleaning on OCR output."""
    logger.info("=== Stage 2: Text Cleaning ===")
    cleaner_config = CleanerConfig(**config.get("cleaner", {}))
    cleaner = TextCleaner(cleaner_config)

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cleaned_files = 0
    for txt_file in input_path.glob("*.txt"):
        text = txt_file.read_text(encoding="utf-8")
        cleaned = cleaner.clean(text)
        (output_path / txt_file.name).write_text(cleaned, encoding="utf-8")
        cleaned_files += 1

    logger.info(f"Cleaned {cleaned_files} files. Stats: {cleaner.get_stats()}")


def run_chunking_stage(input_dir: str, output_dir: str, config: dict):
    """Run text chunking on cleaned texts."""
    logger.info("=== Stage 3: Chunking ===")
    chunk_config = ChunkConfig(**config.get("chunking", {}))
    builder = ChunkBuilder(chunk_config)

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    import json
    total_chunks = 0
    for txt_file in input_path.glob("*.txt"):
        text = txt_file.read_text(encoding="utf-8")
        chunks = builder.build_chunks(text, source=str(txt_file))

        output_file = output_path / f"{txt_file.stem}.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")

        total_chunks += len(chunks)

    logger.info(f"Created {total_chunks} chunks. Stats: {builder.get_stats()}")


def run_synthesis_stage(source_dir: str, output_path: str, config: dict):
    """Run training data synthesis."""
    logger.info("=== Stage 4: Data Synthesis ===")
    synth_config = SynthConfig(**config.get("synthesis", {}))
    synth = DataSynthesizer(synth_config)
    samples = synth.generate(source_dir=source_dir, output_path=output_path)
    logger.info(f"Generated {len(samples)} samples. Stats: {synth.get_stats()}")
    return samples


def run_filtering_stage(input_path: str, output_path: str, config: dict):
    """Run quality filtering on synthetic data."""
    logger.info("=== Stage 5: Quality Filtering ===")
    import json

    filter_config = FilterConfig(**config.get("filtering", {}))
    qf = QualityFilter(filter_config)

    samples = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    filtered = qf.filter(samples)

    with open(output_path, "w", encoding="utf-8") as f:
        for sample in filtered:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    stats = qf.get_stats()
    logger.info(f"Filtered: {stats['passed']}/{stats['total_input']} kept")


def run_training_stage(config: dict):
    """Run model fine-tuning."""
    logger.info("=== Stage 6: Training ===")
    training_config = TrainingConfig(**config.get("training", {}))
    trainer = Trainer(training_config)
    trainer.train()


@click.command()
@click.option("--config", "-c", default=None, help="Pipeline config YAML")
@click.option("--stage", "-s", default="all",
              type=click.Choice(["all", "ocr", "clean", "chunk", "synth", "filter", "train"]),
              help="Which stage to run")
@click.option("--input", "-i", "input_dir", default="./data/raw", help="Input directory")
@click.option("--output", "-o", "output_dir", default="./data", help="Output base directory")
def main(config, stage, input_dir, output_dir):
    """Run the Guwen-LLM data processing and training pipeline."""
    pipeline_config = {}
    if config:
        with open(config, "r") as f:
            pipeline_config = yaml.safe_load(f)

    output_path = Path(output_dir)

    if stage in ("all", "ocr"):
        run_ocr_stage(input_dir, str(output_path / "texts"), pipeline_config)

    if stage in ("all", "clean"):
        run_cleaning_stage(
            str(output_path / "texts"),
            str(output_path / "cleaned"),
            pipeline_config,
        )

    if stage in ("all", "chunk"):
        run_chunking_stage(
            str(output_path / "cleaned"),
            str(output_path / "chunks"),
            pipeline_config,
        )

    if stage in ("all", "synth"):
        run_synthesis_stage(
            str(output_path / "chunks"),
            str(output_path / "synthetic_raw.jsonl"),
            pipeline_config,
        )

    if stage in ("all", "filter"):
        run_filtering_stage(
            str(output_path / "synthetic_raw.jsonl"),
            str(output_path / "training.jsonl"),
            pipeline_config,
        )

    if stage in ("all", "train"):
        run_training_stage(pipeline_config)

    logger.info("Pipeline complete!")


if __name__ == "__main__":
    main()
