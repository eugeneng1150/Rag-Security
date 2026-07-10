#!/usr/bin/env python3
"""Run all three phases and produce summary."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_phase1 import run_phase1
from run_phase2 import run_phase2
from run_phase3 import run_phase3
from analysis.summarize import summarize

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RAG SECURITY EXPERIMENT — FULL RUN")
    print("=" * 70)

    print("\n>>> Starting Phase 1...")
    run_phase1()

    print("\n>>> Starting Phase 2...")
    run_phase2()

    print("\n>>> Starting Phase 3...")
    run_phase3()

    print("\n>>> Generating Summary...")
    summarize()
