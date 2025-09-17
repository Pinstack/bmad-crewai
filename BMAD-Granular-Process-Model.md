# BMAD Framework: Granular Process Model

## Overview

This document provides a **detailed, executable process model** for the BMAD framework, with explicit instructions for each agent at every step. The model includes structured elicitation questions, conditional logic, artefact binding, validation loops, and output schemas.

## Process Flow Architecture

### Core Phases

1. **Classification & Routing** (0-5 min)
2. **Planning & Documentation** (30-120 min)
3. **Validation & Sharding** (15-45 min)
4. **Story Creation & Implementation** (Iterative)

---

## Phase 1: Classification & Routing

### Step 1.1: Initial Enhancement Classification

**Agent:** analyst
**Condition:** Always first step
**Artefact Input:** None

#### Structured Elicitation Questions

```
AGENT MUST ASK (in this exact order):

1. "What type of project is this?"
   - [ ] Greenfield (new project)
   - [ ] Brownfield (enhancing existing system)
   - [ ] If Brownfield: "Briefly describe the existing system"

2. "What is the enhancement scope?"
   - [ ] Single story (< 4 hours development)
   - [ ] Small feature (1-3 stories)
   - [ ] Major enhancement (multiple epics)
   - [ ] If unsure: "Can you describe what you're trying to achieve?"

3. "What documentation exists?"
   - [ ] PRD.md
   - [ ] Architecture.md
   - [ ] Existing code/docs
   - [ ] None
   - [ ] If none: "Do you have access to the existing codebase?"

4. "What is your timeline?"
   - [ ] Immediate (today)
   - [ ] This week
   - [ ] This month
   - [ ] Flexible
```

#### Conditional Logic & Routing

```yaml
# ROUTING DECISIONS
if scope == "single_story":
  route_to: "brownfield-create-story"
  exit_workflow: true

elif scope == "small_feature":
  route_to: "brownfield-create-epic"
  exit_workflow: true

elif scope == "major_enhancement":
  route_to: "full_brownfield_workflow"

elif scope == "greenfield":
  route_to: "greenfield_workflow"

elif no_codebase_access:
  halt_workflow: "Cannot proceed without codebase access"
  message: "Please ensure you have access to the existing codebase"

elif no_timeline:
  default_timeline: "this_week"
```

#### Validation Loop

```
CONFIRMATION REQUIRED:
"Based on your answers, I recommend: [routing_decision]
Is this correct? Would you like to proceed or clarify any answers?"
- [ ] Proceed
- [ ] Clarify answers
- [ ] Change recommendation
```

---

## Phase 2: Planning & Documentation

### Step 2.1: Project Analysis (Brownfield Only)

**Agent:** architect
**Condition:** brownfield_major_enhancement && inadequate_documentation
**Artefact Input:** Existing codebase access

#### Structured Elicitation Questions

```
AGENT MUST ASK:

1. "What is the primary purpose of this system?"
   - Expected: 1-2 sentence description

2. "What are the most critical components/modules?"
   - Expected: List of 3-5 key areas

3. "What patterns/frameworks does the system use?"
   - Expected: Technology stack details

4. "Are there known technical debt areas?"
   - Expected: List of issues or "unknown"

5. "What integration points exist?"
   - Expected: External APIs, services, databases
```

#### Artefact Binding

```
OUTPUT FILE: docs/brownfield-architecture.md
LOCATION: Project root/docs/
FORMAT: Markdown document
```

#### Output Schema

```markdown
# Brownfield Architecture Analysis

## System Overview
- **Primary Purpose**: [1-2 sentence description]
- **Architecture Type**: [monolith/microservices/hybrid]
- **Technology Stack**: [list key technologies]

## Critical Components
1. **[Component Name]**: [Purpose, location, dependencies]
2. **[Component Name]**: [Purpose, location, dependencies]
3. **[Component Name]**: [Purpose, location, dependencies]

## Integration Points
| Component | Purpose | Dependencies | Risk Level |
|-----------|---------|--------------|------------|
| [name]    | [desc]  | [list]       | [low/med/high] |

## Technical Debt
- **HIGH RISK**: [item] - [impact description]
- **MEDIUM RISK**: [item] - [impact description]
- **LOW RISK**: [item] - [impact description]

## Recommendations for Enhancement
- **[Enhancement]**: [How it integrates, risks, approach]
```

#### Validation Loop

```
CONFIRMATION REQUIRED:
"I need to analyze your codebase to create this document. Do you have:
- Access to the source code?
- Any existing documentation?
- Specific areas you'd like me to focus on?"
- [ ] Yes, proceed
- [ ] Need to provide access
- [ ] Need clarification
```

---

### Step 2.2: PRD Creation

