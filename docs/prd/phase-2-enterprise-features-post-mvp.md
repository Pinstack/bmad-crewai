# Phase 2: Enterprise Features (Post-MVP)

## 🔴 HIGH PRIORITY: Context7 MCP Integration
- **Purpose**: Provide CrewAI agents with up-to-date framework documentation and enable Codex CLI/Web integration
- **Priority**: High - Essential for technical research capabilities and development workflow enhancement
- **Timeline**: 6-8 months post-MVP
- **Features**:
  - `mcp_Context7_resolve-library-id` for library identification
  - `mcp_Context7_get-library-docs` for documentation retrieval
  - Automatic context injection into BMAD research tasks
  - Integration with Architect agent for technical framework research
  - Codex CLI integration via CodexMCP wrapper
  - Codex Web interface support through MCP protocol
- **Configuration Requirements**:
  - **CodexMCP Installation**: `pip install codexmcp[openai]`
  - **Codex CLI Installation**: `npm install -g @openai/codex`
  - **Environment Variables**:
    - `OPENAI_API_KEY` for Codex API access
    - `CODEXMCP_DEFAULT_MODEL` (default: "o4-mini")
    - `CODEXMCP_LOG_LEVEL` (default: INFO)
    - `CODEXMCP_USE_CLI` (default: true)
    - `CODEX_PATH` (if Codex CLI not in PATH)
  - **MCP Server Configuration**: `python -m codexmcp.server` (default port 8080)
  - **Fallback Mechanisms**: OpenAI API fallback when CLI unavailable
  - **Web Interface Support**: JSON-based MCP communication protocol
- **Business Value**: 40% faster technical research, 25% reduction in outdated documentation issues, seamless Codex integration

## Advanced Quality Management
- **Stable Identifiers**: Every artefact, activity, template, checklist, and gate has a stable ID (ART_*, ACT_*, TMP_*, CHK_*, GATE_*)
- **Hash/Version Coupling**: Gate result = f(artefact_content_hash, checklist_version) with status-index.json tracking
- **Formal Waiver Policy**: Who can waive which gates, expiry, approver, auto-recheck, audit notes required
- **SLAs & Escalation**: Per-gate max runtime, retry policy, escalation path, owner role
- **Conformance & Drift Rules**: Automatic remediation for non-conformant steps (rerun, re-shard, reopen story)

## Analytics & Monitoring
- **Event Log Specification**: Fields for case_id, act_id, gate_id?, role, art_id?, ts_start, ts_end, result, severity, artefact_hash?, checklist_ver?, waiver_id?
- **Model Governance**: Record per-agent model name, version, temperature, preset ID, prompt hash in artefact headers and event log
- **KPIs Binding**: Tie existing metrics to log fields (first-pass rate, rework count, AC→test coverage, cycle time)

## Enhanced Workflows
- **Enforcement Loci**: Local (CHK_DOD pre-commit), PR checks (PO/PM/ARCH/QA gates required), Release (SEC/NFR baseline required)
- **Brownfield Fast Paths**: Single-story (<4h) and small-feature (1-3 stories) routes skipping heavy artefacts with compensating controls
- **Failure Semantics**: Idempotent retry count per gate, then HITL pause; rework loops create linked fix tasks
