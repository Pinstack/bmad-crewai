# Core Architecture Principles

## Orchestration Strategy
- **CrewAI as Primary Orchestrator**: CrewAI serves as the main workflow engine and coordination layer
- **BMAD Template Consumption**: CrewAI reads and interprets BMAD YAML templates to understand workflow requirements
- **Agent Coordination**: CrewAI orchestrates execution of BMAD specialized agents in proper sequence
- **Artefact Management**: All outputs written to BMAD folder structure following framework conventions
- **Process Integrity**: CrewAI maintains BMAD methodology execution flow and enforces quality gates

## Integration Pattern
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     CrewAI      │────│   BMAD Framework│────│   File System   │
│  Orchestrator   │    │                 │    │                 │
│                 │    │ • Templates     │    │ • docs/         │
│ • Workflow      │    │ • Agents        │    │ • stories/      │
│ • Coordination  │    │ • Quality Gates │    │ • qa/           │
│ • Validation    │    │ • Folder Struct │    │ • etc.          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └─Loads BMAD templates   └─Provides agents &   └─Writes artefacts
           from .bmad-core/      patterns               to BMAD folders
```