**Agent:** pm
**Condition:** Always required after classification
**Artefact Input:**

- For greenfield: project-brief.md
- For brownfield: brownfield-architecture.md

#### Structured Elicitation Questions

```
AGENT MUST ASK (in order of priority):

1. "What problem does this solve for users?"
   - Expected: User problem statement

2. "Who are the primary users?"
   - Expected: User personas with characteristics

3. "What are the acceptance criteria for success?"
   - Expected: Measurable success metrics

4. "What are the functional requirements?"
   - Expected: Feature list with priorities

5. "What are the technical constraints?"
   - Expected: Platform, performance, security requirements

6. "What is out of scope?"
   - Expected: Explicit boundaries

7. "What is the MVP definition?"
   - Expected: Minimum viable product scope
```

#### Artefact Binding

```
OUTPUT FILE: docs/prd.md
LOCATION: Project root/docs/
TEMPLATE: brownfield-prd-tmpl.yaml OR prd-tmpl.yaml
FORMAT: Markdown with YAML frontmatter
```

#### Output Schema

```markdown
---
title: "Product Requirements Document"
version: "1.0"
status: "draft"
created: "2025-01-17"
author: "PM Agent"
---

# Product Requirements Document

## Executive Summary
- **Problem**: [1-2 sentence problem statement]
- **Solution**: [1-2 sentence solution]
- **Success Metrics**: [3-5 measurable KPIs]

## User Personas
### Primary Persona: [Name]
- **Role**: [Job title, responsibilities]
- **Goals**: [What they want to achieve]
- **Pain Points**: [Current problems]
- **Usage Frequency**: [How often they use similar systems]

## Requirements Matrix

| ID | Requirement | Priority | Acceptance Criteria | Status |
|----|-------------|----------|-------------------|--------|
| R1 | [Requirement] | P0/P1/P2 | [Measurable criteria] | Draft |

## Technical Requirements
### Functional Requirements
1. **[Feature Name]**: [Detailed description]
2. **[Feature Name]**: [Detailed description]

### Non-Functional Requirements
1. **Performance**: [Response time, throughput requirements]
2. **Security**: [Authentication, authorization, data protection]
3. **Scalability**: [User load, data volume requirements]
4. **Reliability**: [Uptime, error handling requirements]

## Out of Scope
- [Feature X]: [Reason why excluded]
- [Feature Y]: [Reason why excluded]

## MVP Definition
### Must Have (P0)
- [Feature A]: [Why essential]
- [Feature B]: [Why essential]

### Should Have (P1)
- [Feature C]: [Why important]

### Nice to Have (P2)
- [Feature D]: [Why desirable]

## Risk Assessment
### High Risk
- **[Risk]**: Probability: [high/med/low], Impact: [high/med/low], Mitigation: [strategy]

### Medium Risk
- **[Risk]**: Probability: [high/med/low], Impact: [high/med/low], Mitigation: [strategy]

## Success Metrics
1. **[Metric]**: Target: [value], Measurement: [how]
2. **[Metric]**: Target: [value], Measurement: [how]
3. **[Metric]**: Target: [value], Measurement: [how]
```

#### Validation Loop

```
CONFIRMATION REQUIRED:
"Before I create the PRD, let me confirm my understanding:

1. The main problem is: [repeat back]
2. Primary users are: [repeat back]
3. Success will be measured by: [repeat back]
4. MVP scope includes: [repeat back]

Is this accurate? Shall I proceed with PRD creation?"
- [ ] Accurate, proceed
- [ ] Need corrections
- [ ] Need more information
```

---

### Step 2.3: Architecture Decision

**Agent:** architect
**Condition:** After PRD creation
**Artefact Input:** docs/prd.md

#### Structured Elicitation Questions

```
AGENT MUST ASK:

1. "Does the PRD require architectural changes?"
   - [ ] New technologies/frameworks
   - [ ] New architectural patterns
   - [ ] Infrastructure changes
   - [ ] No significant changes needed

2. "What are the technical risks?"
   - Expected: List of 3-5 potential issues

3. "What integration points need consideration?"
   - Expected: External services, APIs, databases

4. "What are the performance requirements?"
   - Expected: Response times, scalability needs
```

#### Conditional Logic

```yaml
# ARCHITECTURE DECISION MATRIX
if any_changes_needed:
  create_architecture_doc: true
  template: "brownfield-architecture-tmpl.yaml"
  required_sections: ["integration", "risks", "migration"]

elif following_existing_patterns:
  create_architecture_doc: false
  document_decision: "Following existing patterns - no architecture doc needed"
  validation_check: "Confirm existing architecture supports requirements"

elif unclear_requirements:
  halt_workflow: "Need clarification on technical approach"
  questions: ["What technologies are you open to?", "Are there existing constraints?"]
```

