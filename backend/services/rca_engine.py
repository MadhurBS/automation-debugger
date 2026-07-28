from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

from config import settings
from schemas import RootCause


# ── Heuristic rules keyed on exception-type substring ──────────────────────
HEURISTIC_RULES: dict[str, RootCause] = {
    "NullReferenceException": RootCause(
        category="NullReference", title="Null Reference Exception",
        description="A variable or argument was used before being initialised or returned a null value.",
        severity="high", confidence=0.85,
        suggested_fix="Add a null check before using the variable. Initialise variables with default values in workflow arguments.",
        preventive_recommendations=["Always initialise variables before use", "Use 'Is Nothing' checks for variables that may be null", "Add Try-Catch blocks around activities that may produce null values"],
    ),
    "SelectorNotFoundException": RootCause(
        category="SelectorFailure", title="UI Element Selector Not Found",
        description="The automation could not locate the UI element with the specified selector.",
        severity="high", confidence=0.90,
        suggested_fix="Update the selector to be more dynamic (use wildcards for volatile attributes like idx, title). Enable Selector Validation.",
        preventive_recommendations=["Use dynamic selectors with wildcards", "Test selectors in UiExplorer before deploying", "Add retry scope with delay before selector activities"],
    ),
    "TimeoutException": RootCause(
        category="Timeout", title="Activity Timeout Exceeded",
        description="An activity exceeded its configured timeout duration.",
        severity="medium", confidence=0.80,
        suggested_fix="Increase the timeout value for the failing activity. Add a Retry Scope to handle transient delays.",
        preventive_recommendations=["Set appropriate timeout values based on system performance", "Implement retry logic for time-sensitive activities"],
    ),
    "MissingPackageException": RootCause(
        category="MissingPackage", title="Missing Dependency Package",
        description="A required NuGet/activity package is not installed or has version conflicts.",
        severity="critical", confidence=0.92,
        suggested_fix="Ensure all packages listed in project.json dependencies are installed in the Robot environment.",
        preventive_recommendations=["Always deploy dependencies along with the project", "Pin package versions in project.json"],
    ),
    "FileNotFoundException": RootCause(
        category="FileNotFound", title="File or Folder Not Found",
        description="The automation attempted to access a file or directory that does not exist.",
        severity="medium", confidence=0.88,
        suggested_fix="Verify the file path is correct and the file exists. Use relative paths or configurable assets.",
        preventive_recommendations=["Use Assets or Config files for file paths", "Add file existence checks before file operations"],
    ),
    "ArgumentException": RootCause(
        category="MissingArgument", title="Invalid or Missing Argument",
        description="A required workflow argument was not provided or has an invalid value.",
        severity="high", confidence=0.85,
        suggested_fix="Check that all required In/In-Out arguments are passed when invoking the workflow.",
        preventive_recommendations=["Document all required arguments", "Add argument validation at the start of each workflow"],
    ),
    "InvalidCredentialException": RootCause(
        category="CredentialIssue", title="Credential or Authentication Failure",
        description="The automation failed to authenticate due to invalid or expired credentials.",
        severity="critical", confidence=0.90,
        suggested_fix="Refresh credentials in UiPath Orchestrator Assets or Credential Manager.",
        preventive_recommendations=["Store credentials in Orchestrator Assets, not hardcoded", "Set up credential rotation alerts"],
    ),
    "NetworkException": RootCause(
        category="NetworkOrAPIFailure", title="Network or API Failure",
        description="The automation could not reach a network resource, API endpoint, or web service.",
        severity="high", confidence=0.82,
        suggested_fix="Verify the API endpoint URL is correct and the service is available. Check firewall rules.",
        preventive_recommendations=["Implement retry logic for transient network errors", "Monitor API health"],
    ),
    "QueueException": RootCause(
        category="QueueFailure", title="Queue Transaction Failure",
        description="The automation failed while processing an Orchestrator queue transaction.",
        severity="medium", confidence=0.83,
        suggested_fix="Review the queue item data for validation errors.",
        preventive_recommendations=["Validate queue item data before processing", "Set up retry policies on the Orchestrator queue"],
    ),
    "ConfigurationException": RootCause(
        category="ConfigurationIssue", title="Configuration or Asset Not Found",
        description="A required configuration value, Orchestrator asset, or environment variable is missing.",
        severity="high", confidence=0.87,
        suggested_fix="Ensure all assets referenced in the project are created in Orchestrator.",
        preventive_recommendations=["Use a centralised config file (Config.xlsx REFramework pattern)", "Validate all configuration values at startup"],
    ),
    "BusinessRuleException": RootCause(
        category="BusinessRuleException", title="Business Rule Violation",
        description="The automation encountered a business logic condition that could not be processed.",
        severity="medium", confidence=0.78,
        suggested_fix="Review the business rule that was violated. Ensure input data meets the expected business criteria.",
        preventive_recommendations=["Add pre-validation steps for input data", "Implement proper Business Exception handling in REFramework"],
    ),
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class RCAResult:
    root_causes: list[RootCause] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    ai_used: bool = False
    raw_ai_response: str | None = None
    # Extra context surfaces in results
    project_summary: dict = field(default_factory=dict)
    log_correlation: list[dict] = field(default_factory=list)


class RCAEngine:
    """Project-aware Root Cause Analysis engine.

    Analysis strategy:
    1. Build rich project context (name, platform, workflows, packages, metadata).
    2. Parse all log files and correlate exceptions to specific workflows/activities.
    3. Run heuristic rules against both exception data AND project structure.
    4. Incorporate coding-standards violations as additional causes.
    5. Optionally call OpenAI with the full context.
    6. Merge, rank and deduplicate causes.
    """

    async def analyze(
        self,
        project: Any,
        log_files: list[Any],
        pasted_error_text: str | None = None,
        standards_result: Any | None = None,
    ) -> RCAResult:
        project_info = self._build_project_info(project)
        exception_data = self._collect_exceptions(log_files)

        if pasted_error_text and pasted_error_text.strip():
            exception_data = self._parse_pasted_error(pasted_error_text) + exception_data

        # Correlate log exceptions to project workflow structure
        log_correlation = self._correlate_log_to_project(exception_data, project_info)

        # Heuristic: exception-driven causes
        heuristic_causes = self._heuristic_analysis(exception_data, project_info)

        # Structural causes (project-specific, no log needed)
        structural_causes = self._structural_analysis(project_info)

        # Incorporate standards violations as causes
        standards_causes: list[RootCause] = []
        if standards_result:
            standards_causes = self._standards_to_causes(standards_result)

        # AI analysis
        ai_causes: list[RootCause] = []
        raw_response: str | None = None
        ai_used = False

        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            try:
                ai_causes, raw_response = await self._ai_analysis(
                    project_info, exception_data, heuristic_causes + structural_causes
                )
                ai_used = True
            except Exception as e:
                raw_response = f"AI analysis failed: {str(e)}"

        # Merge all cause sources
        final_causes = self._merge_causes(
            ai_causes,
            heuristic_causes + structural_causes + standards_causes,
        )

        recommendations = self._build_recommendations(final_causes, project_info)

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
            project_summary=project_info,
            log_correlation=log_correlation,
        )

    # ── Log / exception parsing ────────────────────────────────────────────────

    def _parse_pasted_error(self, text: str) -> list[dict]:
        exceptions = []
        lines = text.strip().splitlines()
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

        if not exceptions:
            exceptions.append({
                "type": "UnknownError",
                "message": text[:1000],
                "source": "pasted_error",
            })
        return exceptions

    def _collect_exceptions(self, log_files: list[Any]) -> list[dict]:
        exceptions = []
        for lf in log_files:
            summary = lf.exception_summary or {}
            # Primary exception
            primary = summary.get("primary_exception")
            if primary:
                exceptions.append(primary)
            # All exceptions from parsed entries
            for exc in (summary.get("all_exceptions") or [])[:20]:
                if exc not in exceptions:
                    exceptions.append(exc)
            # Error trace entries
            for entry in (lf.execution_trace or {}).get("trace", [])[:30]:
                if entry.get("is_error") and entry.get("message"):
                    exceptions.append({
                        "type": "UnknownError",
                        "message": entry["message"],
                        "timestamp": entry.get("timestamp"),
                        "workflow": entry.get("workflow"),
                        "activity": entry.get("activity"),
                    })
        return exceptions

    # ── Project info ───────────────────────────────────────────────────────────

    def _build_project_info(self, project: Any) -> dict:
        platform = str(project.platform.value if hasattr(project.platform, "value") else project.platform)
        wf_struct = project.workflow_structure or {}
        workflows = wf_struct.get("workflows", [])
        deps = project.dependencies or {}
        packages = deps.get("packages", [])
        meta = project.project_metadata or {}

        # Collect all activity names across all workflows
        all_activities: list[str] = []
        workflow_names: list[str] = []
        for wf in workflows:
            wf_name = wf.get("filename") or wf.get("display_name") or ""
            if wf_name:
                workflow_names.append(wf_name)
            for act in self._flatten_activities(wf.get("activities", [])):
                dn = act.get("display_name") or act.get("name") or ""
                if dn:
                    all_activities.append(dn)

        return {
            "name": project.name,
            "platform": platform,
            "metadata": meta,
            "packages": packages,
            "package_names": [p.get("name", "") for p in packages],
            "workflow_count": len(workflows),
            "workflow_names": workflow_names,
            "activity_names": all_activities[:200],
            "workflows_raw": workflows,
            "upload_path": getattr(project, "upload_path", ""),
            "original_filename": getattr(project, "original_filename", ""),
        }

    # ── Log ↔ Project correlation ──────────────────────────────────────────────

    def _correlate_log_to_project(
        self, exceptions: list[dict], project_info: dict
    ) -> list[dict]:
        """
        Cross-reference each exception's workflow/activity against the parsed
        project structure.  Returns a list of correlation records.
        """
        if not exceptions:
            return []

        workflow_names_lower = {wn.lower().replace(".xaml", ""): wn for wn in project_info.get("workflow_names", [])}
        activity_names_lower = {an.lower(): an for an in project_info.get("activity_names", [])}

        correlations = []
        for exc in exceptions[:10]:
            record: dict = {
                "exception_type": exc.get("type", "Unknown"),
                "message": exc.get("message", "")[:300],
                "timestamp": exc.get("timestamp"),
                "matched_workflow": None,
                "matched_activity": None,
                "stack_trace_snippet": (exc.get("stack_trace") or "")[:300],
            }

            # Try to match workflow from exception's own field
            exc_wf = (exc.get("workflow") or "").lower().replace(".xaml", "")
            if exc_wf:
                record["matched_workflow"] = workflow_names_lower.get(exc_wf, exc.get("workflow"))

            # Try to match workflow by scanning message / stack_trace for workflow names
            if not record["matched_workflow"]:
                combined = f"{exc.get('message','')} {exc.get('stack_trace','')}".lower()
                for wl, wn in workflow_names_lower.items():
                    if wl in combined:
                        record["matched_workflow"] = wn
                        break

            # Try to match activity
            exc_act = (exc.get("activity") or "").lower()
            if exc_act:
                record["matched_activity"] = activity_names_lower.get(exc_act, exc.get("activity"))

            if not record["matched_activity"]:
                combined = f"{exc.get('message','')} {exc.get('stack_trace','')}".lower()
                for al, an in activity_names_lower.items():
                    if al in combined and len(al) > 4:
                        record["matched_activity"] = an
                        break

            correlations.append(record)
        return correlations

    # ── Heuristic analysis ─────────────────────────────────────────────────────

    def _heuristic_analysis(
        self, exceptions: list[dict], project_info: dict
    ) -> list[RootCause]:
        found: list[RootCause] = []
        seen: set[str] = set()

        for exc in exceptions:
            exc_type = exc.get("type", "")
            exc_msg  = exc.get("message", "")
            combined = f"{exc_type} {exc_msg}"

            for key, rule in HEURISTIC_RULES.items():
                if key.lower() in combined.lower():
                    if rule.category not in seen:
                        cause = rule.model_copy()
                        cause.evidence = [
                            f"Exception type: {exc_type}",
                            f"Message: {exc_msg[:300]}",
                        ]
                        if exc.get("timestamp"):
                            cause.evidence.append(f"Timestamp: {exc['timestamp']}")
                        cause.affected_workflow = exc.get("workflow")
                        cause.affected_activity = exc.get("activity")
                        found.append(cause)
                        seen.add(rule.category)
                    break

        return found

    # ── Structural / project-specific analysis ─────────────────────────────────

    def _structural_analysis(self, project_info: dict) -> list[RootCause]:
        """
        Analyse the project structure itself (no log required) and return causes
        that are specific to this project's content.
        """
        causes: list[RootCause] = []
        platform = project_info["platform"]
        pkg_names = project_info.get("package_names", [])
        workflows = project_info.get("workflows_raw", [])
        wf_names  = project_info.get("workflow_names", [])
        activities = project_info.get("activity_names", [])

        if platform == "uipath":
            causes.extend(self._structural_uipath(project_info, pkg_names, workflows, wf_names, activities))
        elif platform == "power_automate":
            causes.extend(self._structural_pa(project_info))
        elif platform == "blue_prism":
            causes.extend(self._structural_bp(project_info))
        elif platform == "automation_anywhere":
            causes.extend(self._structural_aa(project_info))
        else:
            causes.append(RootCause(
                category="UnknownPlatform",
                title="Platform Not Identified",
                description=f"The project platform could not be determined (detected: '{platform}'). Analysis may be incomplete.",
                severity="medium", confidence=0.60,
                evidence=[f"Original filename: {project_info.get('original_filename', 'unknown')}"],
                suggested_fix="Ensure the uploaded file is a valid RPA project archive for a supported platform.",
                preventive_recommendations=["Upload a ZIP containing project.json (UiPath), definition.json (Power Automate), .bprelease (Blue Prism), or bot.json (Automation Anywhere)"],
            ))

        return causes

    def _structural_uipath(self, project_info, pkg_names, workflows, wf_names, activities) -> list[RootCause]:
        causes: list[RootCause] = []
        meta = project_info.get("metadata", {})

        # Missing core package
        if pkg_names and not any("UiPath.System.Activities" in p for p in pkg_names):
            causes.append(RootCause(
                category="MissingPackage",
                title="Core Package UiPath.System.Activities Missing",
                description="project.json dependencies do not include UiPath.System.Activities, which is required for all workflows.",
                severity="critical", confidence=0.95,
                evidence=[f"Packages found: {', '.join(pkg_names[:5]) or 'none'}"],
                suggested_fix="Open Manage Packages in UiPath Studio and install UiPath.System.Activities.",
                preventive_recommendations=["Always verify dependencies before deploying to Robot"],
            ))

        # No Try-Catch in Main.xaml
        main_wf = next((w for w in workflows if "main" in w.get("filename", "").lower()), None)
        if main_wf:
            flat_main = self._flatten_activities(main_wf.get("activities", []))
            has_tc = any("trycatch" in a.get("name", "").lower() or "try" in a.get("display_name", "").lower() for a in flat_main)
            if not has_tc:
                causes.append(RootCause(
                    category="MissingExceptionHandler",
                    title="No Try-Catch in Main.xaml",
                    description="Main.xaml does not contain a TryCatch activity, meaning any unhandled exception will crash the process silently.",
                    severity="high", confidence=0.88,
                    evidence=[f"Main workflow: {main_wf.get('filename')}", f"Top-level activity count: {main_wf.get('activity_count', 0)}"],
                    suggested_fix="Wrap the main Sequence in a TryCatch activity. In the Catches block, log the exception and set a failure status.",
                    preventive_recommendations=["Register a Global Exception Handler for unexpected crashes", "Follow REFramework pattern for robust exception management"],
                ))

        # No logging activities at all
        log_acts = [a for a in activities if "log" in a.lower()]
        if not log_acts and workflows:
            causes.append(RootCause(
                category="MissingLogging",
                title="No Log Message Activities Found",
                description=f"None of the {len(workflows)} workflow(s) in this project contain Log Message activities, making failures hard to diagnose.",
                severity="medium", confidence=0.85,
                evidence=[f"Workflows scanned: {', '.join(wf_names[:3]) or 'none'}"],
                suggested_fix="Add Log Message (Info level) at process start, key decision points, and in all exception handlers.",
                preventive_recommendations=["Enable verbose logging in Robot settings for debugging", "Use structured log fields for machine-readable output"],
            ))

        # REFramework check
        refw = ["init", "gettransaction", "process", "endprocess"]
        wf_lower = " ".join(wf_names).lower()
        if not any(r in wf_lower for r in refw) and len(workflows) > 2:
            causes.append(RootCause(
                category="ArchitectureIssue",
                title="REFramework Pattern Not Detected",
                description=f"Project has {len(workflows)} workflows but does not follow the REFramework (Init/GetTransaction/Process/EndProcess) structure.",
                severity="low", confidence=0.70,
                evidence=[f"Workflows: {', '.join(wf_names[:5])}"],
                suggested_fix="Adopt the UiPath REFramework template for production automation to ensure reliable transaction handling.",
                preventive_recommendations=["Download REFramework from UiPath Marketplace", "Separate Init, Process, and End logic into dedicated workflows"],
            ))

        # Version info
        version = meta.get("version") or meta.get("studio_version")
        if version:
            causes.append(RootCause(
                category="ProjectInfo",
                title=f"Project: {project_info['name']}",
                description=f"UiPath project '{project_info['name']}' (version {version}, Studio {meta.get('studio_version', 'unknown')}). "
                            f"Contains {len(workflows)} workflow(s) and {len(pkg_names)} package(s).",
                severity="low", confidence=1.0,
                evidence=[
                    f"Studio version: {meta.get('studio_version', 'unknown')}",
                    f"Project version: {version}",
                    f"Main workflow: {meta.get('main_workflow', 'unknown')}",
                    f"Author: {meta.get('author', 'unknown')}",
                ],
                suggested_fix="Review the above project details to ensure the correct version is deployed.",
                preventive_recommendations=["Pin project and package versions before deploying to production"],
            ))

        return causes

    def _structural_pa(self, project_info) -> list[RootCause]:
        causes: list[RootCause] = []
        meta = project_info.get("metadata", {})
        wf = project_info.get("workflows_raw", {})
        actions = wf.get("actions", []) if isinstance(wf, dict) else []
        action_types = [a.get("type", "").lower() for a in actions]

        if not any(eh in " ".join(action_types) for eh in ["scope", "runafter", "terminate"]):
            causes.append(RootCause(
                category="MissingExceptionHandler",
                title="No Error Handling in Power Automate Flow",
                description="The flow does not contain Scope or 'Configure run after' error-handling actions.",
                severity="high", confidence=0.85,
                evidence=[f"Actions found: {len(actions)}", f"Action types: {', '.join(set(action_types[:8]))}"],
                suggested_fix="Add a Scope action wrapping critical steps with a 'has failed' run-after path.",
                preventive_recommendations=["Configure 'Run after' on every action that could fail"],
            ))

        if not meta.get("name"):
            causes.append(RootCause(
                category="ProjectInfo",
                title="Flow Metadata Missing",
                description="The Power Automate flow has no name or description in its definition.",
                severity="low", confidence=0.90,
                evidence=["definition.json metadata empty"],
                suggested_fix="Add a name and description to the flow definition.",
                preventive_recommendations=["Document all flows with owner, purpose, and trigger information"],
            ))
        return causes

    def _structural_bp(self, project_info) -> list[RootCause]:
        causes: list[RootCause] = []
        wf_struct = project_info.get("workflows_raw") or {}
        if isinstance(wf_struct, list):
            stages = []
            for w in wf_struct:
                stages += w.get("stages", [])
        else:
            stages = wf_struct.get("stages", [])

        stage_types = [s.get("type", "").lower() for s in stages]

        if "exception" not in " ".join(stage_types):
            causes.append(RootCause(
                category="MissingExceptionHandler",
                title="No Exception Stage in Blue Prism Process",
                description="No Exception stages were found. Without these, runtime errors will terminate the process with no cleanup.",
                severity="high", confidence=0.88,
                evidence=[f"Total stages: {len(stages)}", f"Stage types found: {', '.join(set(stage_types[:8]))}"],
                suggested_fix="Add Exception stages to all process pages and connect them to a Recovery or cleanup path.",
                preventive_recommendations=["Follow Blue Prism's exception handling framework", "Always pair Exception stages with Recovery stages"],
            ))

        if "start" not in " ".join(stage_types) or "end" not in " ".join(stage_types):
            causes.append(RootCause(
                category="StructuralError",
                title="Missing Start or End Stage",
                description="Blue Prism process is missing a Start or End stage, which violates platform conventions and will prevent execution.",
                severity="critical", confidence=0.95,
                evidence=[f"Stage types: {', '.join(set(stage_types))}"],
                suggested_fix="Every process page must have exactly one Start and one End stage.",
                preventive_recommendations=["Run the Blue Prism process validator before publishing"],
            ))

        return causes

    def _structural_aa(self, project_info) -> list[RootCause]:
        causes: list[RootCause] = []
        wf_struct = project_info.get("workflows_raw") or {}
        if isinstance(wf_struct, list):
            commands = []
            for w in wf_struct:
                commands += w.get("commands", [])
        else:
            commands = wf_struct.get("commands", [])

        cmd_types = [c.get("type", "").lower() for c in commands]

        if not any("error" in t or "try" in t or "catch" in t for t in cmd_types):
            causes.append(RootCause(
                category="MissingExceptionHandler",
                title="No Error Handling Commands in Bot",
                description="The Automation Anywhere bot does not contain Try/Catch error-handling commands.",
                severity="high", confidence=0.85,
                evidence=[f"Commands found: {len(commands)}"],
                suggested_fix="Wrap risky operations in Try/Catch error-handling blocks.",
                preventive_recommendations=["Handle both expected and unexpected errors separately"],
            ))

        if not any("log" in t or "message" in t for t in cmd_types):
            causes.append(RootCause(
                category="MissingLogging",
                title="No Logging Commands in Bot",
                description="No Log to File or message commands were found in the bot.",
                severity="medium", confidence=0.82,
                evidence=[f"Commands found: {len(commands)}"],
                suggested_fix="Add Log to File commands at key process milestones for auditability.",
                preventive_recommendations=["Log start, end, and all exceptions to a centralised log file"],
            ))

        return causes

    # ── Standards violations → RCA causes ─────────────────────────────────────

    def _standards_to_causes(self, standards_result: Any) -> list[RootCause]:
        """Convert critical/high coding-standards violations into RCA root causes."""
        causes: list[RootCause] = []
        seen: set[str] = set()

        for v in getattr(standards_result, "violations", []):
            if v.severity not in ("critical", "high"):
                continue
            key = f"Standards:{v.rule_id}"
            if key in seen:
                continue
            seen.add(key)
            causes.append(RootCause(
                category="CodingStandardsViolation",
                title=f"Standards Violation: {v.rule_name}",
                description=v.description,
                severity=v.severity,
                confidence=0.80,
                evidence=[f"Rule: {v.rule_id}", f"Location: {v.location} ({v.location_type})"],
                affected_workflow=v.location if v.location_type == "workflow" else None,
                suggested_fix=v.recommendation,
                preventive_recommendations=[f"Fix rule {v.rule_id} before deploying to production"],
            ))

        return causes

    # ── AI analysis ────────────────────────────────────────────────────────────

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
        project_text = json.dumps({
            "name":           project_info["name"],
            "platform":       project_info["platform"],
            "workflow_count": project_info["workflow_count"],
            "workflow_names": project_info["workflow_names"][:10],
            "package_names":  project_info["package_names"][:10],
            "metadata":       project_info["metadata"],
        }, indent=2, default=str)

        prompt = f"""You are an RPA automation expert specialising in root cause analysis.

Analyse the following automation project and exception data, then provide a structured RCA
that is SPECIFIC to this project — reference actual workflow names, activity names, and package names.

PROJECT:
{project_text}

EXCEPTIONS DETECTED:
{exceptions_text}

INITIAL HEURISTIC FINDINGS:
{heuristic_summary if heuristic_summary else 'None detected'}

Respond with JSON (exact structure):
{{
  "root_causes": [
    {{
      "category": "NullReference|SelectorFailure|Timeout|MissingPackage|FileNotFound|MissingArgument|CredentialIssue|NetworkOrAPIFailure|QueueFailure|ConfigurationIssue|BusinessRuleException|UnhandledException|MissingExceptionHandler|ArchitectureIssue|ProjectInfo",
      "title": "concise title referencing the actual workflow/activity if known",
      "description": "detailed explanation referencing specific project artefacts",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "evidence": ["specific evidence from log/project"],
      "affected_workflow": "exact workflow filename or null",
      "affected_activity": "exact activity name or null",
      "suggested_fix": "specific actionable fix for THIS project",
      "preventive_recommendations": ["list of preventive measures"]
    }}
  ]
}}

Be specific — mention actual workflow names, activity display names, and package names from the project data above."""

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

    # ── Merging & recommendations ──────────────────────────────────────────────

    def _merge_causes(
        self, ai_causes: list[RootCause], other_causes: list[RootCause]
    ) -> list[RootCause]:
        if not ai_causes:
            merged = list(other_causes)
        else:
            ai_cats = {c.category for c in ai_causes}
            merged = list(ai_causes) + [c for c in other_causes if c.category not in ai_cats]

        # Put ProjectInfo last, sort rest by severity then confidence
        info_causes  = [c for c in merged if c.category == "ProjectInfo"]
        other_merged = [c for c in merged if c.category != "ProjectInfo"]
        other_merged.sort(key=lambda c: (SEVERITY_ORDER.get(c.severity, 4), -c.confidence))
        return (other_merged + info_causes)[:12]

    def _build_recommendations(self, causes: list[RootCause], project_info: dict) -> list[str]:
        recs: list[str] = []
        for cause in causes:
            if cause.suggested_fix and cause.category != "ProjectInfo":
                recs.append(f"[{cause.severity.upper()}] {cause.title}: {cause.suggested_fix}")

        platform = project_info.get("platform", "")
        if platform == "uipath":
            recs += [
                "Implement REFramework for production-grade RPA projects",
                "Enable detailed logging in Robot settings",
                "Use Orchestrator Assets for all configurable values",
                "Set up email/Teams alerts for unhandled exceptions",
            ]
        elif platform == "power_automate":
            recs += [
                "Use error handling actions in every cloud flow",
                "Enable flow run history and monitoring",
                "Use environment variables instead of hardcoded values",
            ]
        elif platform == "blue_prism":
            recs += [
                "Use Blue Prism's Exception and Recovery stages on every page",
                "Enable process logging in Control Room",
            ]
        elif platform == "automation_anywhere":
            recs += [
                "Use the Credential Vault for all sensitive values",
                "Add error handling and logging commands to all bots",
            ]

        return list(dict.fromkeys(recs))

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _flatten_activities(self, activities: list[dict], depth: int = 0) -> list[dict]:
        result = []
        for act in activities:
            result.append(act)
            children = act.get("children")
            if children and depth < 10:
                result.extend(self._flatten_activities(children, depth + 1))
        return result
