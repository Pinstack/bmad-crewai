# Component Architecture

## CrewAI Orchestration Layer

### Template Reader
```python
class BmadTemplateReader:
    """Loads and parses BMAD YAML templates"""

    def load_template(self, template_path: str) -> dict:
        """Load BMAD template from .bmad-core/templates/"""
        pass

    def validate_template(self, template: dict) -> bool:
        """Validate template structure and required fields"""
        pass

    def extract_workflow_sequence(self, template: dict) -> list:
        """Extract agent execution sequence from template"""
        pass
```

### Agent Registry
```python
class BmadAgentRegistry:
    """Manages BMAD agent registration with CrewAI"""

    def register_agents(self) -> dict:
        """Register all BMAD agents as CrewAI tools"""
        return {
            'pm': ProductManager(),
            'architect': SystemArchitect(),
            'qa': TestArchitect(),
            'dev': Developer(),
            'po': ProductOwner(),
            'sm': ScrumMaster()
        }

    def get_agent_capabilities(self, agent_id: str) -> list:
        """Get agent capabilities for task assignment"""
        pass
```

### Workflow Engine (Modular Architecture)

The workflow engine has been refactored into multiple specialized components for better maintainability and testability:

```python
class BmadWorkflowEngine:
    """Main workflow orchestration coordinator"""

    def __init__(self, crew: Crew, template_reader: BmadTemplateReader):
        self.crew = crew
        self.template_reader = template_reader
        self.conditional_engine = ConditionalWorkflowEngine()
        self.error_recovery = ErrorRecoveryService()
        self.agent_assigner = DynamicAgentAssigner()
        self.visualizer = WorkflowVisualizer()

    def execute_workflow(self, workflow_template: str):
        """Execute complete BMAD workflow with advanced features"""
        template = self.template_reader.load_template(workflow_template)
        agents = BmadAgentRegistry().register_agents()

        for step in template['workflow_sequence']:
            # Advanced conditional logic
            if not self.conditional_engine.should_execute_step(step, template):
                continue

            # Dynamic agent assignment
            agent = self.agent_assigner.select_optimal_agent(step, agents)

            # Execute with error recovery
            result = self.error_recovery.execute_with_retry(
                agent, step, self.crew
            )

            # Write artefact
            self.write_artefact_to_bmad_folder(result, step['output_path'])

        # Quality gate validation
        self.validate_quality_gates(template['quality_gates'])

class ConditionalWorkflowEngine:
    """Handles complex conditional workflow logic"""

    def should_execute_step(self, step: dict, context: dict) -> bool:
        """Evaluate conditions for step execution"""
        # Implementation of conditional logic
        pass

class ErrorRecoveryService:
    """Manages error recovery and retry mechanisms"""

    def execute_with_retry(self, agent, step: dict, crew: Crew):
        """Execute task with comprehensive error recovery"""
        # Implementation of retry logic and error handling
        pass

class DynamicAgentAssigner:
    """Intelligent agent selection based on context and performance"""

    def select_optimal_agent(self, step: dict, available_agents: dict):
        """Select best agent based on capabilities and load"""
        # Implementation of agent selection logic
        pass
```

### Artefact Writer
```python
class BmadArtefactWriter:
    """Handles writing artefacts to BMAD folder structure"""

    FOLDER_MAPPING = {
        'prd': 'docs/prd.md',
        'architecture': 'docs/architecture.md',
        'stories': 'docs/stories/',
        'qa_assessments': 'docs/qa/assessments/',
        'qa_gates': 'docs/qa/gates/'
    }

    def write_artefact(self, content: str, artefact_type: str, filename: str):
        """Write artefact to appropriate BMAD folder"""
        base_path = self.FOLDER_MAPPING[artefact_type]
        full_path = f"{base_path}/{filename}"

        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write artefact
        with open(full_path, 'w') as f:
            f.write(content)

    def validate_folder_structure(self):
        """Ensure BMAD folder structure exists"""
        for folder in self.FOLDER_MAPPING.values():
            if folder.endswith('/'):
                os.makedirs(folder, exist_ok=True)
```

### Quality Gate Manager
```python
class BmadQualityGateManager:
    """Enforces BMAD quality gates through CrewAI"""

    def __init__(self, crew: Crew):
        self.crew = crew

    def validate_gate(self, gate_definition: dict) -> dict:
        """Execute quality gate validation"""
        # Create validation tasks
        validation_tasks = self.create_validation_tasks(gate_definition)

        # Execute validation
        results = {}
        for task in validation_tasks:
            result = self.crew.execute_task(task['agent'], task['definition'])
            results[task['name']] = self.interpret_validation_result(result)

        return {
            'status': self.determine_overall_status(results),
            'results': results,
            'recommendations': self.generate_recommendations(results)
        }

    def determine_overall_status(self, results: dict) -> str:
        """Determine PASS/CONCERNS/FAIL status"""
        if any(result['severity'] == 'high' for result in results.values()):
            return 'FAIL'
        elif any(result['severity'] == 'medium' for result in results.values()):
            return 'CONCERNS'
        else:
            return 'PASS'
```

## BMAD Framework Layer

### Template System
```yaml
# Example BMAD Template Structure
template_version: "1.0"
workflow_name: "greenfield-fullstack"

agents:
  pm:
    role: "Product Manager"
    capabilities: ["create-prd", "validate-requirements"]
    output_folder: "docs/"

  architect:
    role: "System Architect"
    capabilities: ["create-architecture", "design-system"]
    output_folder: "docs/"

  qa:
    role: "Test Architect"
    capabilities: ["risk-assessment", "test-design", "review"]
    output_folder: "docs/qa/"

workflow_sequence:
  - step: 1
    agent: "pm"
    task: "create-prd"
    template: "prd-tmpl.yaml"
    output_path: "docs/prd.md"
    quality_gate: "document-validation"

  - step: 2
    agent: "architect"
    task: "create-architecture"
    template: "fullstack-architecture-tmpl.yaml"
    output_path: "docs/architecture.md"
    dependencies: [1]
    quality_gate: "architecture-validation"

quality_gates:
  document-validation:
    type: "content-validation"
    criteria: ["completeness", "clarity", "consistency"]

  architecture-validation:
    type: "technical-validation"
    criteria: ["feasibility", "scalability", "security"]
```

### Agent Specializations

#### Product Manager Agent
```python
class ProductManager:
    """BMAD Product Manager specialized agent"""

    def create_prd(self, requirements: dict) -> str:
        """Create Product Requirements Document"""
        # Load PRD template
        template = self.load_template('prd-tmpl.yaml')

        # Generate PRD content
        prd_content = self.generate_prd_content(requirements, template)

        # Return formatted PRD
        return self.format_prd_output(prd_content)

    def validate_requirements(self, prd_content: str) -> dict:
        """Validate PRD against quality criteria"""
        return self.perform_validation_checks(prd_content)
```

#### System Architect Agent
```python
class SystemArchitect:
    """BMAD System Architect specialized agent"""

    def create_architecture(self, prd_content: str) -> str:
        """Create system architecture document"""
        # Analyze PRD requirements
        requirements = self.analyze_prd_requirements(prd_content)

        # Design system architecture
        architecture = self.design_system_architecture(requirements)

        # Generate architecture document
        return self.generate_architecture_document(architecture)

    def validate_technical_feasibility(self, architecture: str) -> dict:
        """Validate technical feasibility"""
        return self.perform_technical_validation(architecture)
```