#### Artefact Binding

```
OUTPUT FILE: docs/architecture.md
LOCATION: Project root/docs/
TEMPLATE: brownfield-architecture-tmpl.yaml
CONDITION: architecture_changes_needed == true
```

#### Output Schema (Architecture Document)

```markdown
---
title: "System Architecture Document"
version: "1.0"
status: "draft"
created: "2025-01-17"
author: "Architect Agent"
enhancement: "[Enhancement Name]"
---

# System Architecture Document

## Executive Summary
- **Enhancement**: [What is being added/changed]
- **Architecture Impact**: [High/Medium/Low]
- **Key Decisions**: [3-5 major decisions]

## Current System Architecture
### High-Level Overview
[Diagram or description of existing system]

### Key Components
1. **[Component]**: [Purpose, technology, responsibilities]
2. **[Component]**: [Purpose, technology, responsibilities]

## Enhancement Architecture
### Proposed Changes
[Diagram showing changes]

### Component Changes
| Component | Change Type | Impact | Risk Level |
|-----------|-------------|--------|------------|
| [name]    | [add/modify] | [high/med/low] | [high/med/low] |

## Technical Design
### Architecture Patterns
- **[Pattern]**: [Why chosen, how implemented]
- **[Pattern]**: [Why chosen, how implemented]

### Data Flow
[Sequence diagram or description]

### Integration Points
1. **[Integration]**: [API, data format, authentication]
2. **[Integration]**: [API, data format, authentication]

## Implementation Plan
### Phase 1: Foundation
- [Task]: [Description, dependencies, effort]

### Phase 2: Implementation
- [Task]: [Description, dependencies, effort]

### Phase 3: Integration
- [Task]: [Description, dependencies, effort]

## Risk Assessment
### High Risk Items
- **[Risk]**: Likelihood: [high/med/low], Impact: [high/med/low]
  **Mitigation**: [Specific strategy]

### Medium Risk Items
- **[Risk]**: Likelihood: [high/med/low], Impact: [high/med/low]
  **Mitigation**: [Specific strategy]

## Performance Considerations
- **Response Times**: [Requirements and approach]
- **Scalability**: [Growth expectations and strategy]
- **Monitoring**: [Metrics and alerting]

## Security Considerations
- **Authentication**: [Approach and requirements]
- **Authorization**: [Role-based access control]
- **Data Protection**: [Encryption and privacy]

## Deployment Strategy
### Environment Strategy
- **Development**: [Setup and configuration]
- **Staging**: [Testing and validation]
- **Production**: [Deployment and monitoring]

### Rollback Plan
1. **Trigger Conditions**: [When to rollback]
2. **Rollback Steps**: [Specific procedure]
3. **Validation**: [How to confirm rollback success]

## Testing Strategy
### Unit Testing
- **Coverage Target**: [Percentage]
- **Tools**: [Framework, mocking libraries]
- **Approach**: [Isolation, mocking strategy]

### Integration Testing
- **Scope**: [What to test, boundaries]
- **Environment**: [Test database, services]
- **Data**: [Test data strategy]

### End-to-End Testing
- **User Journeys**: [Critical paths]
- **Performance**: [Load testing requirements]
- **Automation**: [Tools and approach]

## Monitoring and Observability
### Application Metrics
- **[Metric]**: [Purpose, thresholds, alerting]

### Infrastructure Metrics
- **[Metric]**: [Purpose, thresholds, alerting]

### Logging Strategy
- **Levels**: [Error, Warn, Info, Debug]
- **Retention**: [Duration, size limits]
- **Analysis**: [Tools, dashboards]

## Migration Strategy
### Data Migration
- **Source**: [Current data structure]
- **Target**: [New data structure]
- **Validation**: [Data integrity checks]

### Feature Migration
- **Phased Rollout**: [Percentage of users, duration]
- **Feature Flags**: [Implementation approach]
- **Rollback**: [Graceful degradation]

## Success Criteria
1. **[Criteria]**: [Measurable outcome]
2. **[Criteria]**: [Measurable outcome]
3. **[Criteria]**: [Measurable outcome]
```

---

## Phase 3: Validation & Sharding

### Step 3.1: PO Master Validation

**Agent:** po
**Condition:** After all planning documents created
**Artefact Input:** docs/prd.md, docs/architecture.md (if exists)

#### Structured Elicitation Questions

