# Integration Patterns

## CrewAI to BMAD Agent Communication
```python
# Example integration pattern
from crewai import Crew, Task, Agent
from bmad_agents import ProductManager, SystemArchitect

# Initialize CrewAI crew
crew = Crew(
    agents=[
        Agent(
            role="Product Manager",
            goal="Create comprehensive product requirements",
            backstory="Expert in product strategy and requirements gathering",
            tools=[ProductManager()]
        ),
        Agent(
            role="System Architect",
            goal="Design scalable system architecture",
            backstory="Expert in system design and technical architecture",
            tools=[SystemArchitect()]
        )
    ]
)

# Load BMAD workflow
workflow = load_bmad_workflow('greenfield-fullstack.yaml')

# Execute workflow
result = crew.kickoff(workflow)
```

## Artefact Writing Pattern
```python
# Example artefact writing
from bmad_crewai import BmadArtefactWriter

writer = BmadArtefactWriter()

# Write PRD artefact
writer.write_artefact(
    content=prd_content,
    artefact_type='prd',
    filename='prd.md'
)

# Write story artefact
writer.write_artefact(
    content=story_content,
    artefact_type='stories',
    filename='1.1-user-authentication.md'
)
```
