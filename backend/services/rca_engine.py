from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

from config import settings
from schemas import RootCause


HEURISTIC_RULES = {
    "NullReferenceException": RootCause(
        category="NullReference",
        title="Null Reference Exception",
        description="A variable or argument was used before being initialized or returned a null value.",
        severity="high",
        confidence=0.85,
        suggested_fix="Add a null check before using the variable. Initialize variables with default values in the workflow arguments.",
        preventive_recommendations=[
            "Always initialize variables before use",
            "Use 'Is Nothing' checks for variables that may be null",
            "Add Try-Catch blocks around activities that may produce null values",
        ],
    ),
    "SelectorNotFoundException": RootCause(
        category="SelectorFailure",
        title="UI Element Selector Not Found",
        description="The automation could not locate the UI element with the specified selector.",
        severity="high",
        confidence=0.90,
        suggested_fix="Update the selector to be more dynamic (use wildcards for volatile attributes like idx, title). Enable Selector Validation.",
        preventive_recommendations=[
            "Use dynamic selectors with wildcards",
            "Test selectors in UiExplorer before deploying",
            "Add retry scope with delay before selector activities",
            "Use Computer Vision or Image-based fallbacks",
        ],
    ),
    "TimeoutException": RootCause(
        category="Timeout",
        title="Activity Timeout Exceeded",
        description="An activity exceeded its configured timeout duration.",
        severity="medium",
        confidence=0.80,
        suggested_fix="Increase the timeout value for the failing activity. Add a Retry Scope to handle transient delays.",
        preventive_recommendations=[
            "Set appropriate timeout values based on system performance",
            "Implement retry logic for time-sensitive activities",
            "Monitor system performance to detect slowdowns",
        ],
    ),
    "MissingPackageException": RootCause(
        category="MissingPackage",
        title="Missing Dependency Package",
        description="A required NuGet/activity package is not installed or has version conflicts.",
        severity="critical",
        confidence=0.92,
        suggested_fix="Ensure all packages listed in project.json dependencies are installed in the Robot environment. Run Package Manager to restore dependencies.",
        preventive_recommendations=[
            "Always deploy dependencies along with the project",
            "Pin package versions in project.json",
            "Test in target environment before production deployment",
        ],
    ),
    "FileNotFoundException": RootCause(
        category="FileNotFound",
        title="File or Folder Not Found",
        description="The automation attempted to access a file or directory that does not exist.",
        severity="medium",
        confidence=0.88,
        suggested_fix="Verify the file path is correct and the file exists. Use relative paths or configurable assets instead of hardcoded paths.",
        preventive_recommendations=[
            "Use Assets or Config files for file paths instead of hardcoded values",
            "Add file existence checks before file operations",
            "Ensure network paths are accessible from the Robot machine",
        ],
    ),
    "ArgumentException": RootCause(
        category="MissingArgument",
        title="Invalid or Missing Argument",
        description="A required workflow argument was not provided or has an invalid value.",
        severity="high",
        confidence=0.85,
        suggested_fix="Check that all required In/In-Out arguments are passed when invoking the workflow. Validate argument values before passing.",
        preventive_recommendations=[
            "Document all required arguments",
            "Add argument validation at the start of each workflow",
            "Use default values for optional arguments",
        ],
    ),
    "InvalidCredentialException": RootCause(
        category="CredentialIssue",
        title="Credential or Authentication Failure",
        description="The automation failed to authenticate due to invalid or expired credentials.",
        severity="critical",
        confidence=0.90,
        suggested_fix="Refresh credentials in UiPath Orchestrator Assets or Credential Manager. Ensure the Robot service account has proper permissions.",
        preventive_recommendations=[
            "Store credentials in Orchestrator Assets, not hardcoded",
            "Set up credential rotation alerts",
            "Use service accounts with appropriate permissions",
        ],
    ),
    "NetworkException": RootCause(
        category="NetworkOrAPIFailure",
        title="Network or API Failure",
        description="The automation could not reach a network resource, API endpoint, or web service.",
        severity="high",
        confidence=0.82,
        suggested_fix="Verify the API endpoint URL is correct and the service is available. Check firewall rules and network connectivity from the Robot machine.",
        preventive_recommendations=[
            "Implement retry logic for transient network errors",
            "Add circuit breaker patterns for external API calls",
            "Monitor API health and set up alerting",
        ],
    ),
    "QueueException": RootCause(
        category="QueueFailure",
        title="Queue Transaction Failure",
        description="The automation failed while processing an Orchestrator queue transaction.",
        severity="medium",
        confidence=0.83,
        suggested_fix="Review the queue item data for validation errors. Implement proper exception handling to set correct transaction status (Failed/Rejected).",
        preventive_recommendations=[
            "Validate queue item data before processing",
            "Implement business and application exception handling",
            "Set up retry policies on the Orchestrator queue",
        ],
    ),
    "ConfigurationException": RootCause(
        category="ConfigurationIssue",
        title="Configuration or Asset Not Found",
        description="A required configuration value, Orchestrator asset, or environment variable is missing.",
        severity="high",
        confidence=0.87,
        suggested_fix="Ensure all assets referenced in the project are created in Orchestrator. Verify the Config.xlsx or config file contains all required keys.",
        preventive_recommendations=[
            "Use a centralized config file (Config.xlsx REFramework pattern)",
            "Validate all configuration values at startup",
            "Document all required assets and environment variables",
        ],
    ),
    "BusinessRuleException": RootCause(
        category="BusinessRuleException",
        title="Business Rule Violation",
        description="The automation encountered a business logic condition that could not be processed.",
        severity="medium",
        confidence=0.78,
        suggested_fix="Review the business rule that was violated. Ensure input data meets the expected business criteria.",
        preventive_recommendations=[
            "Add pre-validation steps for input data",
            "Implement proper Business Exception handling in REFramework",
            "Log business exceptions separately for business team review",
        ],
    ),
}