```
AGENT MUST ASK:

1. "Are all planning documents complete?"
   - [ ] PRD.md exists and complete
   - [ ] Architecture.md exists (if needed)
   - [ ] All sections filled out
   - [ ] No placeholder text remaining

2. "Do the documents align?"
   - [ ] PRD requirements match architecture capabilities
   - [ ] No conflicting assumptions
   - [ ] Consistent terminology
   - [ ] Compatible timelines

3. "Are there any missing validations?"
   - [ ] Checklist items covered
   - [ ] Integration safety verified
   - [ ] Brownfield compatibility confirmed
   - [ ] Technical feasibility validated
```

#### Checklist Execution

**PO Master Checklist Items:**

```markdown
## PO Master Checklist

### 1. Document Completeness
- [ ] PRD has executive summary with clear problem/solution
- [ ] PRD has user personas with goals and pain points
- [ ] PRD has acceptance criteria for each requirement
- [ ] PRD has clear MVP definition with priorities
- [ ] PRD has out-of-scope items explicitly listed
- [ ] Architecture document exists (if changes required)
- [ ] Architecture covers integration points
- [ ] Architecture addresses security and performance

### 2. Consistency Validation
- [ ] Terminology consistent across documents
- [ ] User personas align between PRD and architecture
- [ ] Technical requirements match architecture capabilities
- [ ] Timeline and effort estimates realistic
- [ ] Success metrics measurable and achievable

### 3. Integration Safety (Brownfield Only)
- [ ] Existing functionality preservation confirmed
- [ ] API compatibility verified
- [ ] Database changes backward compatible
- [ ] Rollback procedures documented
- [ ] Performance impact assessed
- [ ] Security implications evaluated

### 4. Technical Feasibility
- [ ] Technology choices justified
- [ ] Team skills match requirements
- [ ] Infrastructure available
- [ ] Third-party dependencies accessible
- [ ] Timeline technically achievable

### 5. Risk Assessment
- [ ] High-risk items identified with mitigations
- [ ] Contingency plans documented
- [ ] Dependencies identified and managed
- [ ] Assumptions validated
- [ ] Unknown factors documented

### 6. Business Alignment
- [ ] Requirements tie back to business goals
- [ ] Success metrics align with objectives
- [ ] ROI justification clear
- [ ] Stakeholder approval obtained
- [ ] Communication plan exists

## Validation Results

**Overall Status:**
- [ ] PASS - All documents validated, ready for development
- [ ] CONDITIONAL - Minor issues requiring fixes
- [ ] FAIL - Major issues requiring revision

**Issues Found:**
1. **[Issue]**: [Description, severity: high/medium/low]
2. **[Issue]**: [Description, severity: high/medium/low]

**Recommended Actions:**
- [ ] Fix high-priority issues before proceeding
- [ ] Address medium-priority issues in planning
- [ ] Document low-priority items for future consideration
```

#### Validation Loop

```
CONFIRMATION REQUIRED:
"PO validation complete. Status: [PASS/CONDITIONAL/FAIL]

Issues found: [summary]
Required fixes: [list]

Do you want me to:
1. [ ] Fix the identified issues
2. [ ] Get clarification on specific points
3. [ ] Proceed despite issues (documented risk)
4. [ ] Request additional information"
```

---

### Step 3.2: Document Sharding

**Agent:** po
**Condition:** PO validation passed
**Artefact Input:** docs/prd.md

#### Structured Elicitation Questions

```
AGENT MUST ASK:

1. "Are you ready to move to development?"
   - [ ] Yes, shard documents for IDE development
   - [ ] No, need more planning time
   - [ ] Need to fix validation issues first

2. "Do you prefer automated or manual sharding?"
   - [ ] Automated (recommended, faster)
   - [ ] Manual (if you want to review each file)
   - [ ] If unsure: "Automated is usually faster and more consistent"

3. "Any specific sharding preferences?"
   - [ ] Default structure (epics/ folder)
   - [ ] Custom folder structure
   - [ ] Include/exclude specific sections
```

#### Artefact Binding

```
INPUT FILE: docs/prd.md
OUTPUT STRUCTURE:
docs/prd/
├── epic-1-name/
│   ├── overview.md
│   ├── stories.md
│   └── requirements.md
├── epic-2-name/
│   ├── overview.md
│   ├── stories.md
│   └── requirements.md
└── index.md (links to all epics)
```

#### Output Schema (Sharded Documents)

