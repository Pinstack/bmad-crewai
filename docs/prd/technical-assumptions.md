# Technical Assumptions

## Repository Structure: Monorepo
The BMAD CrewAI Integration uses a monorepo structure to maintain tight coupling between the CrewAI orchestration layer and BMAD framework components.

## Service Architecture: Serverless
CrewAI agents run as serverless functions with the BMAD framework providing the execution context and artefact management.

## Testing Requirements: Unit + Integration
Comprehensive testing strategy combining unit tests for individual components with integration tests for CrewAI-BMAD interactions.

## Additional Technical Assumptions and Requests

### Single-Source Contract Implementation
- All BMAD templates stored in `.bmad-core/templates/` directory
- CrewAI reads templates at runtime without modification
- Artefact output follows BMAD folder structure conventions
- Configuration managed through `.bmad-core/core-config.yaml`

### Tool Use Capabilities
- CrewAI agents require tool execution capabilities for development tasks
- File operations (read, write, modify, search) essential for artefact generation
- Terminal command execution for build and deployment operations
- Git integration for version control and collaboration workflows

### Quality Gate Integration
- Built-in validation using BMAD checklists and gate rules
- Real-time quality monitoring during artefact generation
- Automated feedback loops for quality improvement
- Integration with BMAD's PASS/CONCERNS/FAIL decision framework
