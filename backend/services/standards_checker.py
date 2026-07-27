from __future__ import annotations

"""
RPA Coding Standards Checker
Inspects parsed project structure and flags activities/stages that violate
common RPA best-practice coding standards for each supported platform.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StandardsViolation:
    rule_id: str
    rule_name: str
    severity: str          # critical | high | medium | low
    description: str
    location: str          # workflow / stage / activity name
    location_type: str     # "workflow" | "activity" | "dependency" | "project"
    recommendation: str
    platform: str


@dataclass
class CodeError:
    error_type: str        # SyntaxError | MissingHandler | HardcodedValue | etc.
    title: str
    description: str
    severity: str
    location: str
    line_hint: str         # best-effort line/path hint
    fix: str


@dataclass
class StandardsResult:
    violations: list[StandardsViolation] = field(default_factory=list)
    code_errors: list[CodeError] = field(default_factory=list)
    score: float = 100.0   # 0–100, deducted per violation
    passed_rules: list[str] = field(default_factory=list)
    summary: str = ""


# ─────────────────────────────────────────── Rules catalogue ─────────────────

UIPATH_RULES = [
    # Structural
    {
        "id": "UP001", "name": "No Try-Catch in Main",
        "desc": "Main.xaml does not appear to use Try-Catch / Global Exception Handler.",
        "sev": "high",
        "rec": "Wrap the main sequence in a Try-Catch or configure a Global Exception Handler to prevent unhandled crashes.",
    },
    {
        "id": "UP002", "name": "Hardcoded Credentials Detected",
        "desc": "A workflow contains activities with passwords or credential strings appearing hardcoded.",
        "sev": "critical",
        "rec": "Store all credentials in UiPath Orchestrator Assets or Windows Credential Manager. Never hardcode.",
    },
    {
        "id": "UP003", "name": "No Log Message Activities",
        "desc": "No Log Message activities were found in the project workflows.",
        "sev": "medium",
        "rec": "Add Log Message activities at key checkpoints (Start, Decision, Exception) to aid debugging.",
    },
    {
        "id": "UP004", "name": "Deep Activity Nesting",
        "desc": "A workflow has activities nested more than 5 levels deep, making it hard to read and maintain.",
        "sev": "medium",
        "rec": "Refactor deeply nested logic into separate Invoke Workflow File calls following the REFramework pattern.",
    },
    {
        "id": "UP005", "name": "No REFramework Pattern",
        "desc": "Project does not follow the standard REFramework (Init / Get Transaction / Process / End Process) structure.",
        "sev": "low",
        "rec": "For production RPA, adopt the UiPath REFramework template for reliability and maintainability.",
    },
    {
        "id": "UP006", "name": "Missing UiPath.System.Activities",
        "desc": "Core UiPath.System.Activities package is missing from project dependencies.",
        "sev": "critical",
        "rec": "Add UiPath.System.Activities via Manage Packages in UiPath Studio.",
    },
    {
        "id": "UP007", "name": "Outdated Package Versions",
        "desc": "One or more dependency packages appear to use pre-release or very old version strings.",
        "sev": "low",
        "rec": "Update packages to their latest stable versions to benefit from bug fixes and security patches.",
    },
    {
        "id": "UP008", "name": "Workflow Without Display Name",
        "desc": "One or more activities are missing meaningful DisplayName values.",
        "sev": "low",
        "rec": "Set descriptive DisplayName on all activities so the execution log is readable.",
    },
    {
        "id": "UP009", "name": "No Input Argument Validation",
        "desc": "Workflows accept In/InOut arguments but no validation (If / Throw) is performed at entry.",
        "sev": "medium",
        "rec": "Add an 'If argument Is Nothing Then Throw' check at the start of every workflow that accepts arguments.",
    },
    {
        "id": "UP010", "name": "Selector Without Wildcards",
        "desc": "UI automation selectors appear to use fully static attributes (no wildcards), which are fragile.",
        "sev": "high",
        "rec": "Replace volatile attributes (idx, title) with wildcards (*) in selectors to improve robustness.",
    },
]

POWER_AUTOMATE_RULES = [
    {
        "id": "PA001", "name": "No Error Handling Action",
        "desc": "The flow does not contain any 'Configure run after' or Scope error-handling actions.",
        "sev": "high",
        "rec": "Add a 'Configure run after' setting on critical actions, or wrap in a Scope with error-handling steps.",
    },
    {
        "id": "PA002", "name": "Missing Flow Description",
        "desc": "The flow has no description set.",
        "sev": "low",
        "rec": "Add a description to explain the flow's purpose, trigger, and owner.",
    },
    {
        "id": "PA003", "name": "Hardcoded Environment Values",
        "desc": "Action parameters appear to contain hardcoded URLs, passwords, or connection strings.",
        "sev": "critical",
        "rec": "Use Environment Variables or Custom Connectors to avoid hardcoded values.",
    },
    {
        "id": "PA004", "name": "No Email/Teams Alert on Failure",
        "desc": "No notification action (Send Email / Post Teams message) was found for failure paths.",
        "sev": "medium",
        "rec": "Add an error-path notification step so stakeholders are alerted on failures.",
    },
]

BLUE_PRISM_RULES = [
    {
        "id": "BP001", "name": "Missing Exception Stage",
        "desc": "Process pages do not contain Exception stages for error handling.",
        "sev": "high",
        "rec": "Add Exception stages to every business object page and process page to handle unexpected errors gracefully.",
    },
    {
        "id": "BP002", "name": "No Recovery Stage",
        "desc": "Process does not have a Recovery stage to handle application crashes or unexpected states.",
        "sev": "high",
        "rec": "Implement a Recovery stage that brings the application back to a known state after an exception.",
    },
    {
        "id": "BP003", "name": "Missing Start/End Stages",
        "desc": "A process page is missing Start or End stages.",
        "sev": "critical",
        "rec": "Every page must have exactly one Start and one End stage as per Blue Prism conventions.",
    },
    {
        "id": "BP004", "name": "Unnamed Stages",
        "desc": "One or more stages have default or empty names.",
        "sev": "low",
        "rec": "Name all stages descriptively to improve readability and maintainability.",
    },
]

AA_RULES = [
    {
        "id": "AA001", "name": "No Error Handling Command",
        "desc": "The bot does not appear to include error handling commands.",
        "sev": "high",
        "rec": "Use Try/Catch error-handling commands around risky operations.",
    },
    {
        "id": "AA002", "name": "Hardcoded Credential in Bot",
        "desc": "Credential values appear to be hardcoded in bot commands.",
        "sev": "critical",
        "rec": "Use the Credential Vault to manage credentials securely.",
    },
    {
        "id": "AA003", "name": "No Logging Commands",
        "desc": "No Log to File or message commands were found.",
        "sev": "medium",
        "rec": "Add Log to File commands at key process steps for auditability.",
    },
]

PLATFORM_RULES: dict[str, list[dict]] = {
    "uipath": UIPATH_RULES,
    "power_automate": POWER_AUTOMATE_RULES,
    "blue_prism": BLUE_PRISM_RULES,
    "automation_anywhere": AA_RULES,
}

SEVERITY_DEDUCTIONS = {"critical": 20, "high": 10, "medium": 5, "low": 2}


class StandardsChecker:
    """Checks parsed project data against RPA coding standards."""

    def check(self, project: Any) -> StandardsResult:
        platform = str(
            project.platform.value
            if hasattr(project.platform, "value")
            else project.platform
        )
        result = StandardsResult()

        if platform == "uipath":
            self._check_uipath(project, result)
        elif platform == "power_automate":
            self._check_power_automate(project, result)
        elif platform == "blue_prism":
            self._check_blue_prism(project, result)
        elif platform == "automation_anywhere":
            self._check_aa(project, result)
        else:
            result.summary = "Unknown platform — no standards rules applied."
            return result

        # Compute score
        deduction = sum(
            SEVERITY_DEDUCTIONS.get(v.severity, 0) for v in result.violations
        )
        result.score = max(0.0, round(100.0 - deduction, 1))

        # Also scan for code errors
        self._detect_code_errors(project, platform, result)

        # Build summary
        n = len(result.violations)
        result.summary = (
            f"{n} standards violation{'s' if n != 1 else ''} found. "
            f"Standards score: {result.score}/100. "
            + (
                f"Critical issues: {sum(1 for v in result.violations if v.severity=='critical')}."
                if any(v.severity == "critical" for v in result.violations)
                else "No critical issues."
            )
        )

        return result

    # ───────────────────────── UiPath ─────────────────────────────────────────

    def _check_uipath(self, project: Any, result: StandardsResult) -> None:
        deps: dict = (project.dependencies or {})
        packages: list[dict] = deps.get("packages", [])
        pkg_names = [p.get("name", "") for p in packages]

        wf_struct: dict = project.workflow_structure or {}
        workflows: list[dict] = wf_struct.get("workflows", [])

        # UP006 — missing core package
        if not any("UiPath.System.Activities" in p for p in pkg_names):
            result.violations.append(StandardsViolation(
                rule_id="UP006", rule_name="Missing UiPath.System.Activities",
                severity="critical",
                description="UiPath.System.Activities package is absent from project dependencies.",
                location="project.json", location_type="dependency",
                recommendation="Add UiPath.System.Activities via Manage Packages.",
                platform="uipath",
            ))
        else:
            result.passed_rules.append("UP006")

        # UP007 — pre-release packages
        for pkg in packages:
            ver = str(pkg.get("version", ""))
            if "beta" in ver.lower() or "alpha" in ver.lower() or "rc" in ver.lower():
                result.violations.append(StandardsViolation(
                    rule_id="UP007", rule_name="Pre-release Package Version",
                    severity="low",
                    description=f"Package '{pkg.get('name')}' uses pre-release version '{ver}'.",
                    location=f"project.json → {pkg.get('name')}", location_type="dependency",
                    recommendation="Switch to stable release versions before deploying to production.",
                    platform="uipath",
                ))

        main_wf = next((w for w in workflows if "main" in w.get("filename", "").lower()), None)

        # Analyse each workflow
        for wf in workflows:
            filename = wf.get("filename", "Unknown.xaml")
            activities: list[dict] = wf.get("activities", [])
            flat = self._flatten_activities(activities)
            activity_names = [a.get("display_name", a.get("name", "")).lower() for a in flat]
            selectors = [a.get("selector", "") for a in flat if a.get("selector")]

            # UP003 — no log messages
            if not any("log" in n for n in activity_names):
                result.violations.append(StandardsViolation(
                    rule_id="UP003", rule_name="No Log Message Activities",
                    severity="medium",
                    description=f"Workflow '{filename}' contains no Log Message activities.",
                    location=filename, location_type="workflow",
                    recommendation="Add Log Message (Info/Verbose) at key steps for observability.",
                    platform="uipath",
                ))
            else:
                result.passed_rules.append(f"UP003:{filename}")

            # UP008 — activities without display name
            unnamed = [a for a in flat if not a.get("display_name") or a.get("display_name") == a.get("name")]
            if len(unnamed) > 3:
                result.violations.append(StandardsViolation(
                    rule_id="UP008", rule_name="Activities Without Display Names",
                    severity="low",
                    description=f"Workflow '{filename}' has {len(unnamed)} activities with missing or default display names.",
                    location=filename, location_type="activity",
                    recommendation="Set descriptive DisplayName on all activities.",
                    platform="uipath",
                ))

            # UP010 — static selectors
            static_selectors = [s for s in selectors if s and "*" not in s and "%" not in s]
            if static_selectors:
                result.violations.append(StandardsViolation(
                    rule_id="UP010", rule_name="Fully Static UI Selector",
                    severity="high",
                    description=f"Workflow '{filename}' has {len(static_selectors)} selector(s) with no wildcards.",
                    location=filename, location_type="activity",
                    recommendation="Replace volatile attributes (idx, title) with wildcard (*) patterns.",
                    platform="uipath",
                ))
            else:
                result.passed_rules.append(f"UP010:{filename}")

            # UP004 — deep nesting
            max_depth = self._max_nesting_depth(activities, 0)
            if max_depth > 5:
                result.violations.append(StandardsViolation(
                    rule_id="UP004", rule_name="Deep Activity Nesting",
                    severity="medium",
                    description=f"Workflow '{filename}' has activity nesting depth of {max_depth} (>5).",
                    location=filename, location_type="activity",
                    recommendation="Extract nested logic into separate invoked workflows.",
                    platform="uipath",
                ))

        # UP001 — Main has no try-catch
        if main_wf:
            flat_main = self._flatten_activities(main_wf.get("activities", []))
            has_trycatch = any("trycatch" in a.get("name", "").lower() or "try" in a.get("display_name", "").lower() for a in flat_main)
            if not has_trycatch:
                result.violations.append(StandardsViolation(
                    rule_id="UP001", rule_name="No Try-Catch in Main Workflow",
                    severity="high",
                    description="Main.xaml does not appear to contain a TryCatch activity.",
                    location="Main.xaml", location_type="workflow",
                    recommendation="Wrap the main sequence in a TryCatch or register a Global Exception Handler.",
                    platform="uipath",
                ))
            else:
                result.passed_rules.append("UP001")

        # UP005 — REFramework check
        wf_names = [w.get("filename", "").lower() for w in workflows]
        refw_indicators = ["init", "gettransaction", "process", "endprocess", "settransactionstatus"]
        if not any(ind in " ".join(wf_names) for ind in refw_indicators) and len(workflows) > 1:
            result.violations.append(StandardsViolation(
                rule_id="UP005", rule_name="No REFramework Pattern Detected",
                severity="low",
                description="Project does not appear to use the UiPath REFramework structure.",
                location="project", location_type="project",
                recommendation="Adopt REFramework for production RPA: Init → GetTransaction → Process → EndProcess.",
                platform="uipath",
            ))

    # ───────────────────────── Power Automate ─────────────────────────────────

    def _check_power_automate(self, project: Any, result: StandardsResult) -> None:
        wf_struct: dict = project.workflow_structure or {}
        actions: list[dict] = wf_struct.get("actions", [])
        action_types = [a.get("type", "").lower() for a in actions]

        # PA001 — no error handling
        error_handlers = ["scope", "runafter", "terminate", "try"]
        if not any(eh in " ".join(action_types) for eh in error_handlers):
            result.violations.append(StandardsViolation(
                rule_id="PA001", rule_name="No Error Handling",
                severity="high",
                description="Flow does not contain any Scope or error-handling actions.",
                location="flow", location_type="workflow",
                recommendation="Use 'Configure run after' or a Scope action for error paths.",
                platform="power_automate",
            ))
        else:
            result.passed_rules.append("PA001")

        # PA002 — missing description
        meta = project.project_metadata or {}
        if not meta.get("name") and not meta.get("description"):
            result.violations.append(StandardsViolation(
                rule_id="PA002", rule_name="Missing Flow Description",
                severity="low",
                description="Flow metadata has no description.",
                location="flow metadata", location_type="project",
                recommendation="Set a meaningful description explaining the flow's purpose.",
                platform="power_automate",
            ))

        # PA004 — no notifications
        notify_types = ["sendmail", "postmessage", "send_email", "notification"]
        if not any(nt in " ".join(action_types) for nt in notify_types):
            result.violations.append(StandardsViolation(
                rule_id="PA004", rule_name="No Failure Notification",
                severity="medium",
                description="No email or Teams notification action found for failure scenarios.",
                location="flow", location_type="workflow",
                recommendation="Add a notification action on the error path so stakeholders are alerted.",
                platform="power_automate",
            ))

    # ───────────────────────── Blue Prism ─────────────────────────────────────

    def _check_blue_prism(self, project: Any, result: StandardsResult) -> None:
        wf_struct: dict = project.workflow_structure or {}
        stages: list[dict] = wf_struct.get("stages", [])
        stage_types = [s.get("type", "").lower() for s in stages]
        stage_names = [s.get("name", "").lower() for s in stages]

        # BP001 — no exception stages
        if "exception" not in " ".join(stage_types):
            result.violations.append(StandardsViolation(
                rule_id="BP001", rule_name="No Exception Stage",
                severity="high",
                description="No Exception stages found in process pages.",
                location="process", location_type="workflow",
                recommendation="Add Exception stages to handle errors and recover application state.",
                platform="blue_prism",
            ))
        else:
            result.passed_rules.append("BP001")

        # BP002 — no recovery stage
        if "recover" not in " ".join(stage_types):
            result.violations.append(StandardsViolation(
                rule_id="BP002", rule_name="No Recovery Stage",
                severity="high",
                description="No Recovery stage detected for post-exception recovery.",
                location="process", location_type="workflow",
                recommendation="Add a Recovery stage to bring the application to a known state.",
                platform="blue_prism",
            ))

        # BP003 — missing start/end
        if "start" not in " ".join(stage_types) or "end" not in " ".join(stage_types):
            result.violations.append(StandardsViolation(
                rule_id="BP003", rule_name="Missing Start/End Stages",
                severity="critical",
                description="Process appears to be missing Start or End stages.",
                location="process", location_type="workflow",
                recommendation="Every process page must have exactly one Start and one End stage.",
                platform="blue_prism",
            ))

        # BP004 — unnamed stages
        unnamed = [s for s in stages if not s.get("name") or s.get("name", "").strip() == ""]
        if unnamed:
            result.violations.append(StandardsViolation(
                rule_id="BP004", rule_name="Unnamed Stages",
                severity="low",
                description=f"{len(unnamed)} stage(s) have empty or missing names.",
                location="process", location_type="activity",
                recommendation="Give all stages meaningful names for readability.",
                platform="blue_prism",
            ))

    # ───────────────────────── Automation Anywhere ────────────────────────────

    def _check_aa(self, project: Any, result: StandardsResult) -> None:
        wf_struct: dict = project.workflow_structure or {}
        commands: list[dict] = wf_struct.get("commands", [])
        cmd_types = [c.get("type", "").lower() for c in commands]

        # AA001 — no error handling
        if not any("error" in t or "try" in t or "catch" in t for t in cmd_types):
            result.violations.append(StandardsViolation(
                rule_id="AA001", rule_name="No Error Handling Commands",
                severity="high",
                description="Bot does not contain Try/Catch error-handling commands.",
                location="bot", location_type="workflow",
                recommendation="Wrap risky operations in Try/Catch error-handling blocks.",
                platform="automation_anywhere",
            ))
        else:
            result.passed_rules.append("AA001")

        # AA003 — no logging
        if not any("log" in t or "message" in t for t in cmd_types):
            result.violations.append(StandardsViolation(
                rule_id="AA003", rule_name="No Logging Commands",
                severity="medium",
                description="No log or message commands found in the bot.",
                location="bot", location_type="activity",
                recommendation="Add Log to File commands at key process milestones.",
                platform="automation_anywhere",
            ))

    # ───────────────────────── Code error detection ──────────────────────────

    def _detect_code_errors(self, project: Any, platform: str, result: StandardsResult) -> None:
        """Detect potential code-level errors in the parsed project structure."""
        wf_struct: dict = project.workflow_structure or {}
        deps: dict = project.dependencies or {}

        if platform == "uipath":
            workflows: list[dict] = wf_struct.get("workflows", [])
            packages = [p.get("name", "") for p in deps.get("packages", [])]

            for wf in workflows:
                filename = wf.get("filename", "unknown.xaml")
                activities = wf.get("activities", [])
                flat = self._flatten_activities(activities)

                # Detect hardcoded credential-like values in activity arguments
                for act in flat:
                    for attr in ["text", "url", "filepath"]:
                        val = str(act.get(attr, ""))
                        if any(kw in val.lower() for kw in ["password", "secret", "token", "apikey", "api_key"]):
                            result.code_errors.append(CodeError(
                                error_type="HardcodedCredential",
                                title="Possible Hardcoded Credential",
                                description=f"Activity '{act.get('display_name', act.get('name'))}' contains a value that looks like a credential.",
                                severity="critical",
                                location=filename,
                                line_hint=f"Activity: {act.get('display_name', act.get('name', ''))}",
                                fix="Move credential values to Orchestrator Assets or Windows Credential Manager.",
                            ))

                # Detect invoke workflow without arguments
                for act in flat:
                    name_lower = act.get("name", "").lower()
                    if "invokeWorkflow" in act.get("name", "") or "invoke" in name_lower:
                        if not act.get("arguments") and not act.get("children"):
                            result.code_errors.append(CodeError(
                                error_type="EmptyInvokeWorkflow",
                                title="Invoke Workflow With No Arguments",
                                description=f"Workflow '{filename}' invokes a sub-workflow without passing any arguments, which may cause null reference errors.",
                                severity="medium",
                                location=filename,
                                line_hint=f"Activity: {act.get('display_name', act.get('name', ''))}",
                                fix="Verify all required In/InOut arguments are passed to the invoked workflow.",
                            ))

            # Missing main workflow entirely
            if workflows and not any("main" in w.get("filename", "").lower() for w in workflows):
                result.code_errors.append(CodeError(
                    error_type="MissingMainWorkflow",
                    title="Main.xaml Not Found",
                    description="No workflow named 'Main.xaml' was detected. The robot entry point is undefined.",
                    severity="critical",
                    location="project",
                    line_hint="project.json → main",
                    fix="Ensure a Main.xaml exists and is set as the entry point in project.json.",
                ))

        elif platform == "blue_prism":
            stages: list[dict] = wf_struct.get("stages", [])
            # Detect stages connected to nothing (orphaned)
            stage_names = {s.get("name") for s in stages}
            for stage in stages:
                st = stage.get("type", "").lower()
                if st not in ("start", "end", "exception") and not stage.get("name"):
                    result.code_errors.append(CodeError(
                        error_type="UnnamedStage",
                        title="Unnamed Stage Detected",
                        description=f"A {stage.get('type','unknown')} stage has no name, which will cause identification issues.",
                        severity="medium",
                        location="process",
                        line_hint=f"Stage type: {stage.get('type', 'unknown')}",
                        fix="Assign a descriptive name to all stages.",
                    ))

    # ───────────────────────── Helpers ────────────────────────────────────────

    def _flatten_activities(self, activities: list[dict], depth: int = 0) -> list[dict]:
        result = []
        for act in activities:
            result.append(act)
            children = act.get("children")
            if children and depth < 10:
                result.extend(self._flatten_activities(children, depth + 1))
        return result

    def _max_nesting_depth(self, activities: list[dict], current: int) -> int:
        if not activities:
            return current
        max_d = current
        for act in activities:
            children = act.get("children")
            if children:
                d = self._max_nesting_depth(children, current + 1)
                if d > max_d:
                    max_d = d
        return max_d