```
docs/prd/index.md:
# Product Requirements Document

## Epic Overview

| Epic | Stories | Priority | Status |
|------|---------|----------|--------|
| [Epic 1] | [count] | [P0/P1/P2] | Draft |

## Detailed Epics

### Epic 1: [Epic Title]
- **Goal**: [Epic objective]
- **Stories**: [List of story titles]
- **Priority**: [P0/P1/P2]
- **Acceptance Criteria**: [Epic-level criteria]

[Link to epic folder]

### Epic 2: [Epic Title]
- **Goal**: [Epic objective]
- **Stories**: [List of story titles]
- **Priority**: [P0/P1/P2]
- **Acceptance Criteria**: [Epic-level criteria]

[Link to epic folder]

docs/prd/epic-1-name/overview.md:
# Epic 1: [Epic Title]

## Epic Goal
[1-2 sentence objective]

## Business Value
[Why this epic matters]

## Stories Included
1. **[Story 1]**: [Brief description]
2. **[Story 2]**: [Brief description]

## Acceptance Criteria
- [ ] [Epic-level criterion 1]
- [ ] [Epic-level criterion 2]

## Dependencies
- **Blocks**: [What this epic blocks]
- **Blocked by**: [What blocks this epic]
- **External**: [External dependencies]

## Risk Assessment
- **High Risk**: [Risk description]
- **Medium Risk**: [Risk description]

## Effort Estimate
- **Stories**: [count]
- **Total Effort**: [days/weeks]
- **Team**: [required roles]
```

#### Validation Loop

```
CONFIRMATION REQUIRED:
"Document sharding complete. Created:
- [X] epics in docs/prd/ folder
- [X] index.md with epic overview
- [X] individual epic folders with overview.md

Ready to proceed to story creation?
- [ ] Yes, proceed to SM agent
- [ ] Review sharded content first
- [ ] Need to modify sharding structure"
```

---

## Phase 4: Story Creation & Implementation

### Step 4.1: Story Creation

**Agent:** sm
**Condition:** Documents sharded successfully
**Artefact Input:** docs/prd/ (sharded documents)

#### Structured Elicitation Questions

```
AGENT MUST ASK:

1. "Which epic should we create the first story for?"
   - [ ] Epic 1: [title]
   - [ ] Epic 2: [title]
   - [ ] Other: [specify]
   - Expected: Epic selection

2. "What is the story scope?"
   - [ ] Single user action (< 2 hours)
   - [ ] Small feature (2-4 hours)
   - [ ] Complex feature (4-8 hours)
   - Expected: Scope assessment

3. "Are there technical dependencies?"
   - [ ] None
   - [ ] Database changes required
   - [ ] API endpoints needed
   - [ ] Infrastructure setup
   - Expected: Dependency identification

4. "What testing approach is needed?"
   - [ ] Unit tests only
   - [ ] Integration tests required
   - [ ] E2E tests needed
   - [ ] Manual testing sufficient
```

#### Artefact Binding

```
OUTPUT FILE: docs/stories/epic-1.1-story-title.md
LOCATION: docs/stories/
NAMING: {epic-number}.{story-number}-{kebab-case-title}.md
```

#### Output Schema (Story Document)

