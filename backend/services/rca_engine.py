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
    rpa_tool: str = ""                    # identified by AI
    ai_narrative: dict = field(default_factory=dict)  # structured AI analysis detail


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

        # has_log = True whenever a log file was actually uploaded OR pasted,
        # even if the log has zero exceptions (success run).
        has_log = bool(log_files) or bool(pasted_error_text and pasted_error_text.strip())

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

        ai_narrative: dict = {}
        rpa_tool: str = ""

        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            try:
                ai_causes, raw_response = await self._ai_analysis(
                    project_info, exception_data, heuristic_causes,
                    has_log=has_log,
                )
                # Parse the structured narrative from raw_response
                try:
                    ai_narrative = json.loads(raw_response) if raw_response else {}
                    rpa_tool = ai_narrative.get("rpa_tool", "")
                except Exception:
                    ai_narrative = {}
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
            rpa_tool=rpa_tool,
            ai_narrative=ai_narrative,
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
        """
        Collect ALL exceptions from all log files.
        - Reads the full all_exceptions list from exception_summary (no cap).
        - Also reads execution_trace for additional error entries.
        - Deduplicates by (type, message[:100]).
        """
        exceptions: list[dict] = []
        seen: set[tuple] = set()

        def _add(exc: dict) -> None:
            key = (exc.get("type", ""), (exc.get("message") or "")[:100])
            if key not in seen:
                seen.add(key)
                exceptions.append(exc)

        for lf in log_files:
            summary = lf.exception_summary or {}

            # Primary exception first (highest priority)
            primary = summary.get("primary_exception")
            if primary:
                _add(primary)

            # ALL exceptions from the summary (was [:30] before — now no cap)
            for exc in summary.get("all_exceptions") or []:
                _add(exc)

            # Additional evidence from execution trace
            # execution_trace is stored as {"trace": [...]} in the DB column
            trace_data = lf.execution_trace or {}
            trace_list = trace_data.get("trace", []) if isinstance(trace_data, dict) else []
            for entry in trace_list:  # no cap — read all
                if entry.get("is_error") and entry.get("message"):
                    _add({
                        "type":       entry.get("exception_type") or "RuntimeError",
                        "message":    entry["message"][:1000],
                        "timestamp":  entry.get("timestamp"),
                        "workflow":   entry.get("workflow"),
                        "activity":   entry.get("activity"),
                        "stack_trace": entry.get("stack_trace"),
                    })

        return exceptions

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
        # has_log reflects whether a log was provided, independent of exception count.
        ra = RuntimeAnalysis(has_log=bool(log_files))
        if not exceptions:
            # Success scenario — log uploaded but no errors detected
            if log_files:
                total_entries = sum(
                    len((getattr(lf, "parsed_entries", None) or {}).get("entries", []))
                    for lf in log_files
                )
                ra.root_cause_summary = (
                    "No exceptions detected in the uploaded log — the automation ran successfully."
                )
                ra.evidence_from_log = [
                    f"Log file(s): {', '.join(getattr(lf, 'filename', '?') for lf in log_files)}",
                    f"Total log entries parsed: {total_entries}",
                    "No ERROR or FATAL entries found.",
                    "No exceptions extracted.",
                ]
                ra.suggested_fixes = ["No fixes required — execution completed without errors."]
                ra.validation_steps = [
                    "Review the log entries to confirm all expected steps executed.",
                    "Verify the output/results of the automation are as expected.",
                ]
                ra.failure_category = "None — Success"
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
        ra.all_exceptions = exceptions  # ALL exceptions, no cap

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
        # Additional error context from execution trace — read ALL error entries
        for lf in log_files:
            trace_data = getattr(lf, "execution_trace", None) or {}
            trace_list = trace_data.get("trace", []) if isinstance(trace_data, dict) else []
            for entry in trace_list:
                if entry.get("is_error") and entry.get("message"):
                    ts = entry.get("timestamp") or "?"
                    evidence.append(f"[{ts}] {entry['message'][:300]}")
        ra.evidence_from_log = evidence[:20]  # increased from 12 to 20

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
        Coding standards violations NEVER appear as root causes.
        Per expert rules: coding standard analysis belongs under the
        Coding Standards tab ONLY, not in Root Cause Analysis.
        This method returns an empty list always.
        """
        return []

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
        exceptions_text = json.dumps(exceptions[:15], indent=2, default=str)
        platform = project_info.get("platform", "unknown")
        project_text = json.dumps({
            "name":           project_info["name"],
            "platform":       platform,
            "workflow_count": project_info["workflow_count"],
            "workflow_names": project_info["workflow_names"][:15],
            "package_names":  project_info["package_names"][:15],
            "activity_names": project_info.get("activity_names", [])[:30],
            "metadata":       project_info["metadata"],
        }, indent=2, default=str)

        # ── Platform-specific activity vocabulary ────────────────────────────
        platform_context = {
            "uipath": """
