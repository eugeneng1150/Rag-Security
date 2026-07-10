#!/usr/bin/env python3
"""Summarize results across all phases."""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_config
from core.logging_utils import load_results, compute_asr, compute_asr_by_category


def summarize():
    config = load_config()

    print("=" * 70)
    print("EXPERIMENT SUMMARY")
    print("=" * 70)

    all_phase_results = {}
    for phase in [1, 2, 3]:
        results = load_results(phase, config)
        if not results:
            continue
        all_phase_results[phase] = results

    if not all_phase_results:
        print("No results found.")
        return

    phase_names = {
        1: "Undefended Baseline",
        2: "Cordon-MAS Defense",
        3: "Adaptive Attacks",
    }

    print(f"\n{'Phase':<30} {'ASR':>10} {'Leaked':>10} {'Total':>10}")
    print("-" * 70)

    for phase, results in sorted(all_phase_results.items()):
        asr = compute_asr(results)
        leaked = sum(1 for r in results if r["ssn_exfiltrated"])
        name = phase_names.get(phase, f"Phase {phase}")
        print(f"Phase {phase}: {name:<24} {asr:>9.1%} {leaked:>10} {len(results):>10}")

    for phase, results in sorted(all_phase_results.items()):
        by_cat = compute_asr_by_category(results)
        name = phase_names.get(phase, f"Phase {phase}")
        print(f"\n--- Phase {phase}: {name} ---")
        print(f"  {'Category':<30} {'ASR':>10} {'Trials':>10}")
        for cat, asr in by_cat.items():
            cat_results = [r for r in results if r["attack_category"] == cat]
            print(f"  {cat:<30} {asr:>9.1%} {len(cat_results):>10}")

    if 1 in all_phase_results and 2 in all_phase_results:
        asr1 = compute_asr(all_phase_results[1])
        asr2 = compute_asr(all_phase_results[2])
        reduction = (asr1 - asr2) / asr1 * 100 if asr1 > 0 else 0
        print(f"\n--- Defense Effectiveness ---")
        print(f"  Phase 1 → Phase 2 ASR reduction: {reduction:.1f}%")

    if 2 in all_phase_results and 3 in all_phase_results:
        asr2 = compute_asr(all_phase_results[2])
        asr3 = compute_asr(all_phase_results[3])
        print(f"\n--- Adaptive Attack Effectiveness ---")
        print(f"  Phase 2 ASR: {asr2:.1%} → Phase 3 ASR: {asr3:.1%}")
        if asr3 > asr2:
            print(f"  Adaptive attacks increased penetration by {(asr3 - asr2):.1%}")

    summary_path = os.path.join(config.logging.abs_results_dir, "summary.json")
    summary = {}
    for phase, results in all_phase_results.items():
        summary[f"phase{phase}"] = {
            "overall_asr": compute_asr(results),
            "by_category": compute_asr_by_category(results),
            "total_trials": len(results),
            "total_leaked": sum(1 for r in results if r["ssn_exfiltrated"]),
        }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    summarize()