@dataclass
class RCAResult:
    root_causes: list[RootCause] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    ai_used: bool = False
    raw_ai_response: str | None = None


class RCAEngine:
    """AI-powered Root Cause Analysis engine."""

    async def analyze(
        self,
        project: Any,
        log_files: list[Any],
        pasted_error_text: str | None = None,
    ) -> RCAResult:
        # Compile context
        project_info = self._build_project_info(project)
        exception_data = self._collect_exceptions(log_files)

        # If user pasted error text, parse it as an additional exception source
        if pasted_error_text and pasted_error_text.strip():
            pasted_exceptions = self._parse_pasted_error(pasted_error_text)
            exception_data = pasted_exceptions + exception_data

        # Step 1: Heuristic analysis (always runs)
        heuristic_causes = self._heuristic_analysis(exception_data, project_info)

        # Step 2: AI analysis (if API key configured)
        ai_causes: list[RootCause] = []
        raw_response = None
        ai_used = False

        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            try:
                ai_causes, raw_response = await self._ai_analysis(project_info, exception_data, heuristic_causes)
                ai_used = True
            except Exception as e:
                raw_response = f"AI analysis failed: {str(e)}"

        # Merge results (AI causes take precedence, heuristics fill gaps)
        final_causes = self._merge_causes(ai_causes, heuristic_causes)

        # Build recommendations
        recommendations = self._build_recommendations(final_causes, project_info)

        # Calculate overall confidence
        overall_conf = (
            sum(c.confidence for c in final_causes) / len(final_causes)
            if final_causes else 0.0
        )

        return RCAResult(
            root_causes=final_causes,
            recommendations=recommendations,
            overall_confidence=round(overall_conf, 2),
            ai_used=ai_used,
            raw_ai_response=raw_response,
        )

    def _parse_pasted_error(self, text: str) -> list[dict]:
        """Convert free-form pasted error/stack text into exception dicts."""
        exceptions = []
        lines = text.strip().splitlines()

        # Try to extract exception type from lines like "System.NullReferenceException: ..."
        exc_pattern = re.compile(r"([A-Z][a-zA-Z]+Exception|Error)[:\s]*(.*)", re.IGNORECASE)
        current_exc: dict | None = None

        for line in lines[:200]:
            m = exc_pattern.search(line)
            if m:
                if current_exc:
                    exceptions.append(current_exc)
                current_exc = {
                    "type": m.group(1),
                    "message": m.group(2).strip()[:500] or line.strip()[:500],
                    "stack_trace": line,
                    "source": "pasted_error",
                }
            elif current_exc and line.strip().startswith("at "):
                current_exc["stack_trace"] = (current_exc.get("stack_trace", "") + "\n" + line)[:1000]

        if current_exc:
            exceptions.append(current_exc)

        # Fallback: treat whole text as one exception message if nothing matched
        if not exceptions:
            exceptions.append({
                "type": "UnknownError",
                "message": text[:1000],
                "source": "pasted_error",
            })

        return exceptions

    def _build_project_info(self, project: Any) -> dict:
        return {
            "name": project.name,
            "platform": str(project.platform.value if hasattr(project.platform, "value") else project.platform),
            "metadata": project.project_metadata or {},
            "dependencies": project.dependencies or {},
            "workflow_count": len((project.workflow_structure or {}).get("workflows", [])),
        }

    def _collect_exceptions(self, log_files: list[Any]) -> list[dict]:
        exceptions = []
        for lf in log_files:
            summary = lf.exception_summary or {}
            primary = summary.get("primary_exception")
            if primary:
                exceptions.append(primary)
            trace = (lf.execution_trace or {}).get("trace", [])
            for entry in trace[:20]:
                if entry.get("is_error") and entry.get("message"):
                    exceptions.append({
                        "type": "UnknownError",
                        "message": entry["message"],
                        "timestamp": entry.get("timestamp"),
                        "workflow": entry.get("workflow"),
                    })
        return exceptions

    def _heuristic_analysis(self, exceptions: list[dict], project_info: dict) -> list[RootCause]:
        found: list[RootCause] = []
        seen_categories: set[str] = set()

        for exc in exceptions:
            exc_type = exc.get("type", "")
            exc_message = exc.get("message", "")

            # Match against heuristic rules
            for key, rule in HEURISTIC_RULES.items():
                if key.lower() in exc_type.lower() or key.lower() in exc_message.lower():
                    if rule.category not in seen_categories:
                        cause = rule.model_copy()
                        cause.evidence = [
                            f"Exception: {exc_type}",
                            f"Message: {exc_message[:300]}",
                        ]
                        cause.affected_workflow = exc.get("workflow")
                        cause.affected_activity = exc.get("activity")
                        found.append(cause)
                        seen_categories.add(rule.category)
                    break

        # Platform-specific checks
        if project_info["platform"] == "uipath":
            deps = project_info.get("dependencies", {})
            packages = [p.get("name", "") for p in deps.get("packages", [])]
            if not any("UiPath.System.Activities" in p for p in packages):
                found.append(RootCause(
                    category="MissingPackage",
                    title="Core UiPath Package Missing",
                    description="UiPath.System.Activities package was not found in project dependencies.",
                    severity="critical",
                    confidence=0.95,
                    evidence=["project.json dependencies missing UiPath.System.Activities"],
                    suggested_fix="Add UiPath.System.Activities to project dependencies via Package Manager.",
                ))

        return found

    async def _ai_analysis(
        self,
        project_info: dict,
        exceptions: list[dict],
        heuristic_causes: list[RootCause],
    ) -> tuple[list[RootCause], str]:
        from openai import AsyncOpenAI
        from tenacity import retry, stop_after_attempt, wait_exponential

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        heuristic_summary = "\n".join(f"- {c.title}: {c.description}" for c in heuristic_causes)
        exceptions_text = json.dumps(exceptions[:10], indent=2, default=str)
        project_text = json.dumps({k: v for k, v in project_info.items() if k != "workflow_structure"}, indent=2, default=str)

        prompt = f"""You are an RPA automation expert specializing in root cause analysis.

Analyze the following automation project and exception data, then provide a structured RCA.

PROJECT INFORMATION:
{project_text}

EXCEPTIONS DETECTED:
{exceptions_text}

INITIAL HEURISTIC FINDINGS:
{heuristic_summary if heuristic_summary else 'None detected'}

Provide a JSON response with this exact structure:
{{
  "root_causes": [
    {{
      "category": "string (one of: NullReference, SelectorFailure, Timeout, MissingPackage, FileNotFound, MissingArgument, CredentialIssue, NetworkOrAPIFailure, QueueFailure, ConfigurationIssue, BusinessRuleException, UnhandledException)",
      "title": "string (concise title)",
      "description": "string (detailed explanation of what failed and why)",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "evidence": ["list of evidence strings from the log/project data"],
      "affected_workflow": "string or null",
      "affected_activity": "string or null",
      "suggested_fix": "string (specific actionable fix)",
      "preventive_recommendations": ["list of preventive measures"]
    }}
  ],
  "summary": "string (executive summary of what happened, where, and why)"
}}

Focus on the most likely root causes. Be specific and actionable."""

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
        async def _call():
            return await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
            )

        response = await _call()
        raw_text = response.choices[0].message.content or "{}"

        data = json.loads(raw_text)
        causes = []
        for rc_data in data.get("root_causes", []):
            try:
                causes.append(RootCause(**rc_data))
            except Exception:
                pass

        return causes, raw_text

    def _merge_causes(self, ai_causes: list[RootCause], heuristic_causes: list[RootCause]) -> list[RootCause]:
        if not ai_causes:
            return heuristic_causes

        merged = list(ai_causes)
        ai_categories = {c.category for c in ai_causes}

        for hc in heuristic_causes:
            if hc.category not in ai_categories:
                merged.append(hc)

        # Sort by severity then confidence
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        merged.sort(key=lambda c: (severity_order.get(c.severity, 4), -c.confidence))
        return merged[:10]

    def _build_recommendations(self, causes: list[RootCause], project_info: dict) -> list[str]:
        recs = []
        for cause in causes:
            if cause.suggested_fix:
                recs.append(f"[{cause.severity.upper()}] {cause.title}: {cause.suggested_fix}")

        # General best practices
        platform = project_info.get("platform", "")
        if platform == "uipath":
            recs.extend([
                "Implement REFramework for production-grade RPA projects",
                "Enable detailed logging in Robot settings",
                "Use Orchestrator Assets for all configurable values",
                "Set up email/Teams alerts for unhandled exceptions",
            ])
        elif platform == "power_automate":
            recs.extend([
                "Use error handling actions in every cloud flow",
                "Enable flow run history and monitoring",
                "Use environment variables instead of hardcoded values",
            ])

        return list(dict.fromkeys(recs))  # deduplicate preserving order