For UiPath, identify:
- XAML workflow file (e.g. Main.xaml, Process.xaml, InitAllApplications.xaml)
- REFramework state: Init / Get Transaction Data / Process Transaction / End Process
- Container type: Sequence / Flowchart / State Machine
- Likely activity: Read Range, Click, Type Into, Invoke Workflow File,
  Use Application/Browser, Assign, For Each, HTTP Request, Deserialize JSON,
  Get Credential, Log Message, Send SMTP Mail, Data Table operations""",
            "blue_prism": """
For Blue Prism, identify:
- Process name and Page name (e.g. Main Page, Initialise, Clean Up)
- Stage type: Navigate / Read / Write / Wait / Decision / Calculation / Code / Exception / Recovery
- Utility VBO being called (e.g. MS Excel VBO, Credentials VBO, File Management VBO)
- Business Object and Action invoked""",
            "automation_anywhere": """
For Automation Anywhere, identify:
- TaskBot or MetaBot name
- Package and action: Excel (Open/Read/Write), Browser (Open/Navigate),
  Object Cloning, Database, File/Folder, String, Loop, Error Handler
- MetaBot DLL action if applicable""",
            "power_automate": """
For Power Automate Desktop, identify:
- Flow and Subflow name
- Action type: Launch Excel / Read from Excel / Click / Send Keys /
  Launch Web Browser / Web Automation / Set Variable / Loop / Condition / Exception Block
For Power Automate Cloud, identify:
- Trigger / Scope / Action / Apply to Each / Condition / HTTP
- Connector: SharePoint / Outlook / Dataverse / Teams / OneDrive""",
        }.get(platform, "Identify the likely workflow, stage, and activity based on the exception.")

        if has_log:
            system_instruction = f"""You are an expert RPA Automation Debugger with deep knowledge of UiPath, Blue Prism, Automation Anywhere, and Power Automate.

Your task is LOG-FIRST debugging: correlate the execution log with the uploaded automation project.

STRICT RULES:
1. The log exceptions are the PRIMARY and ONLY source of truth for runtime root causes.
2. Base every root cause STRICTLY on evidence present in the log — never assume errors not in the log.
3. Do NOT include coding standards violations in root causes — those belong in a separate tab.
4. Do NOT generate generic root causes — every finding must reference actual log evidence.
5. Map each exception to the most likely workflow, stage/state/page, and activity/action.
6. Classify the failure: Application Issue / Infrastructure / Business Data / Configuration /
   Credentials / Network / Package Dependency / Coding Logic / Permissions / Environment.

{platform_context}

For each root cause, produce the structured analysis following this expert format:
- What operation was being performed
- Which workflow/process and which stage/state/activity most likely failed
- Why it failed (infer from log evidence + project structure)
- What the bot was doing immediately before the failure
- Confidence level with reasoning (High/Medium/Low)"""

        else:
            system_instruction = f"""You are an expert RPA Automation Debugger with deep knowledge of UiPath, Blue Prism, Automation Anywhere, and Power Automate.

Your task is STATIC analysis of the project structure — no execution log is available.

STRICT RULES:
1. Identify potential runtime risks, missing error handlers, and structural issues.
2. All findings are POTENTIAL risks — NOT confirmed runtime failures.
3. Do NOT include coding standards violations in root causes — those belong in a separate tab.
4. Reference actual workflow names, activity names, and package names from the project data.
5. For each risk, identify the most likely workflow and activity where it could fail.
6. Do NOT generate generic findings — every finding must reference specific project artefacts.

{platform_context}"""

        prompt = f"""{system_instruction}

PROJECT STRUCTURE:
{project_text}

{"EXCEPTIONS FROM LOG:" if has_log else "NO LOG PROVIDED — static analysis only."}
{exceptions_text if has_log else ""}

{"HEURISTIC PRE-ANALYSIS:" if heuristic_summary else ""}
{heuristic_summary if heuristic_summary else ""}

