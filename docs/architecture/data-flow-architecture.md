# Data Flow Architecture

## Input Processing
1. **Template Loading**: CrewAI loads BMAD YAML templates
2. **Requirement Parsing**: Extract workflow sequence and agent assignments
3. **Context Preparation**: Gather necessary context for agent execution
4. **Validation Setup**: Configure quality gates and validation criteria

## Agent Execution Flow
1. **Agent Selection**: CrewAI selects appropriate BMAD agent for task
2. **Task Execution**: Agent performs specialized task with domain expertise
3. **Output Generation**: Agent produces artefact following BMAD conventions
4. **Quality Validation**: Built-in validation checks artefact quality
5. **Artefact Storage**: Output written to BMAD folder structure

## Output Management
1. **File System Integration**: Artefacts written to correct BMAD folders
2. **Naming Conventions**: Files follow BMAD naming patterns
3. **Metadata Tracking**: Track artefact creation and modification
4. **Version Control**: Integration with git for artefact versioning
