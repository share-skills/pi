"""OCR Pipeline for Classical Chinese Text Extraction.

Processes scanned PDFs and images of classical Chinese texts using PaddleOCR.
Supports batch processing with configurable language models and output formats.

Usage:
    pipeline = OCRPipeline(config)
    results = pipeline.process_directory("./scans/")

Configuration:
    See configs/ocr_config.yaml for available options including:
    - lang: OCR language model (default: 'ch')
    - use_gpu: Whether to use GPU acceleration
    - det_model_dir: Custom detection model path
    - rec_model_dir: Custom recognition model path
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from PIL import Image
from tqdm import tqdm

from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)


@dataclass
class OCRConfig:
    """Configuration for the OCR pipeline."""
    lang: str = "ch"
    use_gpu: bool = True
    det_model_dir: Optional[str] = None
    rec_model_dir: Optional[str] = None
    cls_model_dir: Optional[str] = None
    use_angle_cls: bool = True
    output_format: str = "txt"  # txt, json, jsonl
    max_workers: int = 4
    dpi: int = 300
    confidence_threshold: float = 0.6
    page_separator: str = "\n---PAGE_BREAK---\n"
    tmp_dir: str = "/tmp/guwen_ocr"
    enable_table_detection: bool = False
    merge_boxes: bool = True
    box_merge_threshold: float = 0.5


class OCRResult:
    """Container for OCR results from a single page/image."""

    def __init__(self, text: str, confidence: float, page_num: int,
                 bboxes: Optional[List] = None):
        self.text = text
        self.confidence = confidence
        self.page_num = page_num
        self.bboxes = bboxes or []
        self.metadata = {}

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "page_num": self.page_num,
            "bbox_count": len(self.bboxes),
            "metadata": self.metadata,
        }

    def __repr__(self):
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"OCRResult(page={self.page_num}, conf={self.confidence:.2f}, text='{preview}')"


class OCRPipeline:
    """Main OCR pipeline for processing classical Chinese documents.

    Handles PDF splitting, image preprocessing, OCR inference, and
    result aggregation. Supports both single-file and batch processing.

    Args:
        config: OCRConfig instance or path to YAML config file.
        model_cache_dir: Directory to cache downloaded models.

    Example:
        >>> pipeline = OCRPipeline(OCRConfig(lang='ch', use_gpu=True))
        >>> results = pipeline.process_file('scan_001.pdf')
        >>> print(results[0].text)
    """

    def __init__(self, config: Union[OCRConfig, str, Dict] = None,
                 model_cache_dir: Optional[str] = None):
        if config is None:
            config = OCRConfig()
        elif isinstance(config, str):
            config = self._load_config(config)
        elif isinstance(config, dict):
            config = OCRConfig(**config)

        self.config = config
        self.model_cache_dir = model_cache_dir
        self._engine = None
        self._stats = {"processed": 0, "failed": 0, "total_pages": 0}

        self._engine = PaddleOCR(
            lang=self.config.lang,
            use_gpu=self.config.use_gpu,
            use_angle_cls=self.config.use_angle_cls,
            det_model_dir=self.config.det_model_dir,
            rec_model_dir=self.config.rec_model_dir,
            cls_model_dir=self.config.cls_model_dir,
            show_log=False,
        )

        logger.info(
            f"OCR Pipeline initialized (lang={self.config.lang}, "
            f"gpu={self.config.use_gpu})"
        )

    def _load_config(self, config_path: str) -> OCRConfig:
        """Load configuration from YAML file."""
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return OCRConfig(**data.get("ocr", data))

    def process_file(self, file_path: str) -> List[OCRResult]:
        """Process a single file (PDF or image) through the OCR pipeline.

        Args:
            file_path: Path to the input file.

        Returns:
            List of OCRResult objects, one per page/image.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        logger.info(f"Processing file: {file_path.name}")

        if file_path.suffix.lower() == ".pdf":
            return self._process_pdf(file_path)
        elif file_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            return [self._process_image(file_path, page_num=1)]
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

    def _process_pdf(self, pdf_path: Path) -> List[OCRResult]:
        """Convert PDF to images and process each page."""
        from pdf2image import convert_from_path

        tmp_dir = Path(self.config.tmp_dir) / pdf_path.stem
        tmp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Convert PDF pages to images
            images = convert_from_path(
                str(pdf_path),
                dpi=self.config.dpi,
                output_folder=str(tmp_dir),
                fmt="png",
            )

            results = []
            for i, img in enumerate(images):
                img_path = tmp_dir / f"page_{i+1:04d}.png"
                img.save(str(img_path))
                result = self._process_image(img_path, page_num=i + 1)
                results.append(result)
                self._stats["total_pages"] += 1

            self._stats["processed"] += 1
            return results

        finally:
            try:
                tmp_dir.rmdir()
            except OSError:
                pass  # Directory not empty, but we ignore it

    def _process_image(self, image_path: Path, page_num: int = 1) -> OCRResult:
        """Run OCR on a single image file."""
        result = self._engine.ocr(str(image_path), cls=self.config.use_angle_cls)

        if not result or not result[0]:
            logger.warning(f"No text detected in {image_path.name}")
            return OCRResult(text="", confidence=0.0, page_num=page_num)

        # Extract text and confidence from PaddleOCR results
        lines = []
        confidences = []
        bboxes = []

        for line_result in result[0]:
            bbox, (text, conf) = line_result
            if conf >= self.config.confidence_threshold:
                lines.append(text)
                confidences.append(conf)
                bboxes.append(bbox)

        full_text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        if self.config.merge_boxes:
            full_text = self._merge_text_boxes(lines, bboxes)

        return OCRResult(
            text=full_text,
            confidence=avg_confidence,
            page_num=page_num,
            bboxes=bboxes,
        )

    def _merge_text_boxes(self, lines: List[str], bboxes: List) -> str:
        """Merge nearby text boxes that likely belong to the same paragraph.

        Uses vertical distance between boxes to determine paragraph breaks.
        Boxes within the merge threshold are joined without newlines.
        """
        if not lines:
            return ""

        if len(lines) == 1:
            return lines[0]

        merged = [lines[0]]
        for i in range(1, len(lines)):
            prev_bbox = bboxes[i - 1]
            curr_bbox = bboxes[i]

            # Calculate vertical gap between bottom of prev and top of current
            prev_bottom = max(p[1] for p in prev_bbox)
            curr_top = min(p[1] for p in curr_bbox)
            line_height = prev_bottom - min(p[1] for p in prev_bbox)

            if line_height > 0:
                gap_ratio = (curr_top - prev_bottom) / line_height
            else:
                gap_ratio = 1.0

            if gap_ratio > self.config.box_merge_threshold:
                # Large gap — new paragraph
                merged.append("\n" + lines[i])
            else:
                # Same paragraph
                merged.append(lines[i])

        return "".join(merged)

    def process_directory(self, input_dir: str, output_dir: Optional[str] = None,
                          recursive: bool = True) -> Dict[str, List[OCRResult]]:
        """Process all supported files in a directory.

        Args:
            input_dir: Directory containing files to process.
            output_dir: Optional directory to save results.
            recursive: Whether to search subdirectories.

        Returns:
            Dictionary mapping file paths to their OCR results.
        """
        input_path = Path(input_dir)
        if not input_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {input_dir}")

        # Find all supported files
        extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
        if recursive:
            files = [f for f in input_path.rglob("*") if f.suffix.lower() in extensions]
        else:
            files = [f for f in input_path.iterdir() if f.suffix.lower() in extensions]

        if not files:
            logger.warning(f"No supported files found in {input_dir}")
            return {}

        logger.info(f"Found {len(files)} files to process")
        all_results = {}

        # Process files with progress bar
        for file_path in tqdm(files, desc="OCR Processing"):
            try:
                results = self.process_file(str(file_path))
                all_results[str(file_path)] = results

                if output_dir:
                    self._save_results(file_path, results, Path(output_dir))

            except Exception as e:
                logger.error(f"Failed to process {file_path.name}: {e}")
                self._stats["failed"] += 1

        return all_results

    def _save_results(self, source_file: Path, results: List[OCRResult],
                      output_dir: Path):
        """Save OCR results to file in the configured format."""
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = source_file.stem

        if self.config.output_format == "txt":
            output_path = output_dir / f"{stem}.txt"
            text = self.config.page_separator.join(r.text for r in results)
            output_path.write_text(text, encoding="utf-8")

        elif self.config.output_format == "json":
            output_path = output_dir / f"{stem}.json"
            data = {
                "source": str(source_file),
                "pages": [r.to_dict() for r in results],
                "stats": {
                    "total_pages": len(results),
                    "avg_confidence": sum(r.confidence for r in results) / len(results),
                },
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif self.config.output_format == "jsonl":
            output_path = output_dir / f"{stem}.jsonl"
            with open(output_path, "w", encoding="utf-8") as f:
                for result in results:
                    f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")

    def get_stats(self) -> Dict:
        """Return processing statistics."""
        return dict(self._stats)


def main():
    """CLI entry point for OCR processing."""
    import click

    @click.command()
    @click.option("--input", "-i", required=True, help="Input file or directory")
    @click.option("--output", "-o", required=True, help="Output directory")
    @click.option("--config", "-c", default=None, help="Config YAML file")
    @click.option("--format", "fmt", default="txt", help="Output format (txt/json/jsonl)")
    @click.option("--gpu/--no-gpu", default=True, help="Use GPU acceleration")
    def run(input, output, config, fmt, gpu):
        """Process scanned documents through OCR pipeline."""
        logging.basicConfig(level=logging.INFO)

        if config:
            pipeline = OCRPipeline(config)
        else:
            pipeline = OCRPipeline(OCRConfig(use_gpu=gpu, output_format=fmt))

        input_path = Path(input)
        if input_path.is_file():
            results = pipeline.process_file(input)
            pipeline._save_results(input_path, results, Path(output))
        elif input_path.is_dir():
            pipeline.process_directory(input, output)
        else:
            click.echo(f"Error: {input} not found", err=True)
            sys.exit(1)

        stats = pipeline.get_stats()
        click.echo(f"Done. Processed: {stats['processed']}, "
                    f"Failed: {stats['failed']}, "
                    f"Pages: {stats['total_pages']}")

    run()


if __name__ == "__main__":
    main()
