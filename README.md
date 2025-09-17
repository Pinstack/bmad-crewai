# BMAD CrewAI Integration

**CrewAI orchestration layer for the BMAD-Method framework**

This package provides a structured integration between CrewAI's multi-agent orchestration capabilities and the BMAD-Method framework. CrewAI acts as the primary orchestrator that reads BMAD templates and coordinates specialized BMAD agents to write artefacts to BMAD-specified folder structures.

## Architecture Overview

- **CrewAI**: Primary orchestration engine that manages workflow execution
- **BMAD Templates**: YAML templates defining agent roles, workflows, and artefact structures
- **BMAD Agents**: Specialized agents (PM, Architect, QA, Dev, PO, SM) with domain expertise
- **Artefact Output**: All outputs written to BMAD folder structure (`docs/`, `stories/`, `qa/`, etc.)

## Key Features

- **Template-Driven Orchestration**: CrewAI reads BMAD YAML templates to understand workflow requirements
- **Agent Coordination**: Seamless coordination between BMAD specialized agents
- **Quality Assurance**: Built-in quality gates and validation checkpoints
- **File System Integration**: Artefacts automatically written to BMAD folder conventions
- **Process Integrity**: Maintains BMAD methodology execution flow
- **Simple Credential Storage**: Environment variables with JSON config fallback
- **Basic API Rate Limiting**: Simple request spacing with retry on rate limits
- **Essential Error Handling**: HTTP status checking with basic error recovery

## Quick Start (MVP)

### Simple Setup
```bash
# Install
pip install -e .

# Set API keys (environment variables)
export API_OPENAI_KEY="your-openai-key"
export API_ANTHROPIC_KEY="your-anthropic-key"

# Test connection
python -m bmad_crewai.simple_cli test
```

### Basic Usage
```python
from bmad_crewai.simple_api import BMADCrewAISimple

async def main():
    bmad = BMADCrewAISimple()

    # Get API client
    client = bmad.get_api_client("openai")

    # Make request with basic rate limiting
    async with client:
        result = await client.make_request("GET", "https://api.openai.com/v1/models")
        print(result)

asyncio.run(main())
```

## Security & API Management

### Simple Credential Storage
- **Environment Variables**: `API_OPENAI_KEY`, `API_ANTHROPIC_KEY`
- **Config File**: Simple JSON storage in `~/.bmad-crewai/config.json`
- **Priority**: Environment variables override config file

### Basic Rate Limiting & Error Handling
- **Simple Rate Limiting**: 1 second delay between requests
- **Basic Error Handling**: HTTP status code checking with simple retry
- **API-Specific Headers**: Automatic header injection for OpenAI/Anthropic