```markdown
---
epic: "1"
story: "1"
title: "User Authentication"
status: "Draft"
created: "2025-01-17"
author: "SM Agent"
priority: "P0"
effort: "3 hours"
---

# Story 1.1: User Authentication

## Status: Draft

## Story Statement

**As a** [user type]
**I want to** [specific capability]
**So that** [clear benefit/value]

## Context
[2-3 sentence explanation of why this story matters in the epic context]

## Acceptance Criteria

### Functional Requirements
1. **[AC1]**: [Measurable criterion] - *[Test Method: unit/integration/e2e]*
2. **[AC2]**: [Measurable criterion] - *[Test Method: unit/integration/e2e]*
3. **[AC3]**: [Measurable criterion] - *[Test Method: unit/integration/e2e]*

### Quality Requirements
4. **[AC4]**: Code follows project standards - *[Test Method: lint/unit]*
5. **[AC5]**: No performance degradation - *[Test Method: integration]*
6. **[AC6]**: Documentation updated - *[Test Method: manual]*

### Integration Requirements (Brownfield Only)
7. **[AC7]**: Existing functionality preserved - *[Test Method: integration]*
8. **[AC8]**: Backward compatibility maintained - *[Test Method: e2e]*
9. **[AC9]**: No breaking changes to APIs - *[Test Method: integration]*

## Technical Implementation

### Key Components to Create/Modify
1. **[Component]**: [File path, purpose, changes needed]
2. **[Component]**: [File path, purpose, changes needed]

### Dependencies
- **Required Before**: [Story X.Y must be complete]
- **Required After**: [This story enables Story X.Y]
- **External**: [Third-party services, APIs]

### Data Model Changes
| Table/Entity | Change Type | Fields | Migration Required |
|--------------|-------------|--------|-------------------|
| [entity]     | [add/modify] | [fields] | [yes/no]         |

### API Changes
| Endpoint | Method | Change | Backward Compatible |
|----------|--------|--------|-------------------|
| [/api/auth] | POST | [change] | [yes/no]         |

## Testing Strategy

### Unit Tests
- **[Test 1]**: [Function to test] - *[Expected: result]*
- **[Test 2]**: [Function to test] - *[Expected: result]*

### Integration Tests
- **[Test 1]**: [Flow to test] - *[Setup, Action, Assertion]*
- **[Test 2]**: [Flow to test] - *[Setup, Action, Assertion]*

### End-to-End Tests
- **[Test 1]**: [User journey] - *[Steps, Expected outcome]*

## Dev Notes

### Technical Approach
[Specific implementation approach, patterns to follow]

### Edge Cases
- [Edge case 1]: [How to handle]
- [Edge case 2]: [How to handle]

### Assumptions
- [Assumption 1]: [Validation needed]
- [Assumption 2]: [Validation needed]

### Known Limitations
- [Limitation 1]: [Impact and mitigation]
- [Limitation 2]: [Impact and mitigation]

## Tasks / Subtasks

- [ ] **Task 1**: [High-level task]
  - [ ] **Subtask 1.1**: [Specific implementation step]
  - [ ] **Subtask 1.2**: [Specific implementation step]
- [ ] **Task 2**: [High-level task]
  - [ ] **Subtask 2.1**: [Specific implementation step]
- [ ] **Task 3**: [Testing task]
  - [ ] **Subtask 3.1**: [Unit tests]
  - [ ] **Subtask 3.2**: [Integration tests]

## Testing

### Manual Testing Checklist
- [ ] [Test scenario 1]
- [ ] [Test scenario 2]
- [ ] [Test scenario 3]

### Automated Testing Requirements
- **Unit Test Coverage**: [Target %]
- **Integration Test Coverage**: [Target %]
- **Performance Test Requirements**: [Criteria]

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tasks completed
- [ ] Code reviewed and approved
- [ ] Tests passing (unit, integration, e2e as applicable)
- [ ] Documentation updated
- [ ] No known bugs or issues
- [ ] Performance requirements met
- [ ] Security requirements satisfied
- [ ] Existing functionality preserved (brownfield)
- [ ] Story deployed to appropriate environment

## File List

### New Files Created
- `src/components/AuthForm.tsx`
- `src/services/authService.ts`
- `src/pages/LoginPage.tsx`

### Modified Files
- `src/App.tsx` - Added routing
- `src/api/client.ts` - Added auth endpoints

### Configuration Changes
- `src/config/auth.ts` - New configuration file
- `.env` - Added auth service URLs

## Dev Agent Record

### Agent Model Used
- **Primary Model**: [GPT-4/Claude-3.5/etc]
- **Reason**: [Why this model was chosen]

### Completion Notes
- **[Date/Time]**: [What was accomplished]
- **[Date/Time]**: [What was accomplished]

### Debug Log References
- **[Issue]**: [File:line, Resolution]
- **[Issue]**: [File:line, Resolution]

## Change Log

### v1.0.0 - 2025-01-17
- Initial story creation
- Basic requirements identified
- Technical approach defined

## QA Results

[Populated by QA agent during review]

## Agent Model Used
[AI model used for story creation]
```

#### Validation Loop

```
CONFIRMATION REQUIRED:
"Story created: docs/stories/1.1-user-authentication.md

Story details:
- Status: Draft
- Priority: P0
- Effort: 3 hours
- Acceptance Criteria: 9 items

Before proceeding to development:
1. Does the story scope match your expectations?
2. Are the acceptance criteria clear and testable?
3. Are there any technical assumptions that need validation?
4. Should we proceed to development or refine the story?

Choose:
- [ ] Proceed to development (status: Draft → Approved)
- [ ] Refine story requirements
- [ ] Add more technical details
- [ ] Need different scope/approach"
```

---

### Step 4.2: Story Implementation

**Agent:** dev
**Condition:** Story status changed to "Approved"
**Artefact Input:** docs/stories/1.1-story-name.md

#### Structured Elicitation Questions

```
AGENT MUST ASK:

1. "Do you have any additional context for implementation?"
   - [ ] No additional context needed
   - [ ] Technical preferences to follow
   - [ ] Integration requirements
   - [ ] Performance constraints

2. "Are there any files I should reference?"
   - [ ] Use existing patterns from [file]
   - [ ] Follow structure in [file]
   - [ ] No specific references needed

3. "What testing level should I prioritize?"
   - [ ] Unit tests focus
   - [ ] Integration tests required
   - [ ] Full test coverage needed
   - [ ] Based on story requirements

4. "Any specific tools or libraries to use?"
   - [ ] Use project standards
   - [ ] Specific library required
   - [ ] Open to suggestions
```

#### Implementation Workflow

