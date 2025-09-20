# Epic 4: Hard-Case LLM Assist + Canonical Path Stability

## Goal
Deliver a single approach that keeps BMAD strict and deterministic while reducing false positives/negatives and ambiguity in language-heavy checks. Stabilize artefact paths across documentation changes.

## Problem
- Rule/keyword checks (acceptance, testing, security, artefact typing) can misfire on phrasing variants.
- BMAD docs evolve (e.g., brownfield-prd.md → prd.md) causing link/tooling breakage.

## Approach
- Deterministic backbone (authoritative): canonical paths, thresholds, scoring, and mechanics remain code-driven.
- Small LLM assist on hard cases only (config-gated, default off): artefact detection fallback, acceptance measurability fallback, test type mapping fallback. Strict JSON + confidence gate + timeout + cache; always fall back to rules on low confidence.
- Canonical path stability via alias resolver and one-time migration guidance.

## Scope
- Path alias resolver shared by link validation and artefact writer.
- Optional `LLMClassifier` with config flags and strict schema (off by default).
- Wire assist at three points only (fallbacks): artefact detection, acceptance measurability, test type mapping.
- No policy relaxation; PASS/CONCERNS/FAIL and thresholds unchanged.

## Deliverables
- Alias resolver + minimal config.
- Optional LLM assist module + hooks (guarded behind config).
- Operator notes and audit trace for hard-case decisions.

## Acceptance Criteria
- With assist disabled, behavior is unchanged on existing tests (bit-for-bit).
- Links/CI stable across doc renames via alias; missing canonical paths produce guided migration.
- With assist enabled, fewer spurious flags on real BMAD docs without changing thresholds.

## Stories
- 3.5 Path Alias Resolver (course-correct)
- 3.6 Single Gate Decision Source (course-correct)
- 4.1 LLM Assist Scaffolding + Artefact Detection Fallback (config off by default)
- 4.2 Acceptance Measurability Fallback
- 4.3 Test Type Mapping Fallback
