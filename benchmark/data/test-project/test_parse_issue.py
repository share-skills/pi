"""Debug parse issue."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_engineering.synthesizer import DataSynthesizer, SynthConfig

synth = DataSynthesizer(SynthConfig())

# Test case 1: Completely invalid response
content1 = "This is not valid JSON at all!"
samples1 = synth._parse_samples(content1, "source text")
print(f"Test 1 - Invalid text: {len(samples1)} samples")

# Test case 2: Valid JSON but wrong structure
content2 = '{"wrong": "structure"}'
samples2 = synth._parse_samples(content2, "source text")
print(f"Test 2 - Wrong structure: {len(samples2)} samples")

# Test case 3: Missing required fields
content3 = '{"instruction": "test"}'  # missing output
samples3 = synth._parse_samples(content3, "source text")
print(f"Test 3 - Missing output field: {len(samples3)} samples")

# Test case 4: Valid structure
import json
content4 = json.dumps([
    {"instruction": "translate", "output": "This is a sufficiently long output that passes the minimum length requirement of fifty characters."}
])
samples4 = synth._parse_samples(content4, "source text")
print(f"Test 4 - Valid structure: {len(samples4)} samples")

# Check stats
print(f"\nStats: {synth.get_stats()}")