```
DEVELOPMENT ORDER-OF-EXECUTION (MANDATORY):

1. READ TASK → IMPLEMENT TASK + SUBTASKS → WRITE TESTS → EXECUTE VALIDATIONS
2. IF ALL PASS → UPDATE CHECKBOX [x] → UPDATE FILE LIST → REPEAT
3. IF ANY FAIL → HALT FOR USER APPROVAL → FIX → RETRY

CRITICAL: Story has ALL info needed. DO NOT load PRD/architecture unless directed.
```

#### Artefact Binding

```
INPUT: docs/stories/1.1-story-name.md
OUTPUT: Implementation files + updated story
LOCATION: Project source code directories
STATUS UPDATE: Story status: Approved → InProgress → Review
```

#### Validation Loop (After Implementation)

```
CONFIRMATION REQUIRED:
"Implementation complete. Story status updated to 'Review'.

What I've implemented:
- [X] All tasks completed ([count]/[total])
- [X] Tests written and passing
- [X] File List updated
- [X] Acceptance criteria verified

Files created/modified: [list]

Do you want to:
1. [ ] Proceed to QA review
2. [ ] Make additional changes
3. [ ] Add more tests
4. [ ] Update documentation"
```

---

### Step 4.3: QA Review

**Agent:** qa
**Condition:** Story status = "Review"
**Artefact Input:** Implementation files + story document

#### Structured Elicitation Questions

```
AGENT MUST ASK:

1. "What QA approach should I use?"
   - [ ] Standard review (risk, design, trace, nfr)
   - [ ] Lightweight review (basic checks only)
   - [ ] Comprehensive review (all assessments)

2. "Are there specific areas of concern?"
   - [ ] Security considerations
   - [ ] Performance requiremFcjj2811

   - [ ] Integration points
   - [ ] No specific concerns

3. "What is the acceptable risk level?"
   - [ ] Zero defects (production-ready)
   - [ ] Minor issues acceptable
   - [ ] Prototype quality acceptable
```

#### QA Review Process

```
MANDATORY ASSESSMENT ORDER:
1. Risk Profile → Test Design → Requirements Trace → NFR Assessment
2. Code Review → Gate Decision
3. Update QA Results section
4. Update story status
```

#### Output Schema (QA Results Section)

```markdown
## QA Results

### Review Date: 2025-01-17

### Reviewed By: QA Agent

### Code Quality Assessment
- **Architecture**: [Excellent/Good/Needs Improvement] - [reason]
- **Code Standards**: [Compliant/Minor Issues/Major Issues] - [details]
- **Testing Coverage**: [Complete/Partial/Missing] - [percentage]

### Risk Assessment
- **Profile**: docs/qa/assessments/1.1-risk-20250117.md
- **High Risks**: [count] - [summary]
- **Medium Risks**: [count] - [summary]
- **Overall Risk**: [Low/Medium/High]

### Test Design
- **Scenarios**: [count] identified
- **Coverage**: [Complete/Partial/Missing]
- **Gaps**: [list any missing test scenarios]

### Requirements Traceability
- **Mapped**: [percentage]% of ACs to tests
- **Gaps**: [list unmapped ACs]
- **Coverage**: [Complete/Partial/Missing]

### Non-Functional Requirements
- **Security**: [PASS/CONCERNS/FAIL] - [notes]
- **Performance**: [PASS/CONCERNS/FAIL] - [notes]
- **Reliability**: [PASS/CONCERNS/FAIL] - [notes]
- **Maintainability**: [PASS/CONCERNS/FAIL] - [notes]

### Issues Found

#### Critical Issues (Must Fix)
1. **[ISSUE-001]**: [Description] - [Impact]
   - **Severity**: Critical
   - **Recommendation**: [Fix required]

#### Major Issues (Should Fix)
1. **[ISSUE-002]**: [Description] - [Impact]
   - **Severity**: Major
   - **Recommendation**: [Fix recommended]

#### Minor Issues (Nice to Fix)
1. **[ISSUE-003]**: [Description] - [Impact]
   - **Severity**: Minor
   - **Recommendation**: [Optional fix]

### Code Improvements Made
- **[File]**: [Change made] - [Reason]
- **[File]**: [Change made] - [Reason]

### Files Modified During Review
- `src/components/AuthForm.tsx` - Fixed validation logic
- `src/services/authService.ts` - Added error handling
- `tests/authService.test.ts` - Added missing test cases

### Gate Decision

**Gate Status**: [PASS/CONCERNS/FAIL/WAIVED]

**Rationale**: [2-3 sentence explanation]

**Gate File**: docs/qa/gates/1.1-user-authentication.yml

### Recommended Status

- [X] Ready for Done (all issues addressed)
- [ ] Changes Required (see issues above)
- [ ] Further Review Needed

### Next Steps
1. [Action item for dev/PO]
2. [Action item for dev/PO]
3. [Timeline expectations]
```

