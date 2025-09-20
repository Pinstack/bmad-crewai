# BMAD CrewAI – Classification-Focused Audit (Narrative)

Purpose
- Provide a clear, single approach to reduce false positives/negatives, ambiguity, and OOD fragility across BMAD’s rule-driven checks while staying English-first and strict.

One Approach: Deterministic Backbone + Small LLM Assist (Hard Cases Only)
- Deterministic backbone (authoritative):
  - Canonical paths: enforce `docs/prd.md` and `docs/architecture.md` for tools/CI and links.
  - Gate policy/scoring: keep thresholds and critical-section weighting deterministic.
  - Mechanics: retry/backoff, time windows, index validation, file/link resolution.
- Small LLM assist (narrow scope):
  - Trigger only when rules are uncertain: artefact type “unknown/mixed”, acceptance measurability unclear, test type not detected, or decisions near margins (≤ 0.1).
  - Strict JSON output; confidence gate (accept ≥ 0.7), 1–2s timeout, checksum cache; fall back to rules on low confidence or timeout.
  - Config-gated; safe by default (assist on-hard-cases only, no auto-PASS).

BMAD Doc Naming Changes (Stable Paths, Smart Discovery)
- Always resolve to canonical paths for reproducibility: keep links, build targets, and gate inputs on `docs/prd.md` and `docs/architecture.md`.
- Maintain a small alias map (e.g., `docs/brownfield-prd.md → docs/prd.md`) for link checks and artefact writing to avoid breakage during transitions.
- If a canonical file is missing or multiple candidates exist, run LLM discovery on `docs/*.md` to identify the best PRD/Architecture by content, then propose a one-time deterministic migration (rename + link updates).
- With LLM assist enabled, do not expand synonym lists; keep only a minimal fallback for offline/timeout cases.

Risk → Mitigation (concise)
- Artefact misclassification: rules first; on “unknown/mixed” call LLM; enforce canonical path via alias/migration.
- Acceptance measurability: accept Gherkin via LLM on hard cases; keep modal-word rule as fallback.
- Test categorization gaps: map free text to {unit, integration, e2e, acceptance, manual, contract, property, smoke} via LLM on hard cases; fallback to keywords.
- Security coverage narrowness: LLM recognizes broader concepts (e.g., threat model, vault rotation) on hard cases; keep minimal safety-net tokens.
- Ambiguity near thresholds: log LLM rationale; do not auto-PASS—policy remains deterministic.
- API/OOD robustness: keep deterministic fixes (Retry-After parsing, non‑JSON/204 responses) and thresholds; LLM not used here.

Implementation Checklist (minimal)
- Add alias map and resolver used by link validation and artefact writer.
- Add optional LLMClassifier with: enable flag, timeout, confidence threshold, JSON schema, and caching.
- Wire LLM assist at three hooks only: artefact detection (fallback), acceptance measurability (fallback), test type mapping (fallback).
- Keep existing strict thresholds and scoring; no behavior change when assist disabled.

Exit Criteria
- Gate outcomes consistent and reproducible; fewer spurious violations on real BMAD docs without relaxing thresholds.
- Links and CI stable across doc renames via alias + migration.
- Assist produces clear, logged rationales on hard cases; builds remain deterministic.
