#!/usr/bin/env python3
"""LLM-powered analysis of experiment results. Produces a concise narrative report."""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_config
from core.llm import get_llm, invoke_with_retry
from core.logging_utils import load_results, compute_asr, compute_asr_by_category
from langchain_core.messages import SystemMessage, HumanMessage

ANALYSIS_PROMPT = """You are a security researcher summarizing a prompt injection experiment on a multi-agent RAG system.

You will receive structured experiment results across up to 4 phases. Write a SHORT analysis report (max 400 words) with these sections:

## Key Findings
- 3-5 bullet points, most important takeaways

## Phase-by-Phase
- 1-2 sentences per phase, what happened and why

## Attack Category Effectiveness
- Which categories worked best/worst and a brief reason why

## Implications
- 2-3 sentences on what this means for RAG security

Be direct. No filler. Use specific numbers from the data."""


def compress_trial(trial):
    """Extract key facts from a trial JSON, dropping verbose agent traces."""
    summary = {
        "category": trial.get("attack_category", ""),
        "leaked": trial.get("data_exfiltrated", trial.get("ssn_exfiltrated", False)),
        "leaked_values_count": len(trial.get("leaked_values", trial.get("ssns_leaked", []))),
    }

    if "access_denied" in trial:
        summary["access_denied"] = trial["access_denied"]

    for entry in trial.get("agent_trace", []):
        if entry.get("agent") == "sql_agent" and "SQL:" in entry.get("content", ""):
            sql_line = entry["content"].split("\n")[0]
            summary["sql_executed"] = sql_line[:150]
            break

    if trial.get("data_exfiltrated") or trial.get("ssn_exfiltrated"):
        for entry in trial.get("agent_trace", []):
            if entry.get("agent") == "notification_agent":
                summary["email_sent"] = True
                break

    return summary


def build_analysis_input(config):
    """Build a concise data blob for the LLM from all phase results."""
    report = {}

    for phase in [0, 1, 2, 3]:
        results = load_results(phase, config)
        if not results:
            continue

        asr = compute_asr(results)
        by_cat = compute_asr_by_category(results)
        total = len(results)
        leaked = sum(1 for r in results if r.get("data_exfiltrated", r.get("ssn_exfiltrated", False)))

        phase_data = {
            "overall_asr": f"{asr:.1%}",
            "leaked": leaked,
            "total": total,
            "by_category": {cat: f"{v:.1%}" for cat, v in by_cat.items()},
        }

        if phase == 0:
            blocked = sum(1 for r in results if r.get("access_denied", False))
            phase_data["access_denied_count"] = blocked

        trials_summary = [compress_trial(r) for r in results]
        leaked_trials = [t for t in trials_summary if t["leaked"]]
        safe_trials_sample = [t for t in trials_summary if not t["leaked"]][:3]

        phase_data["leaked_trials"] = leaked_trials
        phase_data["safe_trials_sample"] = safe_trials_sample

        report[f"phase{phase}"] = phase_data

    return report


def run_analysis():
    config = load_config()
    data = build_analysis_input(config)

    if not data:
        print("No results found. Run the experiment first.")
        return

    llm = get_llm(config)
    messages = [
        SystemMessage(content=ANALYSIS_PROMPT),
        HumanMessage(content=json.dumps(data, indent=2)),
    ]

    print("Analyzing results with LLM...")
    response = invoke_with_retry(llm, messages)
    report = response.content

    report_path = os.path.join(config.logging.abs_results_dir, "analysis_report.md")
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n{'=' * 60}")
    print(report)
    print(f"{'=' * 60}")
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    run_analysis()
