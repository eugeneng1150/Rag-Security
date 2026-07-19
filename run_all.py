#!/usr/bin/env python3
"""Run all phases and produce summary."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import parse_model_arg
from run_phase0 import run_phase0
from run_phase1 import run_phase1
from run_phase2 import run_phase2
from run_phase3 import run_phase3
from analysis.summarize import summarize
from analysis.analyze_results import run_analysis

if __name__ == "__main__":
    model = parse_model_arg()

    print("\n" + "=" * 70)
    print(f"RAG SECURITY EXPERIMENT — FULL RUN (model: {model or 'default'})")
    print("=" * 70)

    print("\n>>> Starting Phase 0 (Access Control Validation)...")
    run_phase0(model_override=model)

    print("\n>>> Starting Phase 1...")
    run_phase1(model_override=model)

    print("\n>>> Starting Phase 2...")
    run_phase2(model_override=model)

    print("\n>>> Starting Phase 3...")
    run_phase3(model_override=model)

    print("\n>>> Generating Summary...")
    summarize()

    print("\n>>> Generating LLM Analysis...")
    run_analysis()
