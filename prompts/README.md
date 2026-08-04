# Prompt Documentation

Each LLM role has its own Markdown file:

- `orchestrator.md` — Phase 0 restricted and Phase 1 unrestricted orchestrators
- `sql_agent.md` — Phase 0 restricted and Phase 1 unrestricted SQL agents
- `query_router.md` — Phase 2 query router
- `claim_extractor.md` — Phase 2 optional LLM claim extractor
- `claim_auditor.md` — Phase 2 claim auditor
- `response_synthesizer.md` — Phase 2 response synthesizer
- `action_planner.md` — Phase 2 action planner
- `experiment_report.md` — optional results-analysis prompt

These files document the prompts. Runtime definitions remain beside their Python implementations, so this folder does not change experiment behavior.

The notification agent, claim gate, action gate, and notification executor are deterministic and have no LLM prompts. Attack payloads remain in `attacks/payloads.py` and `attacks/adaptive.py`.
