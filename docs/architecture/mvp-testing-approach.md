# MVP Testing Approach

## Basic Testing Strategy

**Unit Testing:**
- Core orchestration logic
- Template parsing and validation
- Basic agent coordination
- Target: 60-70% coverage for MVP

**Integration Testing:**
- CrewAI + BMAD template interaction
- Artefact generation workflow
- Basic tool use capabilities

**Simple Quality Gates:**
- **PASS**: Template loads, agents execute, artefacts generated
- **FAIL**: Critical errors prevent basic functionality

## Testing Infrastructure (MVP)

**Directory Structure:**
```
docs/qa/
├── gates/                # Simple quality gate decisions
│   └── {epic}.{story}-{slug}.yml
└── basic-checks/         # Basic validation results
    └── {epic}.{story}-checks.md
```

**Gate File (Simplified):**
```yaml
schema: 1
story: "1.1"
gate: PASS|FAIL
status: "Template validation passed, artefacts generated successfully"
reviewer: "Basic QA"
updated: "2025-01-17T10:30:00Z"
```
