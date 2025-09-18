"""Main BMAD CrewAI integration orchestrator."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import yaml

from .agent_registry import AgentRegistry
from .agent_wrappers import BmadAgentRegistry
from .api_client import APIClient, APIError, RateLimiter, RateLimitError
from .artefact_manager import ArtefactManager
from .artefact_writer import BMADArtefactWriter
from .checklist_executor import ChecklistExecutor
from .config import APIConfig, ConfigManager

# CrewAI Orchestration Components
from .crewai_engine import CrewAIOrchestrationEngine
from .development_tester import DevelopmentTester
from .error_handler import BmadErrorHandler
from .exceptions import TemplateError
from .quality_gate_manager import QualityGateManager
from .template_manager import TemplateInfo, TemplateManager
from .workflow_manager import BmadWorkflowManager

logger = logging.getLogger(__name__)


class BmadCrewAI:
    """Main BMAD CrewAI integration class."""

    def __init__(self, config_file: Optional[str] = None):
        # Initialize logger first
        self.logger = logging.getLogger(__name__)

        self.config_manager = ConfigManager(config_file)
        self.rate_limiter = RateLimiter()
        self.api_clients: Dict[str, APIClient] = {}
        self.templates: Dict[str, TemplateInfo] = {}

        # Initialize managers
        self.agent_registry = AgentRegistry()
        self.artefact_manager = ArtefactManager()
        self.development_tester = DevelopmentTester()
        self.quality_gate_manager = QualityGateManager()
        self.template_manager = TemplateManager()

        # Initialize CrewAI orchestration components
        self.crewai_engine = CrewAIOrchestrationEngine(self.logger)
        self.bmad_agent_registry = BmadAgentRegistry(self.logger)
        self.workflow_manager = BmadWorkflowManager(self.crewai_engine, self.logger)
        self.error_handler = BmadErrorHandler(self.logger)

        # Legacy attributes for backward compatibility
        self.artefact_writer = self.artefact_manager.artefact_writer
        self.checklist_executor = self.quality_gate_manager.checklist_executor
        self.bmad_agents = self.agent_registry.bmad_agents
        self.crew = self.agent_registry.crew

        # Configure logging
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging configuration."""
        log_config = self.config_manager._config["logging"]
        logging.basicConfig(
            level=getattr(logging, log_config["level"]), format=log_config["format"]
        )

    def get_api_client(self, provider: str) -> APIClient:
        """Get or create API client for a provider."""
        if provider not in self.api_clients:
            api_config = self.config_manager.get_api_config(provider)

            # Try to get API key from secure storage
            api_key = self.config_manager.get_api_key(provider)
            if api_key:
                api_config.api_key = api_key

            self.api_clients[provider] = APIClient(api_config)

        return self.api_clients[provider]

    async def make_api_request(
        self, provider: str, method: str, url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Make API request with rate limiting and error handling."""
        try:
            # Check global rate limit
            api_config = self.config_manager.get_api_config(provider)
            self.rate_limiter.check_rate_limit(
                provider, api_config.rate_limit_requests, api_config.rate_limit_window
            )

            # Get client and make request
            client = self.get_api_client(provider)
            response = await getattr(client, method.lower())(url, **kwargs)

            # Record successful request
            self.rate_limiter.record_request(provider)

            return response

        except RateLimitError as e:
            self.logger.warning(f"Rate limit error for {provider}: {e}")
            # Set backoff if retry_after is provided
            if hasattr(e, "retry_after") and e.retry_after:
                self.rate_limiter.set_backoff(provider, e.retry_after)
            raise
        except APIError as e:
            self.logger.error(f"API error for {provider}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error for {provider}: {e}")
            raise APIError(f"Unexpected error: {str(e)}") from e

    # ===============================
    # Template Management
    # ===============================

    def load_bmad_templates(self) -> Dict[str, TemplateInfo]:
        """Load all BMAD templates from .bmad-core/templates/ directory.

        Returns:
            Dict[str, TemplateInfo]: Dictionary mapping template IDs to template info
        """
        return self.template_manager.load_templates()

    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        """Get a loaded template by ID.

        Args:
            template_id: Template identifier

        Returns:
            TemplateInfo or None: Template information if found
        """
        return self.template_manager.get_template(template_id)

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all loaded templates with basic information.

        Returns:
            Dict[str, Dict[str, Any]]: Template summaries by ID
        """
        return self.template_manager.list_templates()

    def validate_template_dependencies(self, template_id: str) -> bool:
        """Validate that a template's dependencies are satisfied.

        Args:
            template_id: Template identifier to validate

        Returns:
            bool: True if dependencies are satisfied

        Raises:
            TemplateError: If dependencies are not satisfied
        """
        return self.template_manager.validate_template_dependencies(template_id)

    # ===============================
    # BMAD Agent Integration
    # ===============================

    def register_bmad_agents(self) -> bool:
        """Register all BMAD agents with CrewAI.

        Returns:
            bool: True if registration successful
        """
        return self.agent_registry.register_bmad_agents()

    def get_bmad_agent(self, agent_id: str):
        """Get a registered BMAD agent by ID.

        Args:
            agent_id: Agent identifier (e.g., 'scrum-master', 'dev-agent')

        Returns:
            Agent object or None if not found
        """
        return self.agent_registry.get_bmad_agent(agent_id)

    def list_bmad_agents(self):
        """List all registered BMAD agents.

        Returns:
            Dict of agent information
        """
        return self.agent_registry.list_bmad_agents()

    def test_agent_coordination(self):
        """Test agent coordination and crew functionality.

        Returns:
            Dict with coordination test results
        """
        return self.agent_registry.test_agent_coordination()

    # ===============================
    # Artefact Management
    # ===============================

    def write_artefact(self, artefact_type: str, content: str, **kwargs) -> bool:
        """Write artefact to BMAD folder structure.

        Args:
            artefact_type: Type of artefact ('prd', 'story', 'gate', 'assessment', 'epic')
            content: Artefact content
            **kwargs: Additional parameters for specific artefact types

        Returns:
            bool: True if successful
        """
        return self.artefact_manager.write_artefact(artefact_type, content, **kwargs)

    def test_artefact_generation(self) -> Dict[str, Any]:
        """Test artefact generation functionality.

        Returns:
            Dict with artefact generation test results
        """
        return self.artefact_manager.test_artefact_generation()

    # ===============================
    # Development Environment Testing
    # ===============================

    def test_development_environment(self):
        """Test development environment configuration and capabilities.

        Returns:
            Dict with environment test results
        """
        return self.development_tester.test_development_environment()

    # ===============================
    # Quality Gates & Checklists
    # ===============================

    def test_quality_gates(self):
        """Test quality gate and checklist execution framework.

        Returns:
            Dict with quality gate test results
        """
        return self.quality_gate_manager.test_quality_gates()

    def execute_checklist(
        self, checklist_id: str, context: Optional[Dict[str, Any]] = None
    ):
        """Execute a quality checklist.

        Args:
            checklist_id: ID of checklist to execute
            context: Optional context data for validation

        Returns:
            Dict with execution results
        """
        return self.quality_gate_manager.execute_checklist(checklist_id, context)

    def validate_gate(self, checklist_id: str, gate_type: str = "story"):
        """Validate a quality gate using a checklist.

        Args:
            checklist_id: Checklist to use for validation
            gate_type: Type of gate ('story', 'epic', 'sprint')

        Returns:
            Dict with gate validation results
        """
        return self.quality_gate_manager.validate_gate(checklist_id, gate_type)

    def list_available_checklists(self):
        """List all available checklists for quality gates.

        Returns:
            Dict with checklist information
        """
        return self.quality_gate_manager.list_available_checklists()

    def get_checklist_details(self, checklist_id: str):
        """Get detailed information about a specific checklist.

        Args:
            checklist_id: ID of checklist to retrieve

        Returns:
            Dict with checklist details or None if not found
        """
        return self.quality_gate_manager.get_checklist_details(checklist_id)

    def validate_gate_with_feedback(
        self,
        checklist_id: str,
        gate_type: str = "story",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Enhanced gate validation with comprehensive actionable feedback.

        Args:
            checklist_id: Checklist to use for validation
            gate_type: Type of gate ('story', 'epic', 'sprint', 'release')
            context: Optional context data including artefact content

        Returns:
            Dict with gate validation results and actionable feedback
        """
        try:
            # Use the enhanced validation framework
            gate_results = self.quality_gate_manager.validate_gate_with_decision(
                checklist_id, gate_type, context
            )

            # Add workflow integration feedback
            gate_results["workflow_integration"] = self._generate_workflow_feedback(
                gate_results
            )

            self.logger.info(
                f"Enhanced gate validation completed: {gate_results.get('decision', 'UNKNOWN')} "
                f"with actionable feedback"
            )

            return gate_results

        except Exception as e:
            self.logger.error(f"Enhanced gate validation with feedback failed: {e}")
            return {"error": str(e)}

    def _generate_workflow_feedback(
        self, gate_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate workflow-specific feedback based on gate results.

        Args:
            gate_results: Complete gate validation results

        Returns:
            Workflow integration feedback
        """
        decision = gate_results.get("decision", "UNKNOWN")
        gate_type = gate_results.get("gate_type", "unknown")
        feedback = {
            "can_proceed": decision in ["PASS", "CONCERNS"],
            "blocking_issues": decision == "FAIL",
            "next_workflow_steps": [],
            "team_notifications": [],
            "escalation_required": False,
            "escalation_reason": None,
        }

        # Determine next workflow steps based on decision and gate type
        if decision == "PASS":
            feedback["next_workflow_steps"] = self._get_pass_workflow_steps(gate_type)
        elif decision == "CONCERNS":
            feedback["next_workflow_steps"] = self._get_concerns_workflow_steps(
                gate_type
            )
            feedback["team_notifications"] = self._get_concerns_notifications(
                gate_results
            )
        elif decision == "FAIL":
            feedback["next_workflow_steps"] = self._get_fail_workflow_steps(gate_type)
            feedback["escalation_required"] = True
            feedback["escalation_reason"] = (
                "Quality gate failed - critical issues must be addressed"
            )

        # Add team notifications for critical issues
        critical_issues = gate_results.get("critical_issues", [])
        if critical_issues:
            feedback["team_notifications"].extend(
                self._generate_critical_issue_notifications(critical_issues, gate_type)
            )

        return feedback

    def _get_pass_workflow_steps(self, gate_type: str) -> List[str]:
        """Get workflow steps when gate passes."""
        steps = {
            "story": [
                "Proceed to development implementation",
                "Update sprint board with story status",
                "Schedule testing when development complete",
            ],
            "epic": [
                "Release epic for story development",
                "Update product roadmap progress",
                "Communicate readiness to development team",
            ],
            "sprint": [
                "Proceed with sprint execution",
                "Monitor velocity and quality metrics",
                "Schedule sprint review and retrospective",
            ],
            "release": [
                "Proceed with deployment preparation",
                "Schedule release validation testing",
                "Notify stakeholders of release readiness",
            ],
        }
        return steps.get(gate_type, ["Proceed to next workflow phase"])

    def _get_concerns_workflow_steps(self, gate_type: str) -> List[str]:
        """Get workflow steps when gate passes with concerns."""
        steps = {
            "story": [
                "Document identified concerns for development awareness",
                "Proceed with development but track concerns",
                "Schedule additional review after implementation",
            ],
            "epic": [
                "Document concerns in epic description",
                "Proceed but allocate time for concern resolution",
                "Schedule follow-up quality check",
            ],
            "sprint": [
                "Document sprint concerns for visibility",
                "Proceed but monitor impact on deliverables",
                "Address concerns in sprint retrospective",
            ],
            "release": [
                "Document release concerns and mitigation plan",
                "Proceed with caution and additional monitoring",
                "Schedule post-release quality assessment",
            ],
        }
        return steps.get(gate_type, ["Document concerns and proceed with caution"])

    def _get_fail_workflow_steps(self, gate_type: str) -> List[str]:
        """Get workflow steps when gate fails."""
        steps = {
            "story": [
                "STOP: Address critical issues before development",
                "Re-work story based on quality feedback",
                "Re-submit for quality gate validation",
            ],
            "epic": [
                "STOP: Epic cannot proceed until critical issues resolved",
                "Review and revise epic requirements",
                "Re-submit epic for quality validation",
            ],
            "sprint": [
                "STOP: Sprint quality unacceptable",
                "Address critical quality issues immediately",
                "Re-plan sprint with quality improvements",
            ],
            "release": [
                "STOP: Release blocked by quality issues",
                "Address critical release-blocking issues",
                "Re-schedule release after quality remediation",
            ],
        }
        return steps.get(
            gate_type, ["STOP: Address critical quality issues before proceeding"]
        )

    def _get_concerns_notifications(
        self, gate_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate team notifications for concerns."""
        notifications = []

        # Notify development team about concerns
        notifications.append(
            {
                "audience": "development_team",
                "priority": "medium",
                "message": "Quality concerns identified - review feedback before implementation",
                "action_required": "Review assessment report and address concerns where applicable",
            }
        )

        # Notify product owner about tracking needs
        notifications.append(
            {
                "audience": "product_owner",
                "priority": "medium",
                "message": "Quality concerns require tracking and follow-up",
                "action_required": "Ensure concerns are documented and tracked to resolution",
            }
        )

        return notifications

    def _generate_critical_issue_notifications(
        self, critical_issues: List[Dict[str, Any]], gate_type: str
    ) -> List[Dict[str, Any]]:
        """Generate notifications for critical issues."""
        notifications = []

        # Group issues by severity
        high_severity = [
            issue for issue in critical_issues if issue.get("severity") == "high"
        ]

        if high_severity:
            notifications.append(
                {
                    "audience": "quality_team",
                    "priority": "high",
                    "message": f"Critical quality issues found in {gate_type} - immediate attention required",
                    "action_required": "Review and address all high-severity issues before proceeding",
                    "issue_count": len(high_severity),
                }
            )

        # Notify responsible team
        responsible_team = (
            "development_team" if gate_type == "story" else "product_team"
        )
        notifications.append(
            {
                "audience": responsible_team,
                "priority": "high",
                "message": f"Quality validation identified {len(critical_issues)} critical issues in {gate_type}",
                "action_required": "Review assessment report and implement remediation plan",
            }
        )

        return notifications

    def get_actionable_quality_feedback(
        self, gate_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get comprehensive actionable feedback from quality gate results.

        Args:
            gate_results: Results from quality gate validation

        Returns:
            Structured actionable feedback for teams
        """
        feedback = {
            "executive_summary": self._create_feedback_executive_summary(gate_results),
            "immediate_actions": self._extract_immediate_actions(gate_results),
            "team_responsibilities": self._assign_team_responsibilities(gate_results),
            "timeline_expectations": self._establish_timeline_expectations(
                gate_results
            ),
            "success_criteria": self._define_success_criteria(gate_results),
            "communication_plan": self._create_communication_plan(gate_results),
        }

        return feedback

    def _create_feedback_executive_summary(self, gate_results: Dict[str, Any]) -> str:
        """Create executive summary of quality feedback."""
        decision = gate_results.get("decision", "UNKNOWN")
        gate_type = gate_results.get("gate_type", "unknown")
        confidence = gate_results.get("confidence", 0)

        summary = f"Quality Gate Result: {decision} for {gate_type} "
        summary += f"(confidence: {confidence:.1f}). "

        if decision == "PASS":
            summary += "Ready to proceed with development."
        elif decision == "CONCERNS":
            summary += "Can proceed but requires attention to identified concerns."
        else:
            summary += "Blocked - critical issues must be resolved before proceeding."

        return summary

    def _extract_immediate_actions(
        self, gate_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract immediate actions from gate results."""
        actions = []
        decision = gate_results.get("decision", "UNKNOWN")

        # Add decision-based immediate actions
        if decision == "FAIL":
            actions.append(
                {
                    "action": "STOP all work on this item",
                    "priority": "critical",
                    "timeframe": "immediate",
                    "owner": "all_teams",
                }
            )

        # Add actions from assessment report
        assessment_report = gate_results.get("assessment_report", {})
        recommendations = assessment_report.get("recommendations", {})
        immediate_actions = recommendations.get("immediate_actions", [])

        actions.extend(immediate_actions)

        return actions

    def _assign_team_responsibilities(
        self, gate_results: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Assign responsibilities to different teams based on gate results."""
        responsibilities = {
            "development_team": [],
            "product_team": [],
            "quality_team": [],
            "management": [],
        }

        decision = gate_results.get("decision", "UNKNOWN")
        gate_type = gate_results.get("gate_type", "unknown")

        # Base responsibilities by decision
        if decision == "FAIL":
            responsibilities["development_team"].append(
                "Address all critical technical issues"
            )
            responsibilities["product_team"].append(
                "Review and revise requirements if needed"
            )
            responsibilities["quality_team"].append(
                "Provide detailed remediation guidance"
            )
            responsibilities["management"].append(
                "Escalate blocking issues and resource needs"
            )

        elif decision == "CONCERNS":
            responsibilities["development_team"].append(
                "Review concerns and plan mitigation"
            )
            responsibilities["product_team"].append("Track concerns to resolution")
            responsibilities["quality_team"].append(
                "Monitor concern resolution progress"
            )

        # Add gate-type specific responsibilities
        if gate_type == "story":
            responsibilities["development_team"].append(
                "Implement story with quality considerations"
            )
        elif gate_type == "epic":
            responsibilities["product_team"].append(
                "Ensure epic scope accounts for quality requirements"
            )
        elif gate_type == "sprint":
            responsibilities["management"].append("Address sprint-level quality trends")
        elif gate_type == "release":
            responsibilities["management"].append(
                "Make release decision considering quality status"
            )

        return responsibilities

    def _establish_timeline_expectations(
        self, gate_results: Dict[str, Any]
    ) -> Dict[str, str]:
        """Establish timeline expectations for quality remediation."""
        timelines = {}
        decision = gate_results.get("decision", "UNKNOWN")

        if decision == "PASS":
            timelines["next_steps"] = "Proceed immediately"
            timelines["monitoring"] = "Standard quality monitoring during development"
        elif decision == "CONCERNS":
            timelines["concern_resolution"] = "Within current sprint/iteration"
            timelines["follow_up_review"] = "After implementation completion"
        elif decision == "FAIL":
            timelines["critical_fixes"] = "Immediate - before any further work"
            timelines["re_validation"] = "Within 24 hours after fixes"
            timelines["maximum_resolution_time"] = "No more than 3 business days"

        return timelines

    def _define_success_criteria(self, gate_results: Dict[str, Any]) -> List[str]:
        """Define success criteria for quality remediation."""
        criteria = []
        decision = gate_results.get("decision", "UNKNOWN")

        # Base success criteria
        criteria.append("All identified critical issues resolved")
        criteria.append("Re-validation passes quality gate")
        criteria.append("Team agreement on resolution adequacy")

        if decision == "CONCERNS":
            criteria.append("Concern mitigation plan documented and approved")
            criteria.append("Risks of proceeding with concerns understood and accepted")

        return criteria

    def _create_communication_plan(
        self, gate_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create communication plan for quality gate results."""
        communications = []

        decision = gate_results.get("decision", "UNKNOWN")
        gate_type = gate_results.get("gate_type", "unknown")

        # Immediate notifications
        if decision == "FAIL":
            communications.append(
                {
                    "timing": "immediate",
                    "audience": "all_stakeholders",
                    "method": "direct_notification",
                    "message": f"CRITICAL: {gate_type} quality gate FAILED - work stopped",
                }
            )

        # Standard communications
        communications.extend(
            [
                {
                    "timing": "within_1_hour",
                    "audience": "directly_involved_teams",
                    "method": "slack_email",
                    "message": f"Quality gate results for {gate_type}: {decision}",
                },
                {
                    "timing": "daily_standup",
                    "audience": "development_team",
                    "method": "verbal_update",
                    "message": "Quality gate status and any required actions",
                },
            ]
        )

        if decision == "CONCERNS":
            communications.append(
                {
                    "timing": "sprint_planning",
                    "audience": "product_team",
                    "method": "meeting_discussion",
                    "message": "Review quality concerns and mitigation planning",
                }
            )

        return communications

    async def close(self):
        """Close all API clients."""
        for client in self.api_clients.values():
            await client.close()
        self.api_clients.clear()

    @asynccontextmanager
    async def session(self):
        """Context manager for BMAD CrewAI session."""
        try:
            yield self
        finally:
            await self.close()
