from __future__ import annotations

"""
RCA Engine — Log-First Analysis

Rules enforced:
1. When a log file is present:
   - Log is the PRIMARY source of truth.
   - Extract the actual exception, error message, stack trace, and failed activity.
   - Correlate every exception to the uploaded project structure.
   - Runtime root causes come ONLY from log evidence.
   - Static code review is performed separately and NOT mixed into runtime causes.
   - Standards violations are NOT classified as runtime root causes unless the log
     directly references the same workflow/activity.
2. When NO log file is present:
   - Perform static analysis of the project structure.
   - Review for coding standards, best practices, potential runtime risks, etc.
   - All findings are labelled as "potential" — not confirmed runtime failures.
3. Never generate generic root causes.
4. Never assume an error not present in the log.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

from config import settings
from schemas import RootCause


# ── Heuristic rules keyed on exception-type substring ──────────────────────
HEURISTIC_RULES: dict[str, dict] = {
    "NullReferenceException": dict(
        category="NullReference", title="Null Reference Exception",
        description="A variable or argument was used before being initialised or returned a null value at runtime.",
        severity="high", confidence=0.88,
        suggested_fix="Add a null check (Is Nothing / is None) before using the variable. Initialise all In/Out arguments with default values.",
        preventive_recommendations=[
            "Always initialise variables before use",
            "Use 'Is Nothing' or conditional checks for optional arguments",
            "Wrap activities that may return null in Try-Catch",
        ],
        failure_category="Coding Logic",
    ),
    "SelectorNotFoundException": dict(
        category="SelectorFailure", title="UI Element Selector Not Found",
        description="The automation could not locate the UI element matching the configured selector. The target application UI may have changed or is not in the expected state.",
        severity="high", confidence=0.92,
        suggested_fix="Update the selector using wildcards for volatile attributes (idx, title). Enable dynamic selectors and add a Retry Scope.",
        preventive_recommendations=[
            "Use dynamic selectors with wildcard attributes",
            "Validate selectors in UiExplorer before deploying",
            "Add Retry Scope with delay around selector-dependent activities",
        ],
        failure_category="Application Issue",
    ),
    "TimeoutException": dict(
        category="Timeout", title="Activity Timeout Exceeded",
        description="An activity exceeded its configured timeout. The target system was slow or unresponsive.",
        severity="medium", confidence=0.82,
        suggested_fix="Increase the timeout value for the failing activity. Add a Retry Scope for transient delays.",
        preventive_recommendations=[
            "Set timeout values based on measured system performance",
            "Implement retry logic for time-sensitive activities",
        ],
        failure_category="Infrastructure",
    ),
    "MissingPackageException": dict(
        category="MissingPackage", title="Missing or Incompatible Dependency Package",
        description="A required NuGet/activity package is not installed or has a version conflict in the execution environment.",
        severity="critical", confidence=0.93,
        suggested_fix="Ensure all packages listed in project.json are installed in the Robot environment with matching versions.",
        preventive_recommendations=[
            "Deploy dependencies alongside the project archive",
            "Pin exact package versions in project.json",
        ],
        failure_category="Package Dependency",
    ),
    "FileNotFoundException": dict(
        category="FileNotFound", title="File or Folder Not Found",
        description="The automation attempted to access a file or folder path that does not exist at runtime.",
        severity="medium", confidence=0.90,
        suggested_fix="Verify the file path is correct and the file exists before the activity runs. Use relative paths or Orchestrator Assets for paths.",
        preventive_recommendations=[
            "Add path existence checks before file operations",
            "Use Assets/Config files for file paths instead of hardcoding",
        ],
        failure_category="Business Data",
    ),
    "ArgumentException": dict(
        category="MissingArgument", title="Invalid or Missing Workflow Argument",
        description="A required workflow argument was not provided or received an invalid value when the workflow was invoked.",
        severity="high", confidence=0.86,
        suggested_fix="Check that all required In/In-Out arguments are passed correctly when invoking the workflow.",
        preventive_recommendations=[
            "Document all required arguments and their expected types",
            "Add argument validation at the start of each workflow",
        ],
        failure_category="Coding Logic",
    ),
    "InvalidCredentialException": dict(
        category="CredentialIssue", title="Credential or Authentication Failure",
        description="The automation failed to authenticate. Credentials may be expired, incorrect, or missing from the credential store.",
        severity="critical", confidence=0.91,
        suggested_fix="Refresh credentials in Orchestrator Assets or Windows Credential Manager. Verify the account has the required permissions.",
        preventive_recommendations=[
            "Never hardcode credentials — use Orchestrator Assets or Credential Manager",
            "Set up credential rotation and expiry alerts",
        ],
        failure_category="Credentials",
    ),
    "NetworkException": dict(
        category="NetworkOrAPIFailure", title="Network or API Communication Failure",
        description="The automation could not reach a network resource, REST API, or web service endpoint.",
        severity="high", confidence=0.84,
        suggested_fix="Verify the API endpoint URL, check firewall/proxy rules, and confirm the service is available.",
        preventive_recommendations=[
            "Implement retry logic with exponential back-off for transient network errors",
            "Monitor API health and configure alerts",
        ],
        failure_category="Network",
    ),
    "QueueException": dict(
        category="QueueFailure", title="Queue Transaction Processing Failure",
        description="The automation failed while reading or processing an Orchestrator queue transaction.",
        severity="medium", confidence=0.83,
        suggested_fix="Review the failing queue item's data for validation errors. Check queue retry policies.",
        preventive_recommendations=[
            "Validate queue item data before processing",
            "Configure retry policies on the Orchestrator queue",
        ],
        failure_category="Business Data",
    ),
    "ConfigurationException": dict(
        category="ConfigurationIssue", title="Configuration or Asset Not Found",
        description="A required Orchestrator asset, configuration key, or environment variable was missing at runtime.",
        severity="high", confidence=0.88,
        suggested_fix="Ensure all assets referenced by the project exist in Orchestrator for the correct environment.",
        preventive_recommendations=[
            "Use a centralised Config.xlsx or Orchestrator asset store",
            "Validate all configuration values during the Init state",
        ],
        failure_category="Configuration",
    ),
    "BusinessRuleException": dict(
        category="BusinessRuleException", title="Business Rule Violation",
        description="The automation encountered a business condition it was not designed to handle.",
        severity="medium", confidence=0.79,
        suggested_fix="Review the business rule that was violated. Ensure input data meets expected criteria before processing.",
        preventive_recommendations=[
            "Add pre-validation steps for all input data",
            "Implement proper BusinessRuleException handling (REFramework pattern)",
        ],
        failure_category="Business Data",
    ),
    "PermissionException": dict(
        category="PermissionIssue", title="Permissions / Access Denied",
        description="The robot account does not have the required file, folder, application, or network permissions.",
        severity="high", confidence=0.87,
        suggested_fix="Grant the robot service account the required permissions. Review UAC and file-system ACLs.",
        preventive_recommendations=[
            "Document all required permissions per robot environment",
            "Test robot accounts with least-privilege access before deployment",
        ],
        failure_category="Permissions",
    ),
    "EnvironmentException": dict(
        category="EnvironmentIssue", title="Environment or Infrastructure Failure",
        description="The execution environment (OS, infrastructure, runtime) is not in the expected state.",
        severity="high", confidence=0.80,
        suggested_fix="Verify the execution environment meets the automation prerequisites (OS version, runtime, installed software).",
        preventive_recommendations=[
            "Maintain environment baselines and monitor drift",
            "Run smoke tests after environment changes",
        ],
        failure_category="Environment",
    ),
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class RuntimeAnalysis:
    """Structured runtime analysis extracted from a log file."""
    has_log: bool = False
    error_message: str = ""
    exception_type: str = ""
    failed_workflow: str = ""
    failed_activity: str = ""
    timestamp: str = ""
    root_cause_summary: str = ""
    evidence_from_log: list[str] = field(default_factory=list)
    suggested_fixes: list[str] = field(default_factory=list)
    validation_steps: list[str] = field(default_factory=list)
    failure_category: str = ""        # App / Infra / Data / Config / Creds / Network / Package / Logic / Env
    all_exceptions: list[dict] = field(default_factory=list)


@dataclass
class RCAResult:
    root_causes: list[RootCause] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    ai_used: bool = False
    raw_ai_response: str | None = None
    project_summary: dict = field(default_factory=dict)
    log_correlation: list[dict] = field(default_factory=list)
    runtime_analysis: dict = field(default_factory=dict)   # serialised RuntimeAnalysis
    has_log: bool = False


class RCAEngine:
    """
    Log-First Root Cause Analysis engine.

    When log files are provided:
      1. Parse all logs — extract every exception, message, stack trace, workflow, activity.
      2. Build RuntimeAnalysis: primary failure details, correlated to project structure.
      3. Heuristic causes come from log exceptions only — never from structure alone.
      4. Static analysis runs independently and is tagged as "potential risk" not runtime cause.

    When no log files are provided:
      1. Static structural analysis of the project.
      2. Coding standards violations as potential risks.
      3. All findings are clearly labelled as static analysis, not confirmed runtime failures.
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
            pasted = self._parse_pasted_error(pasted_error_text)
            exception_data = pasted + exception_data

        has_log = bool(exception_data)

        # ── Log correlation (always runs when exceptions exist) ──────────────
        log_correlation = self._correlate_log_to_project(exception_data, project_info)

        # ── Runtime analysis (log-driven) ────────────────────────────────────
        runtime_analysis = self._build_runtime_analysis(
            exception_data, log_correlation, project_info, log_files
        )

        # ── Root causes ──────────────────────────────────────────────────────
        if has_log:
            # LOG PRESENT: heuristic causes ONLY from log exceptions
            heuristic_causes = self._heuristic_from_log(exception_data, log_correlation)
            # Static structural causes become "potential risks" (severity lowered, confidence lowered)
            static_causes = self._structural_analysis_as_risks(project_info)
        else:
            # NO LOG: full static analysis, all findings labelled as potential
            heuristic_causes = []
            static_causes = self._structural_analysis(project_info)

        # Standards violations: only inject as runtime causes when log confirms same location
        standards_causes: list[RootCause] = []
        if standards_result:
            standards_causes = self._standards_to_causes(
                standards_result,
                log_correlation=log_correlation if has_log else [],
                log_confirmed_only=has_log,
            )

        # ── AI analysis ──────────────────────────────────────────────────────
        ai_causes: list[RootCause] = []
        raw_response: str | None = None
        ai_used = False

        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            try:
                ai_causes, raw_response = await self._ai_analysis(
                    project_info, exception_data, heuristic_causes,
                    has_log=has_log,
                )
                ai_used = True
            except Exception as exc:
                raw_response = f"AI analysis failed: {str(exc)}"

        # ── Merge ────────────────────────────────────────────────────────────
        if has_log:
            # AI + heuristic causes are runtime causes; static causes are appended after
            runtime_pool = heuristic_causes + standards_causes
            static_pool  = static_causes
            final_causes = self._merge_causes(ai_causes, runtime_pool, static_pool)
        else:
            all_static = static_causes + standards_causes
            final_causes = self._merge_causes(ai_causes, all_static, [])

        recommendations = self._build_recommendations(
            final_causes, project_info, has_log, runtime_analysis
        )

        overall_conf = (
            sum(c.confidence for c in final_causes) / len(final_causes)
            if final_causes else 0.0
        )

        import dataclasses
        ra_dict = dataclasses.asdict(runtime_analysis)

        return RCAResult(
            root_causes=final_causes,
            recommendations=recommendations,
            overall_confidence=round(overall_conf, 2),
            ai_used=ai_used,
            raw_ai_response=raw_response,
            project_summary=project_info,
            log_correlation=log_correlation,
            runtime_analysis=ra_dict,
            has_log=has_log,
        )

    # ─────────────────────────── Log/exception parsing ───────────────────────

    def _parse_pasted_error(self, text: str) -> list[dict]:
        exceptions: list[dict] = []
        lines = text.strip().splitlines()
        exc_pattern = re.compile(r"([A-Z][a-zA-Z]+Exception|Error)[:\s]*(.*)", re.IGNORECASE)
        current_exc: dict | None = None

        for line in lines[:300]:
            m = exc_pattern.search(line)
            if m:
                if current_exc:
                    exceptions.append(current_exc)
                current_exc = {
                    "type": m.group(1),
                    "message": (m.group(2).strip() or line.strip())[:500],
                    "stack_trace": line,
                    "source": "pasted_error",
                }
            elif current_exc and line.strip().startswith("at "):
                current_exc["stack_trace"] = (
                    current_exc.get("stack_trace", "") + "\n" + line
                )[:2000]

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
        exceptions: list[dict] = []
        for lf in log_files:
            summary = lf.exception_summary or {}
            primary = summary.get("primary_exception")
            if primary:
                exceptions.append(primary)
            for exc in (summary.get("all_exceptions") or [])[:30]:
                if exc not in exceptions:
                    exceptions.append(exc)
            for entry in (lf.execution_trace or {}).get("trace", [])[:50]:
                if entry.get("is_error") and entry.get("message"):
                    exceptions.append({
                        "type": entry.get("exception_type") or "RuntimeError",
                        "message": entry["message"],
                        "timestamp": entry.get("timestamp"),
                        "workflow": entry.get("workflow"),
                        "activity": entry.get("activity"),
                        "stack_trace": entry.get("stack_trace"),
                    })
        # Deduplicate by (type, message[:100])
        seen: set[tuple] = set()
        deduped: list[dict] = []
        for e in exceptions:
            key = (e.get("type", ""), e.get("message", "")[:100])
            if key not in seen:
                seen.add(key)
                deduped.append(e)
        return deduped

    # ─────────────────────────── Project info ────────────────────────────────

    def _build_project_info(self, project: Any) -> dict:
        platform = str(
            project.platform.value if hasattr(project.platform, "value") else project.platform
        )
        wf_struct  = project.workflow_structure or {}
        workflows  = wf_struct.get("workflows", [])
        deps       = project.dependencies or {}
        packages   = deps.get("packages", [])
        meta       = project.project_metadata or {}

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

    # ─────────────────────────── Runtime analysis builder ────────────────────

    def _build_runtime_analysis(
        self,
        exceptions: list[dict],
        correlations: list[dict],
        project_info: dict,
        log_files: list[Any],
    ) -> RuntimeAnalysis:
        ra = RuntimeAnalysis(has_log=bool(exceptions))
        if not exceptions:
            return ra

        primary = exceptions[0]
        corr    = correlations[0] if correlations else {}

        ra.exception_type   = primary.get("type") or "Unknown"
        ra.error_message    = primary.get("message") or ""
        ra.timestamp        = primary.get("timestamp") or ""
        ra.failed_workflow  = (
            corr.get("matched_workflow")
            or primary.get("workflow")
            or ""
        )
        ra.failed_activity  = (
            corr.get("matched_activity")
            or primary.get("activity")
            or ""
        )
        ra.all_exceptions = exceptions[:15]

        # Determine failure category from exception type
        rule = HEURISTIC_RULES.get(ra.exception_type)
        ra.failure_category = rule["failure_category"] if rule else self._infer_failure_category(
            ra.exception_type, ra.error_message
        )

        # Evidence — pulled directly from the log
        evidence: list[str] = [f"Exception: {ra.exception_type}"]
        if ra.error_message:
            evidence.append(f"Message: {ra.error_message[:400]}")
        if ra.timestamp:
            evidence.append(f"Timestamp: {ra.timestamp}")
        if ra.failed_workflow:
            evidence.append(f"Workflow: {ra.failed_workflow}")
        if ra.failed_activity:
            evidence.append(f"Activity: {ra.failed_activity}")
        if primary.get("stack_trace"):
            st = (primary["stack_trace"] or "")[:400]
            evidence.append(f"Stack trace snippet:\n{st}")
        # Additional errors from log
        for lf in log_files:
            for entry in (getattr(lf, "execution_trace", None) or {}).get("trace", [])[:5]:
                if entry.get("is_error") and entry.get("message"):
                    evidence.append(f"[{entry.get('timestamp','?')}] {entry['message'][:200]}")
        ra.evidence_from_log = evidence[:12]

        # Root cause summary
        if rule:
            ra.root_cause_summary = rule["description"]
        else:
            ra.root_cause_summary = (
                f"Runtime {ra.exception_type} occurred"
                + (f" in workflow '{ra.failed_workflow}'" if ra.failed_workflow else "")
                + (f" at activity '{ra.failed_activity}'" if ra.failed_activity else "")
                + "."
            )

        # Suggested fixes
        if rule:
            ra.suggested_fixes = [rule["suggested_fix"]] + list(rule.get("preventive_recommendations", []))
        else:
            ra.suggested_fixes = [
                f"Investigate the root cause of the {ra.exception_type} in the execution logs.",
                "Add a Try-Catch block around the failing activity.",
                "Enable verbose logging and re-run to capture more details.",
            ]

        # Validation steps
        ra.validation_steps = self._build_validation_steps(ra, project_info)

        return ra

    def _infer_failure_category(self, exc_type: str, message: str) -> str:
        combined = f"{exc_type} {message}".lower()
        if any(k in combined for k in ["permission", "access denied", "unauthorized"]):
            return "Permissions"
        if any(k in combined for k in ["network", "http", "api", "connection", "timeout"]):
            return "Network"
        if any(k in combined for k in ["file", "path", "folder", "directory"]):
            return "Business Data"
        if any(k in combined for k in ["credential", "password", "auth"]):
            return "Credentials"
        if any(k in combined for k in ["config", "asset", "environment variable"]):
            return "Configuration"
        if any(k in combined for k in ["package", "assembly", "dependency"]):
            return "Package Dependency"
        return "Application Issue"

    def _build_validation_steps(self, ra: RuntimeAnalysis, project_info: dict) -> list[str]:
        steps: list[str] = []
        platform = project_info.get("platform", "")
        exc = ra.exception_type.lower()

        if ra.failed_workflow:
            steps.append(f"Open '{ra.failed_workflow}' and locate the failing activity.")
        if "selector" in exc or "element" in exc:
            steps.append("Open UiExplorer and validate the selector against the live application.")
        if "credential" in exc or "auth" in exc:
            steps.append("Check the credential in Orchestrator Assets — verify username/password is current.")
        if "null" in exc or "argument" in exc:
            steps.append("Add a breakpoint before the failing activity and inspect variable values.")
        if "file" in exc:
            steps.append("Confirm the file path exists on the Robot machine and the service account has read access.")
        if "network" in exc or "http" in exc or "api" in exc:
            steps.append("Test the API endpoint manually (curl / Postman) from the Robot machine.")
        if "timeout" in exc:
            steps.append("Increase the activity timeout and add a Retry Scope with a delay.")
        if "package" in exc or "assembly" in exc:
            steps.append("Run 'Manage Packages' in UiPath Studio — verify all dependencies are installed and version-matched.")

        # Platform-specific
        if platform == "uipath":
            steps.append("Check the UiPath Robot execution logs in Orchestrator for the full stack trace.")
            steps.append("Run the workflow in debug mode with 'Break on Exception' enabled.")
        elif platform == "power_automate":
            steps.append("Review the flow run history in Power Automate for the detailed error output.")
        elif platform == "blue_prism":
            steps.append("Check the Control Room session log for the failing stage.")
        elif platform == "automation_anywhere":
            steps.append("Review the bot execution logs in Control Room / Bot Insight.")

        if not steps:
            steps.append("Enable verbose logging and re-run the automation to capture additional context.")

        return steps[:8]

    # ─────────────────────────── Log → Project correlation ───────────────────

    def _correlate_log_to_project(
        self, exceptions: list[dict], project_info: dict
    ) -> list[dict]:
        if not exceptions:
            return []

        wf_lower = {
            wn.lower().replace(".xaml", ""): wn
            for wn in project_info.get("workflow_names", [])
        }
        act_lower = {
            an.lower(): an for an in project_info.get("activity_names", [])
        }

        correlations: list[dict] = []
        for exc in exceptions[:15]:
            record: dict = {
                "exception_type":       exc.get("type", "Unknown"),
                "message":              exc.get("message", "")[:400],
                "timestamp":            exc.get("timestamp"),
                "matched_workflow":     None,
                "matched_activity":     None,
                "stack_trace_snippet":  (exc.get("stack_trace") or "")[:500],
                "match_confidence":     "none",   # high / partial / none
            }

            # Try exact workflow match from exception field
            exc_wf = (exc.get("workflow") or "").lower().replace(".xaml", "")
            if exc_wf and exc_wf in wf_lower:
                record["matched_workflow"] = wf_lower[exc_wf]
                record["match_confidence"] = "high"
            elif exc_wf:
                record["matched_workflow"] = exc.get("workflow")
                record["match_confidence"] = "partial"

            # Scan message+stack for workflow names
            if not record["matched_workflow"]:
                combined = f"{exc.get('message','')} {exc.get('stack_trace','')}".lower()
                for wl, wn in wf_lower.items():
                    if wl in combined:
                        record["matched_workflow"] = wn
                        record["match_confidence"] = "partial"
                        break

            # Activity match
            exc_act = (exc.get("activity") or "").lower()
            if exc_act and exc_act in act_lower:
                record["matched_activity"] = act_lower[exc_act]
            elif exc_act:
                record["matched_activity"] = exc.get("activity")

            if not record["matched_activity"]:
                combined = f"{exc.get('message','')} {exc.get('stack_trace','')}".lower()
                for al, an in act_lower.items():
                    if al in combined and len(al) > 4:
                        record["matched_activity"] = an
                        break

            correlations.append(record)

        return correlations

    # ─────────────────────────── Heuristic causes (log-only) ─────────────────

    def _heuristic_from_log(
        self,
        exceptions: list[dict],
        correlations: list[dict],
    ) -> list[RootCause]:
        """
        Build heuristic causes STRICTLY from log exceptions.
        Evidence always references specific log data (type, message, timestamp, workflow).
        """
        found: list[RootCause] = []
        seen: set[str] = set()
        corr_map = {c["exception_type"]: c for c in correlations}

        for exc in exceptions:
            exc_type = exc.get("type", "")
            exc_msg  = exc.get("message", "")
            combined = f"{exc_type} {exc_msg}"

            matched_rule = None
            for key, rule in HEURISTIC_RULES.items():
                if key.lower() in combined.lower():
                    matched_rule = rule
                    break

            category = matched_rule["category"] if matched_rule else "UnhandledException"
            if category in seen:
                continue
            seen.add(category)

            corr = corr_map.get(exc_type, {})

            if matched_rule:
                cause = RootCause(
                    category=matched_rule["category"],
                    title=matched_rule["title"],
                    description=matched_rule["description"],
                    severity=matched_rule["severity"],
                    confidence=matched_rule["confidence"],
                    suggested_fix=matched_rule["suggested_fix"],
                    preventive_recommendations=matched_rule["preventive_recommendations"],
                )
            else:
                cause = RootCause(
                    category="UnhandledException",
                    title=f"Runtime Error: {exc_type}",
                    description=(
                        f"An unhandled {exc_type} was raised at runtime"
                        + (f" in workflow '{corr.get('matched_workflow')}'" if corr.get("matched_workflow") else "")
                        + "."
                    ),
                    severity="high",
                    confidence=0.75,
                    suggested_fix=(
                        f"Wrap the failing activity in a Try-Catch. Review: {exc_msg[:200]}"
                    ),
                    preventive_recommendations=[
                        "Add a Global Exception Handler to prevent silent crashes",
                        "Log all exceptions with full stack traces",
                    ],
                )

            # Evidence strictly from the log
            cause.evidence = []
            cause.evidence.append(f"Exception type (from log): {exc_type}")
            if exc_msg:
                cause.evidence.append(f"Error message: {exc_msg[:300]}")
            if exc.get("timestamp"):
                cause.evidence.append(f"Timestamp: {exc['timestamp']}")
            if corr.get("matched_workflow"):
                cause.evidence.append(f"Failed workflow: {corr['matched_workflow']}")
            if corr.get("matched_activity"):
                cause.evidence.append(f"Failed activity: {corr['matched_activity']}")
            if exc.get("stack_trace"):
                cause.evidence.append(f"Stack trace: {str(exc['stack_trace'])[:300]}")

            cause.affected_workflow = corr.get("matched_workflow") or exc.get("workflow")
            cause.affected_activity = corr.get("matched_activity") or exc.get("activity")

            found.append(cause)

        return found

    # ─────────────────────────── Structural analysis ─────────────────────────

    def _structural_analysis(self, project_info: dict) -> list[RootCause]:
        """Full structural analysis when NO log is present."""
        causes: list[RootCause] = []
        platform = project_info["platform"]
        pkg_names  = project_info.get("package_names", [])
        workflows  = project_info.get("workflows_raw", [])
        wf_names   = project_info.get("workflow_names", [])
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
                description=(
                    f"The project platform could not be determined (detected: '{platform}'). "
                    "Analysis may be incomplete."
                ),
                severity="medium", confidence=0.60,
                evidence=[f"Original filename: {project_info.get('original_filename', 'unknown')}"],
                suggested_fix="Ensure the uploaded file is a valid RPA project archive.",
                preventive_recommendations=[
                    "Upload a ZIP containing project.json (UiPath), definition.json (Power Automate), "
                    ".bprelease (Blue Prism), or bot.json (Automation Anywhere)"
                ],
            ))
        return causes

    def _structural_analysis_as_risks(self, project_info: dict) -> list[RootCause]:
        """
        Structural analysis when a log IS present.
        All findings are tagged as 'Potential Risk' with reduced confidence
        to distinguish them from confirmed runtime causes from the log.
        """
        raw = self._structural_analysis(project_info)
        risks: list[RootCause] = []
        for cause in raw:
            if cause.category == "ProjectInfo":
                risks.append(cause)
                continue
            risk = cause.model_copy()
            risk.title = f"[Static Risk] {risk.title}"
            risk.description = (
                f"(Potential risk — not confirmed by log) {risk.description}"
            )
            risk.confidence = round(max(risk.confidence - 0.15, 0.40), 2)
            risks.append(risk)
        return risks

    def _structural_uipath(self, project_info, pkg_names, workflows, wf_names, activities) -> list[RootCause]:
        causes: list[RootCause] = []
        meta = project_info.get("metadata", {})

        if pkg_names and not any("UiPath.System.Activities" in p for p in pkg_names):
            causes.append(RootCause(
                category="MissingPackage",
                title="Core Package UiPath.System.Activities Missing",
                description=(
                    "project.json dependencies do not include UiPath.System.Activities, "
                    "which is required for all UiPath workflows to execute."
                ),
                severity="critical", confidence=0.95,
                evidence=[f"Packages found: {', '.join(pkg_names[:8]) or 'none'}"],
                suggested_fix="Open Manage Packages in UiPath Studio and install UiPath.System.Activities.",
                preventive_recommendations=["Verify all dependencies before deploying"],
            ))

        main_wf = next((w for w in workflows if "main" in w.get("filename", "").lower()), None)
        if main_wf:
            flat_main = self._flatten_activities(main_wf.get("activities", []))
            has_tc = any(
                "trycatch" in a.get("name", "").lower()
                or "try" in a.get("display_name", "").lower()
                for a in flat_main
            )
            if not has_tc:
                causes.append(RootCause(
                    category="MissingExceptionHandler",
                    title="No Try-Catch in Main.xaml",
                    description=(
                        f"'{main_wf.get('filename')}' does not contain a TryCatch activity. "
                        "Any unhandled exception will terminate the process without cleanup or logging."
                    ),
                    severity="high", confidence=0.88,
                    evidence=[
                        f"Main workflow: {main_wf.get('filename')}",
                        f"Activity count in Main: {main_wf.get('activity_count', 0)}",
                    ],
                    suggested_fix=(
                        "Wrap the main Sequence in a TryCatch. In the Catches block, "
                        "log the exception and set a failure exit status."
                    ),
                    preventive_recommendations=[
                        "Register a Global Exception Handler",
                        "Follow REFramework pattern for robust exception management",
                    ],
                ))

        log_acts = [a for a in activities if "log" in a.lower()]
        if not log_acts and workflows:
            causes.append(RootCause(
                category="MissingLogging",
                title="No Log Message Activities Found",
                description=(
                    f"None of the {len(workflows)} workflow(s) contain Log Message activities, "
                    "making runtime failures difficult to diagnose."
                ),
                severity="medium", confidence=0.85,
                evidence=[f"Workflows scanned: {', '.join(wf_names[:5]) or 'none'}"],
                suggested_fix="Add Log Message activities at process start, key decision points, and all exception handlers.",
                preventive_recommendations=[
                    "Enable verbose logging in Robot settings",
                    "Use structured log fields for machine-readable audit trails",
                ],
            ))

        refw = ["init", "gettransaction", "process", "endprocess"]
        wf_lower_str = " ".join(wf_names).lower()
        if not any(r in wf_lower_str for r in refw) and len(workflows) > 2:
            causes.append(RootCause(
                category="ArchitectureIssue",
                title="REFramework Pattern Not Detected",
                description=(
                    f"Project has {len(workflows)} workflows but does not follow the "
                    "REFramework (Init/GetTransaction/Process/EndProcess) structure."
                ),
                severity="low", confidence=0.70,
                evidence=[f"Workflows: {', '.join(wf_names[:6])}"],
                suggested_fix="Adopt the UiPath REFramework template for production automation.",
                preventive_recommendations=[
                    "Download REFramework from UiPath Marketplace",
                    "Separate Init, Process, and End logic into dedicated workflows",
                ],
            ))

        version = meta.get("version") or meta.get("studio_version")
        if version:
            causes.append(RootCause(
                category="ProjectInfo",
                title=f"Project: {project_info['name']}",
                description=(
                    f"UiPath project '{project_info['name']}' "
                    f"(version {version}, Studio {meta.get('studio_version', 'unknown')}). "
                    f"Contains {len(workflows)} workflow(s) and {len(pkg_names)} package(s)."
                ),
                severity="low", confidence=1.0,
                evidence=[
                    f"Studio version: {meta.get('studio_version', 'unknown')}",
                    f"Project version: {version}",
                    f"Main workflow: {meta.get('main_workflow', 'unknown')}",
                    f"Author: {meta.get('author', 'unknown')}",
                ],
                suggested_fix="Verify the correct version is deployed to the target environment.",
                preventive_recommendations=["Pin project and package versions before deploying to production"],
            ))

        return causes

    def _structural_pa(self, project_info) -> list[RootCause]:
        causes: list[RootCause] = []
        meta  = project_info.get("metadata", {})
        wf    = project_info.get("workflows_raw", {})
        actions = wf.get("actions", []) if isinstance(wf, dict) else []
        action_types = [a.get("type", "").lower() for a in actions]

        if not any(eh in " ".join(action_types) for eh in ["scope", "runafter", "terminate"]):
            causes.append(RootCause(
                category="MissingExceptionHandler",
                title="No Error Handling in Power Automate Flow",
                description="The flow lacks Scope or 'Configure run after' error-handling actions.",
                severity="high", confidence=0.85,
                evidence=[f"Actions found: {len(actions)}", f"Action types: {', '.join(set(action_types[:8]))}"],
                suggested_fix="Add a Scope action around critical steps with a 'has failed' run-after path.",
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
            stages: list[dict] = []
            for w in wf_struct:
                stages += w.get("stages", [])
        else:
            stages = wf_struct.get("stages", [])

        stage_types = [s.get("type", "").lower() for s in stages]

        if "exception" not in " ".join(stage_types):
            causes.append(RootCause(
                category="MissingExceptionHandler",
                title="No Exception Stage in Blue Prism Process",
                description="No Exception stages detected — runtime errors will terminate the process with no cleanup.",
                severity="high", confidence=0.88,
                evidence=[f"Total stages: {len(stages)}", f"Stage types: {', '.join(set(stage_types[:8]))}"],
                suggested_fix="Add Exception stages to all process pages, connected to Recovery paths.",
                preventive_recommendations=["Follow Blue Prism's exception handling framework"],
            ))

        if "start" not in " ".join(stage_types) or "end" not in " ".join(stage_types):
            causes.append(RootCause(
                category="StructuralError",
                title="Missing Start or End Stage",
                description="Blue Prism process is missing a Start or End stage — execution will be prevented.",
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
            commands: list[dict] = []
            for w in wf_struct:
                commands += w.get("commands", [])
        else:
            commands = wf_struct.get("commands", [])

        cmd_types = [c.get("type", "").lower() for c in commands]

        if not any("error" in t or "try" in t or "catch" in t for t in cmd_types):
            causes.append(RootCause(
                category="MissingExceptionHandler",
                title="No Error Handling Commands in Bot",
                description="The bot does not contain Try/Catch error-handling commands.",
                severity="high", confidence=0.85,
                evidence=[f"Commands found: {len(commands)}"],
                suggested_fix="Wrap risky operations in Try/Catch error-handling blocks.",
                preventive_recommendations=["Handle both expected and unexpected errors separately"],
            ))

        if not any("log" in t or "message" in t for t in cmd_types):
            causes.append(RootCause(
                category="MissingLogging",
                title="No Logging Commands in Bot",
                description="No Log to File or message commands found in the bot.",
                severity="medium", confidence=0.82,
                evidence=[f"Commands found: {len(commands)}"],
                suggested_fix="Add Log to File commands at key process milestones.",
                preventive_recommendations=["Log start, end, and all exceptions to a centralised log file"],
            ))
        return causes

    # ─────────────────────────── Standards → causes ───────────────────────────

    def _standards_to_causes(
        self,
        standards_result: Any,
        log_correlation: list[dict],
        log_confirmed_only: bool = False,
    ) -> list[RootCause]:
        """
        Convert standards violations to RCA causes.
        When log_confirmed_only=True, only inject causes where the violation location
        matches a workflow/activity referenced in the log correlation results.
        """
        causes: list[RootCause] = []
        seen: set[str] = set()
        confirmed_workflows = {
            (c.get("matched_workflow") or "").lower()
            for c in log_correlation
            if c.get("matched_workflow")
        }
        confirmed_activities = {
            (c.get("matched_activity") or "").lower()
            for c in log_correlation
            if c.get("matched_activity")
        }

        for v in getattr(standards_result, "violations", []):
            if v.severity not in ("critical", "high"):
                continue
            key = f"Standards:{v.rule_id}"
            if key in seen:
                continue

            if log_confirmed_only:
                loc = v.location.lower()
                if loc not in confirmed_workflows and loc not in confirmed_activities:
                    continue  # Not confirmed by log — skip as runtime cause

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
                preventive_recommendations=[
                    f"Fix rule {v.rule_id} before deploying to production"
                ],
            ))

        return causes

    # ─────────────────────────── AI analysis ─────────────────────────────────

    async def _ai_analysis(
        self,
        project_info: dict,
        exceptions: list[dict],
        heuristic_causes: list[RootCause],
        has_log: bool = False,
    ) -> tuple[list[RootCause], str]:
        from openai import AsyncOpenAI
        from tenacity import retry, stop_after_attempt, wait_exponential

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        heuristic_summary = "\n".join(
            f"- {c.title}: {c.description}" for c in heuristic_causes
        )
        exceptions_text = json.dumps(exceptions[:10], indent=2, default=str)
        project_text = json.dumps({
            "name":           project_info["name"],
            "platform":       project_info["platform"],
            "workflow_count": project_info["workflow_count"],
            "workflow_names": project_info["workflow_names"][:10],
            "package_names":  project_info["package_names"][:10],
            "metadata":       project_info["metadata"],
        }, indent=2, default=str)

        if has_log:
            analysis_instruction = """
You are an expert RPA Automation Debugger performing LOG-FIRST analysis.

RULES:
1. The log exceptions below are the PRIMARY source of truth.
2. Base all runtime root causes ONLY on evidence present in the log exceptions.
3. Never assume errors not present in the log.
4. Reference actual workflow names, activity names, and exception messages from the data.
5. Do NOT list coding standards violations as runtime root causes.
6. Identify the failure category: Application Issue / Infrastructure / Business Data /
   Configuration / Credentials / Network / Package Dependency / Coding Logic / Environment / Permissions.
"""
        else:
            analysis_instruction = """
You are an expert RPA Automation Debugger performing STATIC analysis (no log provided).

RULES:
1. Perform static code review of the project structure.
2. Identify coding standards issues, missing exception handlers, hardcoded values,
   potential runtime risks, performance concerns, and security issues.
3. Label all findings as 'potential risk' — NOT confirmed runtime failures.
4. Reference actual workflow names, activity names, and package names from the project data.
"""

        prompt = f"""{analysis_instruction}

PROJECT:
{project_text}

EXCEPTIONS FROM LOG:
{exceptions_text if has_log else "No log provided."}

INITIAL HEURISTIC FINDINGS:
{heuristic_summary if heuristic_summary else "None detected"}

Respond with JSON (exact structure):
{{
  "root_causes": [
    {{
      "category": "NullReference|SelectorFailure|Timeout|MissingPackage|FileNotFound|MissingArgument|CredentialIssue|NetworkOrAPIFailure|QueueFailure|ConfigurationIssue|BusinessRuleException|UnhandledException|MissingExceptionHandler|ArchitectureIssue|CodingStandardsViolation|ProjectInfo",
      "title": "concise title referencing actual workflow/activity name if known",
      "description": "detailed explanation referencing specific project artefacts",
      "severity": "critical|high|medium|low",
      "confidence": 0.0,
      "evidence": ["specific evidence from log or project structure"],
      "affected_workflow": "exact workflow filename or null",
      "affected_activity": "exact activity name or null",
      "suggested_fix": "specific actionable fix for THIS project",
      "preventive_recommendations": ["list of preventive measures"]
    }}
  ]
}}"""

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
        causes: list[RootCause] = []
        for rc_data in data.get("root_causes", []):
            try:
                causes.append(RootCause(**rc_data))
            except Exception:
                pass
        return causes, raw_text

    # ─────────────────────────── Merging & recommendations ───────────────────

    def _merge_causes(
        self,
        ai_causes: list[RootCause],
        primary_causes: list[RootCause],
        secondary_causes: list[RootCause],
    ) -> list[RootCause]:
        """
        Merge strategy:
        - AI causes take precedence (most specific, project-aware).
        - primary_causes fill gaps not covered by AI.
        - secondary_causes (static risks when log present) are appended at the end.
        - ProjectInfo causes always last.
        """
        if ai_causes:
            ai_cats = {c.category for c in ai_causes}
            primary_fill = [c for c in primary_causes if c.category not in ai_cats]
            merged = list(ai_causes) + primary_fill
        else:
            merged = list(primary_causes)

        # Add secondary (static) causes
        existing_cats = {c.category for c in merged}
        merged += [c for c in secondary_causes if c.category not in existing_cats]

        info   = [c for c in merged if c.category == "ProjectInfo"]
        others = [c for c in merged if c.category != "ProjectInfo"]
        others.sort(key=lambda c: (SEVERITY_ORDER.get(c.severity, 4), -c.confidence))
        return (others + info)[:14]

    def _build_recommendations(
        self,
        causes: list[RootCause],
        project_info: dict,
        has_log: bool,
        runtime_analysis: RuntimeAnalysis,
    ) -> list[str]:
        recs: list[str] = []

        if has_log and runtime_analysis.suggested_fixes:
            for fix in runtime_analysis.suggested_fixes[:4]:
                recs.append(f"[RUNTIME FIX] {fix}")

        for cause in causes:
            if cause.suggested_fix and cause.category != "ProjectInfo":
                prefix = (
                    "[STATIC RISK]"
                    if "[Static Risk]" in cause.title or not has_log
                    else "[CONFIRMED]"
                )
                recs.append(f"{prefix} {cause.title}: {cause.suggested_fix}")

        platform = project_info.get("platform", "")
        if platform == "uipath":
            recs += [
                "Implement REFramework for production-grade automation",
                "Enable detailed logging in Robot settings",
                "Use Orchestrator Assets for all configurable values",
                "Set up email/Teams alerts for unhandled exceptions",
            ]
        elif platform == "power_automate":
            recs += [
                "Use error handling Scope actions in every cloud flow",
                "Enable flow run history and monitoring",
                "Use environment variables instead of hardcoded values",
            ]
        elif platform == "blue_prism":
            recs += [
                "Use Exception and Recovery stages on every process page",
                "Enable process logging in Control Room",
            ]
        elif platform == "automation_anywhere":
            recs += [
                "Use the Credential Vault for all sensitive values",
                "Add error handling and logging commands to all bots",
            ]

        return list(dict.fromkeys(recs))[:20]

    # ─────────────────────────── Helpers ─────────────────────────────────────

    def _flatten_activities(self, activities: list[dict], depth: int = 0) -> list[dict]:
        result: list[dict] = []
        for act in activities:
            result.append(act)
            children = act.get("children")
            if children and depth < 10:
                result.extend(self._flatten_activities(children, depth + 1))
        return result
