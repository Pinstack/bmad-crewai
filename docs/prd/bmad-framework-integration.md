# BMAD Framework Integration

## BMAD Agent Registry

The following BMAD agents will be integrated with CrewAI orchestration:

| Agent | Purpose | Integration Point | Status |
|-------|---------|------------------|--------|
| **Product Manager (PM)** | Requirements management, PRD creation | CrewAI task execution for product strategy | Required |
| **System Architect** | Technical architecture design | CrewAI coordination for system design | Required |
| **Test Architect (QA)** | Quality assurance, risk assessment | CrewAI workflow validation and quality gates | Required |
| **Developer (Dev)** | Code implementation, testing | CrewAI task assignment for development work | Required |
| **Product Owner (PO)** | Process validation, story approval | CrewAI workflow orchestration | Required |
| **Scrum Master (SM)** | Story creation, agile coordination | CrewAI task sequencing and handoffs | Required |
| **BMAD Master** | Universal task execution | CrewAI fallback and complex operations | Optional |
| **BMAD Orchestrator** | Multi-agent coordination | CrewAI meta-orchestration | Optional |

## BMAD Template Integration

CrewAI will consume the following BMAD templates for workflow orchestration:

### Core Templates (Required)
| Template | Purpose | CrewAI Integration | Status |
|----------|---------|-------------------|--------|
| **prd-tmpl.yaml** | Product Requirements Document | CrewAI PM agent execution | Required |
| **architecture-tmpl.yaml** | System architecture design | CrewAI Architect agent execution | Required |
| **story-tmpl.yaml** | User story creation | CrewAI SM agent execution | Required |
| **qa-gate-tmpl.yaml** | Quality gate decisions | CrewAI QA agent execution | Required |

### Workflow-Specific Templates
| Template | Purpose | CrewAI Integration | Status |
|----------|---------|-------------------|--------|
| **brownfield-prd-tmpl.yaml** | Brownfield PRD creation | CrewAI PM agent for existing systems | Required |
| **brownfield-architecture-tmpl.yaml** | Brownfield architecture analysis | CrewAI Architect agent | Required |
| **fullstack-architecture-tmpl.yaml** | Full-stack system design | CrewAI Architect agent | Required |
| **front-end-architecture-tmpl.yaml** | Frontend architecture design | CrewAI Architect agent | Optional |

## BMAD Task Integration

The following BMAD tasks will be orchestrated by CrewAI:

### Core Development Tasks (Required)
| Task | Purpose | CrewAI Trigger | Status |
|------|---------|----------------|--------|
| **create-doc** | Document generation from templates | CrewAI workflow execution | Required |
| **execute-checklist** | Quality validation and checklists | CrewAI QA integration | Required |
| **review-story** | Comprehensive code review | CrewAI QA workflow | Required |
| **validate-next-story** | Story validation and approval | CrewAI PO workflow | Required |

### Specialized Tasks
| Task | Purpose | CrewAI Trigger | Status |
|------|---------|----------------|--------|
| **create-next-story** | Story creation from epics | CrewAI SM workflow | Required |
| **risk-profile** | Risk assessment and analysis | CrewAI QA pre-development | Required |
| **test-design** | Test strategy and planning | CrewAI QA development phase | Required |
| **trace-requirements** | Requirements traceability | CrewAI QA validation | Required |
| **nfr-assess** | Non-functional requirements | CrewAI QA quality gates | Required |
| **shard-doc** | Document sharding for IDE | CrewAI PO workflow completion | Required |

### Brownfield-Specific Tasks
| Task | Purpose | CrewAI Trigger | Status |
|------|---------|----------------|--------|
| **brownfield-create-epic** | Brownfield epic creation | CrewAI PM brownfield workflow | Required |
| **brownfield-create-story** | Brownfield story creation | CrewAI SM brownfield workflow | Required |
| **document-project** | Existing codebase analysis | CrewAI Architect brownfield | Required |

## BMAD Checklist Integration

Quality gates will use the following BMAD checklists:

| Checklist | Purpose | CrewAI Integration | Status |
|-----------|---------|-------------------|--------|
| **po-master-checklist** | Product Owner validation | CrewAI PO workflow | Required |
| **architect-checklist** | Architecture quality assessment | CrewAI Architect workflow | Required |
| **story-dod-checklist** | Definition of Done validation | CrewAI Dev completion | Required |
| **story-draft-checklist** | Story draft validation | CrewAI SM creation | Required |
| **pm-checklist** | PRD quality validation | CrewAI PM workflow | Required |
| **change-checklist** | Change management | CrewAI PO change navigation | Optional |

