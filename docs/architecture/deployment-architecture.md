# Deployment Architecture

## Local Development
- **Standalone Mode**: CrewAI orchestrates BMAD agents locally
- **File System Access**: Direct access to BMAD folder structure
- **Template Loading**: Load templates from local .bmad-core directory
- **Artefact Storage**: Write to local docs/, stories/, qa/ directories

## Containerized Deployment
- **Docker Integration**: Containerized CrewAI + BMAD environment
- **Volume Mounting**: Mount BMAD folder structure into container
- **Template Access**: Access to .bmad-core/templates via volume mount
- **Artefact Persistence**: Persistent volume for generated artefacts

## Local Development Integration
- **File System API**: Direct file system access for artefact generation
- **Local Storage**: Local file system storage for generated artefacts
- **Template Management**: Local template storage and validation
- **Process Monitoring**: Local workflow execution monitoring and logging
