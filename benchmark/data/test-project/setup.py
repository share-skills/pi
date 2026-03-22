"""Setup configuration for Guwen-LLM package."""

from setuptools import setup, find_packages

setup(
    name="guwen-llm",
    version="0.4.2",
    description="Classical Chinese Text Processing & LLM Pipeline",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "torch>=2.1.0",
        "transformers>=4.36.0",
        "peft>=0.7.0",
        "trl>=0.7.0",
        "datasets>=2.16.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "httpx>=0.25.0",
        "pymilvus>=2.3.0",
        "sentence-transformers>=2.2.0",
        "paddleocr>=2.7.0",
        "pyyaml>=6.0.0",
        "click>=8.1.0",
        "loguru>=0.7.0",
        "tqdm>=4.66.0",
    ],
    entry_points={
        "console_scripts": [
            "guwen-ocr=src.data_processing.ocr_pipeline:main",
            "guwen-serve=src.inference.api_server:serve",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3.10",
    ],
)