#### Validation Loop

```
CONFIRMATION REQUIRED:
"QA Review complete. Gate decision: [PASS/CONCERNS/FAIL]

Summary:
- Issues found: [critical/major/minor counts]
- Code improvements: [made directly/fixes needed]
- Status recommendation: [Ready for Done/Changes Required]

Do you want to:
1. [ ] Accept gate decision and update story status
2. [ ] Request clarification on specific issues
3. [ ] Override gate decision (documented reason required)
4. [ ] Request additional QA work"
```

---

## Process Control & Decision Points

### Critical Decision Gates

#### Gate 1: Enhancement Classification

```
INPUT: User description
OUTPUT: Routing decision
CONDITIONS:
- Single story (< 4 hours) → brownfield-create-story
- Small feature (1-3 stories) → brownfield-create-epic
- Major enhancement → full workflow
- No codebase access → HALT
```

#### Gate 2: Documentation Assessment

```
INPUT: Existing documentation quality
OUTPUT: Analysis requirement
CONDITIONS:
- Adequate docs → skip document-project
- Inadequate docs → run document-project
- No docs → run document-project
```

#### Gate 3: Architecture Decision

```
INPUT: PRD requirements
OUTPUT: Architecture document requirement
CONDITIONS:
- New patterns/tech → create architecture
- Following existing → skip architecture
- Unclear requirements → halt for clarification
```

#### Gate 4: PO Validation

```
INPUT: All planning documents
OUTPUT: Validation status
CONDITIONS:
- All checklists pass → proceed to sharding
- Minor issues → fix and revalidate
- Major issues → revise documents
```

#### Gate 5: QA Gate

```
INPUT: Implementation + assessments
OUTPUT: Release decision
CONDITIONS:
- All high-severity issues fixed → PASS
- Some issues remain → CONCERNS/WAIVED
- Critical issues remain → FAIL
```

### Process Metrics & KPIs

#### Cycle Time Metrics

- **Classification**: < 5 minutes
- **Planning Phase**: < 2 hours
- **PO Validation**: < 30 minutes
- **Story Creation**: < 30 minutes
- **Implementation**: < 4 hours (per story)
- **QA Review**: < 2 hours

#### Quality Metrics

- **Checklist Compliance**: > 90%
- **Rework Rate**: < 15%
- **Gate Pass Rate**: > 80%
- **Defect Density**: < 0.5 per story
- **Requirements Coverage**: > 95%

#### Process Efficiency Metrics

- **Agent Utilization**: > 80%
- **Artefact Reuse**: > 70%
- **Automation Coverage**: > 60%
- **Context Switching**: < 20% of time

---

## Error Handling & Exception Paths

### Exception: No Codebase Access

```
CONDITION: User cannot provide codebase access
ACTION: HALT workflow
MESSAGE: "Cannot proceed without codebase access for brownfield work"
ALTERNATIVE: Suggest greenfield approach or provide access
```

### Exception: Unclear Requirements

```
CONDITION: PRD requirements ambiguous or incomplete
ACTION: Halt and request clarification
QUESTIONS:
- What specific user problem are we solving?
- What does success look like?
- What are the acceptance criteria?
```

### Exception: Technical Impossibility

```
CONDITION: Requirements technically infeasible
ACTION: Halt and provide alternatives
OPTIONS:
- Reduce scope to MVP
- Change technical approach
- Split into multiple phases
```

### Exception: High Risk Identified

```
CONDITION: Risk assessment shows critical risks
ACTION: Halt for risk mitigation planning
REQUIREMENTS:
- Mitigation strategies
- Alternative approaches
- Risk acceptance documentation
```

---

## Success Criteria & Completion

### Story-Level Success

- [ ] All acceptance criteria met
- [ ] Code follows project standards
- [ ] Tests pass at required levels
- [ ] QA gate passed
- [ ] Documentation updated
- [ ] File List complete and accurate

### Epic-Level Success

- [ ] All stories completed
- [ ] Integration testing passed
- [ ] Performance requirements met
- [ ] No regression in existing functionality
- [ ] User acceptance obtained

### Project-Level Success

- [ ] All epics delivered
- [ ] Business objectives achieved
- [ ] Quality standards maintained
- [ ] Documentation complete
- [ ] Team satisfaction measured

---

*This granular process model provides explicit instructions for each agent at every step, with structured elicitation, conditional logic, artefact binding, and validation loops to ensure consistent, high-quality execution of the BMAD framework.*