## BMAD Workflow Integration

CrewAI will support the following BMAD workflow patterns:

| Workflow | Purpose | CrewAI Execution | Status |
|----------|---------|-----------------|--------|
| **greenfield-fullstack** | New full-stack application | Complete CrewAI orchestration | Required |
| **brownfield-fullstack** | Existing system enhancement | CrewAI brownfield orchestration | Required |
| **greenfield-service** | New backend service | CrewAI service-focused workflow | Required |
| **brownfield-service** | Existing service modification | CrewAI service brownfield workflow | Required |
| **greenfield-ui** | New frontend application | CrewAI UI-focused workflow | Optional |
| **brownfield-ui** | Existing UI enhancement | CrewAI UI brownfield workflow | Optional |

## BMAD Data Integration

The following BMAD data resources will be utilized:

| Data Resource | Purpose | CrewAI Access | Status |
|---------------|---------|---------------|--------|
| **bmad-kb.md** | Framework knowledge base | CrewAI agent context | Required |
| **technical-preferences.md** | Tech stack preferences | CrewAI decision making | Required |
| **test-levels-framework.md** | Testing strategy guidance | CrewAI QA planning | Required |
| **test-priorities-matrix.md** | Risk-based test prioritization | CrewAI QA execution | Required |
| **elicitation-methods.md** | User interaction techniques | CrewAI agent communication | Required |
| **brainstorming-techniques.md** | Ideation facilitation | CrewAI PM/PO workflows | Optional |

## BMAD Configuration Integration

### Core Configuration Requirements
- **core-config.yaml**: BMAD framework configuration
  - Path: `.bmad-core/core-config.yaml`
  - Integration: CrewAI reads for folder paths and settings
  - Status: Required

### Configuration Parameters
| Parameter | Purpose | CrewAI Usage | Status |
|-----------|---------|--------------|--------|
| **prd.prdFile** | PRD document location | CrewAI artefact output path | Required |
| **architecture.architectureFile** | Architecture document location | CrewAI artefact output path | Required |
| **devStoryLocation** | Story document location | CrewAI artefact output path | Required |
| **qa.qaLocation** | QA document location | CrewAI artefact output path | Required |
| **prd.prdSharded** | Sharding configuration | CrewAI workflow decisions | Required |
| **markdownExploder** | Document processing | CrewAI artefact generation | Required |

## BMAD Utility Integration

The following BMAD utilities will be integrated:

| Utility | Purpose | CrewAI Integration | Status |
|---------|---------|-------------------|--------|
| **workflow-management.md** | Workflow orchestration guidance | CrewAI process management | Required |
| **bmad-doc-template.md** | Documentation standards | CrewAI artefact formatting | Required |

## Integration Architecture Summary

### CrewAI Orchestration Layer
```python
# Core integration pattern
crew = Crew(
    agents=[
        ProductManager(),      # BMAD PM agent
        SystemArchitect(),     # BMAD Architect agent
        TestArchitect(),       # BMAD QA agent
        Developer(),          # BMAD Dev agent
        ProductOwner(),       # BMAD PO agent
        ScrumMaster()         # BMAD SM agent
    ],
    tasks=load_bmad_tasks(),  # From BMAD task definitions
    templates=load_bmad_templates(),  # From BMAD template system
    workflows=load_bmad_workflows()   # From BMAD workflow definitions
)
```

### Artefact Generation Pattern
```python
# BMAD folder structure integration
artefact_writer = BmadArtefactWriter(
    base_paths={
        'prd': 'docs/prd.md',
        'architecture': 'docs/architecture.md',
        'stories': 'docs/stories/',
        'qa': 'docs/qa/'
    }
)

# CrewAI writes artefacts to BMAD structure
result = crew.execute_workflow('greenfield-fullstack')
artefact_writer.write_artefacts(result.outputs)
```

### Quality Gate Integration
```python
# BMAD checklists as CrewAI quality gates
quality_manager = BmadQualityManager(
    checklists=[
        'po-master-checklist',
        'architect-checklist',
        'story-dod-checklist'
    ]
)

# CrewAI enforces BMAD quality gates
gate_result = quality_manager.validate_gate(
    workflow_output=result,
    checklist='po-master-checklist'
)
```