Respond with JSON (exact structure — do not add extra keys):
{{
  "rpa_tool": "UiPath | Blue Prism | Automation Anywhere | Power Automate Desktop | Power Automate Cloud | Unknown",
  "runtime_error_summary": "one-sentence summary of the primary runtime failure (or 'No log — static analysis' if no log)",
  "root_causes": [
    {{
      "category": "NullReference|SelectorFailure|Timeout|MissingPackage|FileNotFound|MissingArgument|CredentialIssue|NetworkOrAPIFailure|QueueFailure|ConfigurationIssue|BusinessRuleException|UnhandledException|MissingExceptionHandler|ArchitectureIssue|PermissionIssue|EnvironmentIssue|ProjectInfo",
      "title": "concise title — must reference actual workflow/activity name",
      "description": "detailed explanation referencing specific project artefacts from the data above",
      "severity": "critical|high|medium|low",
      "confidence": 0.0,
      "confidence_label": "High|Medium|Low",
      "confidence_reasoning": "why you assigned this confidence level",
      "failure_category": "Application Issue|Infrastructure|Business Data|Configuration|Credentials|Network|Package Dependency|Coding Logic|Permissions|Environment",
      "evidence": ["specific evidence line from log or project structure — must be concrete"],
      "affected_workflow": "exact workflow/process/page filename or null",
      "affected_activity": "exact activity/stage/action name or null",
      "what_was_happening": "what operation the bot was performing when this failed",
      "why_it_failed": "inferred reason based on log evidence and project context",
      "suggested_checks": ["step-by-step validation checks"],
      "suggested_fix": "specific actionable fix referencing this project's actual workflow/activity names",
      "preventive_recommendations": ["preventive measures specific to this platform and project"]
    }}
  ]
}}

IMPORTANT: Do NOT include any CodingStandardsViolation category items — those go in a separate tab."""

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
            # Skip any coding standards violations that AI may have included
            if rc_data.get("category") == "CodingStandardsViolation":
                continue
            # Extract RootCause-compatible fields only (ignore extra AI fields)
            rc_fields = {
                "category":                  rc_data.get("category", "UnhandledException"),
                "title":                     rc_data.get("title", ""),
                "description":               rc_data.get("description", ""),
                "severity":                  rc_data.get("severity", "medium"),
                "confidence":                float(rc_data.get("confidence", 0.7)),
                "evidence":                  rc_data.get("evidence", []),
                "affected_workflow":         rc_data.get("affected_workflow"),
                "affected_activity":         rc_data.get("affected_activity"),
                "suggested_fix":             rc_data.get("suggested_fix", ""),
                "preventive_recommendations": rc_data.get("preventive_recommendations", []),
            }
            # Enrich description with AI's deeper analysis fields
            what_was = rc_data.get("what_was_happening", "")
            why      = rc_data.get("why_it_failed", "")
            conf_rsn = rc_data.get("confidence_reasoning", "")
            fail_cat = rc_data.get("failure_category", "")
            if what_was:
                rc_fields["description"] += f"\n\nOperation: {what_was}"
            if why:
                rc_fields["description"] += f"\nWhy it failed: {why}"
            if fail_cat:
                rc_fields["evidence"] = [f"Failure category: {fail_cat}"] + rc_fields["evidence"]
            if conf_rsn:
                rc_fields["evidence"].append(f"Confidence reasoning: {conf_rsn}")
            # Add suggested_checks to preventive_recommendations
            for chk in rc_data.get("suggested_checks", []):
                if chk not in rc_fields["preventive_recommendations"]:
                    rc_fields["preventive_recommendations"].append(chk)
            try:
                causes.append(RootCause(**rc_fields))
            except Exception:
                pass

        # Build a rich structured narrative stored in raw_ai_response
        structured = {
            "rpa_tool":             data.get("rpa_tool", "Unknown"),
            "runtime_error_summary": data.get("runtime_error_summary", ""),
            "root_causes_detail":   [
                {
                    "title":               rc.get("title"),
                    "affected_workflow":   rc.get("affected_workflow"),
                    "affected_activity":   rc.get("affected_activity"),
                    "what_was_happening":  rc.get("what_was_happening"),
                    "why_it_failed":       rc.get("why_it_failed"),
                    "failure_category":    rc.get("failure_category"),
                    "confidence_label":    rc.get("confidence_label"),
                    "confidence_reasoning": rc.get("confidence_reasoning"),
                    "suggested_checks":    rc.get("suggested_checks", []),
                    "suggested_fix":       rc.get("suggested_fix"),
                }
                for rc in data.get("root_causes", [])
                if rc.get("category") != "CodingStandardsViolation"
            ],
        }
        return causes, json.dumps(structured, indent=2)

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
