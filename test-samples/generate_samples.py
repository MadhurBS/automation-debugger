"""
Generate all test sample ZIP files and execution logs for the Automation Debugger.

Produces 8 project ZIPs + 8 execution logs:
  UiPath             - success / error (NullReferenceException in Process.xaml)
  Blue Prism         - success / error (RPCServerUnavailable on Navigate stage)
  Automation Anywhere- success / error (ObjectNotFoundException - stale selector)
  Power Automate     - success / error (HTTP 401 expired token)
"""

import io
import json
import zipfile
from pathlib import Path
from datetime import datetime, timedelta

BASE = Path(__file__).parent


def write_zip(dest: Path, files: dict) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            if isinstance(content, bytes):
                zf.writestr(name, content)
            else:
                zf.writestr(name, content.encode("utf-8"))
    dest.write_bytes(buf.getvalue())
    print(f"  + {dest.relative_to(BASE)}")


def write_log(dest: Path, content: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"  + {dest.relative_to(BASE)}")


def ts(base: datetime, offset_s: int) -> str:
    return (base + timedelta(seconds=offset_s)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ===========================================================================
# UIPATH SUCCESS
# ===========================================================================

UIPATH_SUCCESS_PROJECT = json.dumps({
    "name": "InvoiceProcessing_Success",
    "description": "REFramework invoice processing automation - fully working",
    "main": "Main.xaml",
    "projectVersion": "1.0.6",
    "runtimeOptions": {"requiresUserInteraction": False},
    "dependencies": {
        "UiPath.System.Activities": "[22.10.4]",
        "UiPath.UIAutomation.Activities": "[22.10.5]",
        "UiPath.Excel.Activities": "[2.16.1]",
        "UiPath.Orchestrator.Activities": "[2.0.3]",
        "UiPath.Mail.Activities": "[1.16.0]"
    },
    "studioVersion": "22.10.4",
    "targetFramework": "Windows",
    "author": "RPA Developer",
    "outputType": "Process"
}, indent=2)

UIPATH_SUCCESS_MAIN = '''<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap" x:Class="UiPath.REFramework.Main"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
          xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <StateMachine DisplayName="Main">
    <State DisplayName="Init">
      <State.Entry>
        <Sequence DisplayName="InitAllApplications">
          <InvokeWorkflowFile DisplayName="Invoke InitAllSettings" WorkflowFileName="Framework\\InitAllSettings.xaml"/>
          <InvokeWorkflowFile DisplayName="Invoke GetAppCredential" WorkflowFileName="Framework\\GetAppCredential.xaml"/>
          <Log DisplayName="Log Init Complete" Level="Information" Message="Init state completed"/>
        </Sequence>
      </State.Entry>
    </State>
    <State DisplayName="Get Transaction Data">
      <State.Entry>
        <Sequence DisplayName="GetTransactionData">
          <InvokeWorkflowFile DisplayName="Invoke GetTransactionData" WorkflowFileName="Framework\\GetTransactionData.xaml"/>
          <Log DisplayName="Log Transaction Fetched" Level="Information" Message="Transaction retrieved from queue"/>
        </Sequence>
      </State.Entry>
    </State>
    <State DisplayName="Process Transaction">
      <State.Entry>
        <Sequence DisplayName="ProcessTransaction">
          <TryCatch DisplayName="TryCatch - Process Invoice">
            <Try>
              <Sequence DisplayName="Invoice Processing Sequence">
                <InvokeWorkflowFile DisplayName="Invoke OpenApplication" WorkflowFileName="Framework\\OpenApplication.xaml"/>
                <InvokeWorkflowFile DisplayName="Invoke Process" WorkflowFileName="Process.xaml"/>
                <Log DisplayName="Log Success" Level="Information" Message="Invoice processed successfully"/>
              </Sequence>
            </Try>
            <Catches>
              <Catch x:TypeArguments="s:Exception">
                <Sequence DisplayName="Exception Handler">
                  <Log DisplayName="Log Exception" Level="Error" Message="Exception in Process Transaction"/>
                  <InvokeWorkflowFile DisplayName="Invoke SetTransactionStatus" WorkflowFileName="Framework\\SetTransactionStatus.xaml"/>
                </Sequence>
              </Catch>
            </Catches>
          </TryCatch>
        </Sequence>
      </State.Entry>
    </State>
    <State DisplayName="End Process">
      <State.Entry>
        <Sequence DisplayName="CloseApplication">
          <InvokeWorkflowFile DisplayName="Invoke CloseApplication" WorkflowFileName="Framework\\CloseApplication.xaml"/>
          <Log DisplayName="Log End" Level="Information" Message="Process completed"/>
        </Sequence>
      </State.Entry>
    </State>
  </StateMachine>
</Activity>'''

UIPATH_SUCCESS_PROCESS = '''<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="InvoiceProcessing.Process"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Process">
    <Log DisplayName="Log Start" Level="Information" Message="Processing invoice transaction"/>
    <UseApplicationBrowser DisplayName="Open SAP" BrowserType="IE" Url="http://sap.company.com/invoice">
      <TypeInto DisplayName="Enter Invoice Number" Selector="&lt;html /&gt;&lt;webctrl id='invoiceNum'/&gt;"/>
      <Click DisplayName="Click Submit" Selector="&lt;html /&gt;&lt;webctrl id='btnSubmit'/&gt;"/>
      <GetText DisplayName="Get Confirmation" Selector="&lt;html /&gt;&lt;webctrl id='confirmMsg'/&gt;"/>
    </UseApplicationBrowser>
    <ReadRange DisplayName="Read Invoice Data" SheetName="Invoices" WorkbookPath="Data\\Invoices.xlsx"/>
    <ForEach DisplayName="For Each Invoice Row">
      <Assign DisplayName="Set Invoice Amount" To="invoiceAmount" Value="currentRow(&quot;Amount&quot;).ToString()"/>
      <Log DisplayName="Log Row" Level="Information" Message="Row processed"/>
    </ForEach>
    <Log DisplayName="Log Complete" Level="Information" Message="Process workflow completed"/>
  </Sequence>
</Activity>'''


def build_uipath_success_log():
    t = datetime(2024, 6, 15, 9, 0, 0)
    entries = [
        (0,  "INFO",  "Main",    None,                "Process started"),
        (2,  "INFO",  "Main",    "InitAllSettings",   "Init state started"),
        (4,  "INFO",  "Main",    "GetAppCredential",  "Credentials loaded: SAPCredential"),
        (7,  "INFO",  "Main",    "InitAllSettings",   "Config loaded: MaxRetries=3, Timeout=30000ms"),
        (9,  "INFO",  "Main",    "GetTransactionData","Transaction data state started"),
        (11, "INFO",  "Main",    "GetTransactionData","Queue item retrieved: InvoiceQueue - TXN-20240615-001"),
        (13, "INFO",  "Process", "Open SAP",          "SAP browser launched"),
        (16, "INFO",  "Process", "Enter Invoice Number","Typed invoice number: INV-2024-0087"),
        (18, "INFO",  "Process", "Click Submit",       "Submit button clicked"),
        (20, "INFO",  "Process", "Get Confirmation",   "Confirmation: Invoice INV-2024-0087 posted"),
        (22, "INFO",  "Process", "Read Invoice Data",  "15 rows read from Invoices sheet"),
        (25, "INFO",  "Process", "For Each Invoice Row","Row: INV-2024-0088, Amount: 1250.00"),
        (27, "INFO",  "Process", "For Each Invoice Row","Row: INV-2024-0089, Amount: 3400.75"),
        (29, "INFO",  "Process", "Log Complete",       "Process workflow completed"),
        (31, "INFO",  "Main",    "SetTransactionStatus","TXN-20240615-001 set to Success"),
        (33, "INFO",  "Main",    "GetTransactionData", "No more queue items - transitioning to End Process"),
        (35, "INFO",  "Main",    "CloseApplication",   "SAP browser closed"),
        (37, "INFO",  "Main",    None,                 "Process completed. Total: 1 transactions processed"),
    ]
    lines = []
    for offset, level, wf, act, msg in entries:
        stamp = (t + timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        entry = {"timeStamp": stamp, "level": level, "message": msg,
                 "workflowFilePath": wf + ".xaml"}
        if act:
            entry["activityInfo"] = {"Name": act}
        lines.append(entry)
    return json.dumps(lines, indent=2)


# ===========================================================================
# UIPATH ERROR — NullReferenceException: in_TransactionItem is Nothing
# ===========================================================================

UIPATH_ERROR_PROJECT = json.dumps({
    "name": "InvoiceProcessing_Error",
    "description": "REFramework invoice processing - NullReference bug in Process.xaml",
    "main": "Main.xaml",
    "projectVersion": "1.0.5",
    "dependencies": {
        "UiPath.System.Activities": "[22.10.4]",
        "UiPath.UIAutomation.Activities": "[22.10.5]",
        "UiPath.Excel.Activities": "[2.16.1]",
        "UiPath.Orchestrator.Activities": "[2.0.3]"
    },
    "studioVersion": "22.10.4",
    "targetFramework": "Windows",
    "author": "RPA Developer",
    "outputType": "Process"
}, indent=2)

UIPATH_ERROR_PROCESS = '''<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="InvoiceProcessing.Process"
          xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Process">
    <Log DisplayName="Log Start" Level="Information" Message="Processing invoice transaction"/>
    <UseApplicationBrowser DisplayName="Open SAP" BrowserType="IE" Url="http://sap.company.com/invoice">
      <TypeInto DisplayName="Enter Invoice Number" Selector="&lt;html /&gt;&lt;webctrl id='invoiceNum'/&gt;"/>
      <Click DisplayName="Click Submit" Selector="&lt;html /&gt;&lt;webctrl id='btnSubmit'/&gt;"/>
    </UseApplicationBrowser>
    <ReadRange DisplayName="Read Invoice Data" SheetName="Invoices" WorkbookPath="Data\\Invoices.xlsx"/>
    <!-- BUG: in_TransactionItem is null — not passed when invoked from Main.xaml -->
    <Assign DisplayName="Extract Invoice Amount"
            To="invoiceAmount"
            Value="in_TransactionItem.SpecificContent(&quot;Amount&quot;).ToString()"/>
    <Log DisplayName="Log Amount" Level="Information" Message="Invoice amount extracted"/>
  </Sequence>
</Activity>'''


def build_uipath_error_log():
    t = datetime(2024, 6, 15, 14, 30, 0)
    entries = [
        {"timeStamp": (t).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "INFO", "message": "Process started",
         "workflowFilePath": "Main.xaml"},
        {"timeStamp": (t + timedelta(seconds=3)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "INFO", "message": "Init state started",
         "workflowFilePath": "Main.xaml", "activityInfo": {"Name": "InitAllSettings"}},
        {"timeStamp": (t + timedelta(seconds=6)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "INFO", "message": "Credentials loaded from Orchestrator Asset: SAPCredential",
         "workflowFilePath": "Main.xaml", "activityInfo": {"Name": "GetAppCredential"}},
        {"timeStamp": (t + timedelta(seconds=9)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "INFO", "message": "Transaction data state started",
         "workflowFilePath": "Main.xaml", "activityInfo": {"Name": "GetTransactionData"}},
        {"timeStamp": (t + timedelta(seconds=11)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "WARN", "message": "Queue InvoiceQueue returned no items. in_TransactionItem will be Nothing.",
         "workflowFilePath": "Main.xaml", "activityInfo": {"Name": "GetTransactionData"}},
        {"timeStamp": (t + timedelta(seconds=13)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "INFO", "message": "Process Transaction state started",
         "workflowFilePath": "Main.xaml"},
        {"timeStamp": (t + timedelta(seconds=15)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "INFO", "message": "SAP browser launched",
         "workflowFilePath": "Process.xaml", "activityInfo": {"Name": "Open SAP"}},
        {"timeStamp": (t + timedelta(seconds=18)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "INFO", "message": "Invoice number field typed",
         "workflowFilePath": "Process.xaml", "activityInfo": {"Name": "Enter Invoice Number"}},
        {"timeStamp": (t + timedelta(seconds=20)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "INFO", "message": "Reading invoice data from Excel workbook",
         "workflowFilePath": "Process.xaml", "activityInfo": {"Name": "Read Invoice Data"}},
        {"timeStamp": (t + timedelta(seconds=22)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "ERROR",
         "message": "Invoke Process.xaml: NullReferenceException - Object reference not set to an instance of an object.",
         "workflowFilePath": "Process.xaml",
         "activityInfo": {"Name": "Extract Invoice Amount"},
         "Exception": {
             "ExceptionType": "System.NullReferenceException",
             "Message": "Object reference not set to an instance of an object. Variable 'in_TransactionItem' is Nothing. Cannot call SpecificContent(\"Amount\") on a null QueueItem.",
             "Source": "Process.xaml",
             "StackTrace": (
                 "   at UiPath.Activities.Assign.Execute() in Process.xaml line 12\n"
                 "   at UiPath.Activities.Sequence.Execute() in Process.xaml\n"
                 "   at UiPath.Core.Activities.InvokeWorkflowFile.Execute() in Main.xaml line 34"
             )
         }},
        {"timeStamp": (t + timedelta(seconds=23)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "ERROR", "message": "Transaction TXN-20240615-002 set to Application Exception",
         "workflowFilePath": "Main.xaml", "activityInfo": {"Name": "SetTransactionStatus"}},
        {"timeStamp": (t + timedelta(seconds=25)).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
         "level": "INFO", "message": "Process ended with errors. Failed: 1",
         "workflowFilePath": "Main.xaml"},
    ]
    return json.dumps(entries, indent=2)


# ===========================================================================
# BLUE PRISM SUCCESS
# ===========================================================================

BP_SUCCESS_BPRELEASE = '''<?xml version="1.0" encoding="utf-8"?>
<bpr:release xmlns:bpr="http://www.blueprism.co.uk/product/release">
  <bpr:name>EmployeeOnboarding_Success</bpr:name>
  <bpr:release-notes>Employee onboarding automation - HR portal integration</bpr:release-notes>
  <bpr:created>2024-05-10T09:00:00Z</bpr:created>
  <bpr:package-id>PK-EMP-001</bpr:package-id>
  <bpr:contents>
    <bpr:process id="PROC-001" name="Employee_Onboarding" type="process">
      <bpr:subsheet name="Main Page" type="mainpage">
        <bpr:stage type="Start" name="Start"/>
        <bpr:stage type="Action" name="Initialise" object="Utilities - General" action="Write Log Message">
          <bpr:inputs>
            <bpr:input name="Message" value="Employee Onboarding Process Started"/>
          </bpr:inputs>
        </bpr:stage>
        <bpr:stage type="Navigate" name="Open HR Portal" url="https://hr.company.com/portal"/>
        <bpr:stage type="Action" name="Read Employee Data" object="MS Excel VBO" action="Read Range">
          <bpr:inputs>
            <bpr:input name="Workbook Path" value="C:\\RPA\\Data\\EmployeeList.xlsx"/>
            <bpr:input name="Worksheet Name" value="New Hires"/>
          </bpr:inputs>
        </bpr:stage>
        <bpr:stage type="Loop" name="For Each Employee" loopstart="true"/>
        <bpr:stage type="Action" name="Enter Employee Details" object="HR_Portal_BO" action="Create Employee"/>
        <bpr:stage type="Action" name="Send Welcome Email" object="Utilities - Email" action="Send Message"/>
        <bpr:stage type="Action" name="Log Success" object="Utilities - General" action="Write Log Message">
          <bpr:inputs>
            <bpr:input name="Message" value="Employee onboarded successfully"/>
          </bpr:inputs>
        </bpr:stage>
        <bpr:stage type="Loop" name="End For Each Employee" loopstart="false"/>
        <bpr:stage type="End" name="End"/>
      </bpr:subsheet>
      <bpr:subsheet name="Exception Handler" type="normal">
        <bpr:stage type="Exception" name="Throw Exception"/>
        <bpr:stage type="Recover" name="Recover"/>
        <bpr:stage type="Action" name="Log Error" object="Utilities - General" action="Write Log Message"/>
        <bpr:stage type="End" name="End"/>
      </bpr:subsheet>
    </bpr:process>
    <bpr:object id="OBJ-001" name="HR_Portal_BO" type="object">
      <bpr:action name="Create Employee">
        <bpr:stage type="Navigate" name="Navigate to Employee Form" url="/employees/new"/>
        <bpr:stage type="Write" name="Enter First Name" field="firstName"/>
        <bpr:stage type="Write" name="Enter Last Name" field="lastName"/>
        <bpr:stage type="Write" name="Enter Email" field="email"/>
        <bpr:stage type="Navigate" name="Click Save" element="btnSave"/>
        <bpr:stage type="Read" name="Get Employee ID" field="empId"/>
      </bpr:action>
    </bpr:object>
  </bpr:contents>
</bpr:release>'''


def build_bp_success_log():
    t = datetime(2024, 5, 20, 8, 0, 0)
    lines = [
        f"{ts(t,  0)} | INFO  | Session started | Resource: BP-ROBOT-01 | Process: Employee_Onboarding",
        f"{ts(t,  2)} | INFO  | [Main Page] Stage: Initialise | Employee Onboarding Process Started",
        f"{ts(t,  4)} | INFO  | [Main Page] Stage: Open HR Portal | Navigating to https://hr.company.com/portal",
        f"{ts(t,  7)} | INFO  | [Main Page] Stage: Read Employee Data | Reading EmployeeList.xlsx Sheet: New Hires",
        f"{ts(t,  9)} | INFO  | [Main Page] Stage: Read Employee Data | 12 rows read successfully",
        f"{ts(t, 11)} | INFO  | [Main Page] Stage: For Each Employee | Processing employee 1/12: John Smith",
        f"{ts(t, 14)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Navigate to Employee Form | /employees/new",
        f"{ts(t, 16)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Enter First Name | John",
        f"{ts(t, 17)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Enter Last Name | Smith",
        f"{ts(t, 18)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Enter Email | j.smith@company.com",
        f"{ts(t, 19)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Click Save | Record saved",
        f"{ts(t, 20)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Get Employee ID | EMP-20240520-001",
        f"{ts(t, 22)} | INFO  | [Main Page] Stage: Send Welcome Email | Email sent to j.smith@company.com",
        f"{ts(t, 24)} | INFO  | [Main Page] Stage: Log Success | Employee onboarded: John Smith (EMP-20240520-001)",
        f"{ts(t, 50)} | INFO  | [Main Page] Stage: For Each Employee | All 12 employees processed",
        f"{ts(t, 52)} | INFO  | Session completed | Duration: 52s | Status: Success | Items: 12",
    ]
    return "\n".join(lines)


# ===========================================================================
# BLUE PRISM ERROR — RPC Server Unavailable (IE not available on robot)
# ===========================================================================

BP_ERROR_BPRELEASE = '''<?xml version="1.0" encoding="utf-8"?>
<bpr:release xmlns:bpr="http://www.blueprism.co.uk/product/release">
  <bpr:name>EmployeeOnboarding_Error</bpr:name>
  <bpr:release-notes>Employee onboarding - RPC Server Unavailable error on Navigate stage</bpr:release-notes>
  <bpr:created>2024-05-10T09:00:00Z</bpr:created>
  <bpr:package-id>PK-EMP-002</bpr:package-id>
  <bpr:contents>
    <bpr:process id="PROC-002" name="Employee_Onboarding_v2" type="process">
      <bpr:subsheet name="Main Page" type="mainpage">
        <bpr:stage type="Start" name="Start"/>
        <bpr:stage type="Action" name="Initialise" object="Utilities - General" action="Write Log Message"/>
        <bpr:stage type="Navigate" name="Open HR Portal" url="https://hr.company.com/portal"/>
        <bpr:stage type="Action" name="Read Employee Data" object="MS Excel VBO" action="Read Range"/>
        <bpr:stage type="Loop" name="For Each Employee" loopstart="true"/>
        <bpr:stage type="Action" name="Enter Employee Details" object="HR_Portal_BO" action="Create Employee"/>
        <!-- BUG: IE11 not available on robot machine; causes RPC Server Unavailable -->
        <bpr:stage type="Navigate" name="Navigate to Benefits Page" browser="InternetExplorer"
                   url="https://hr.company.com/benefits"/>
        <bpr:stage type="Action" name="Assign Benefits Package" object="HR_Portal_BO" action="Set Benefits"/>
        <bpr:stage type="Loop" name="End For Each Employee" loopstart="false"/>
        <bpr:stage type="End" name="End"/>
      </bpr:subsheet>
      <bpr:subsheet name="Exception Handler" type="normal">
        <bpr:stage type="Exception" name="Throw Exception"/>
        <bpr:stage type="Recover" name="Recover"/>
        <bpr:stage type="End" name="End"/>
      </bpr:subsheet>
    </bpr:process>
  </bpr:contents>
</bpr:release>'''


def build_bp_error_log():
    t = datetime(2024, 5, 21, 10, 15, 0)
    lines = [
        f"{ts(t,  0)} | INFO  | Session started | Resource: BP-ROBOT-02 | Process: Employee_Onboarding_v2",
        f"{ts(t,  2)} | INFO  | [Main Page] Stage: Initialise | Employee Onboarding Process Started",
        f"{ts(t,  5)} | INFO  | [Main Page] Stage: Open HR Portal | Navigating to https://hr.company.com/portal",
        f"{ts(t,  8)} | INFO  | [Main Page] Stage: Read Employee Data | Reading EmployeeList.xlsx",
        f"{ts(t, 10)} | INFO  | [Main Page] Stage: Read Employee Data | 8 rows read",
        f"{ts(t, 12)} | INFO  | [Main Page] Stage: For Each Employee | Processing employee 1/8: Jane Doe",
        f"{ts(t, 14)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Navigate to Employee Form | OK",
        f"{ts(t, 16)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Enter First Name | Jane",
        f"{ts(t, 17)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Enter Last Name | Doe",
        f"{ts(t, 19)} | INFO  | [HR_Portal_BO - Create Employee] Stage: Click Save | EMP-20240521-001",
        f"{ts(t, 21)} | INFO  | [Main Page] Stage: Navigate to Benefits Page | Attempting Internet Explorer launch",
        f"{ts(t, 23)} | ERROR | [Main Page] Stage: Navigate to Benefits Page | EXCEPTION: Internal : The RPC server is unavailable. (Exception from HRESULT: 0x800706BA)",
        f"{ts(t, 23)} | ERROR | Detail: System.Runtime.InteropServices.COMException (0x800706BA): The RPC server is unavailable.",
        f"{ts(t, 23)} | ERROR |    at BluePrism.BrowserAutomation.InternetExplorer.Launch(String url)",
        f"{ts(t, 23)} | ERROR |    at BluePrism.AutomateC.Application.Navigate(String action, String url)",
        f"{ts(t, 23)} | ERROR |    at BluePrism.Core.StageNavigation.Execute(Process process, CalcEngine calc)",
        f"{ts(t, 24)} | WARN  | [Exception Handler] Stage: Recover | Attempting recovery from RPC error",
        f"{ts(t, 25)} | ERROR | Session terminated | Status: Failed | Reason: RPC server unavailable | Duration: 25s",
    ]
    return "\n".join(lines)


# ===========================================================================
# AUTOMATION ANYWHERE SUCCESS
# ===========================================================================

AA_SUCCESS_BOT = json.dumps({
    "botName": "PurchaseOrder_Processing",
    "botVersion": "2.1.0",
    "platform": "Automation Anywhere A360",
    "description": "Process purchase orders from Excel and submit to SAP portal",
    "variables": [
        {"name": "sPONumber", "type": "String"},
        {"name": "nAmount", "type": "Number"},
        {"name": "bProcessed", "type": "Boolean", "defaultValue": False}
    ],
    "tasks": [
        {
            "id": "TASK-001",
            "name": "PO_Processing_Main",
            "type": "TaskBot",
            "steps": [
                {"package": "Excel Basic", "action": "Open Spreadsheet", "path": "C:\\RPA\\Data\\PurchaseOrders.xlsx"},
                {"package": "Excel Basic", "action": "Get Cell", "sheet": "Orders", "range": "A2:G50"},
                {"package": "Browser", "action": "Open Browser", "url": "http://sap.company.com"},
                {"package": "Object Cloning", "action": "Click", "object": "btnLogin"},
                {"package": "Object Cloning", "action": "Set Text", "object": "inputPONumber", "value": "sPONumber"},
                {"package": "Object Cloning", "action": "Click", "object": "btnSubmitPO"},
                {"package": "String", "action": "Trim", "source": "confirmationCode"},
                {"package": "Log to File", "action": "Log Message", "level": "INFO"},
                {"package": "Excel Basic", "action": "Close Spreadsheet"}
            ],
            "errorHandler": {
                "type": "Try/Catch",
                "onError": "Log Error and Continue"
            }
        }
    ]
}, indent=2)


def build_aa_success_log():
    t = datetime(2024, 7, 10, 9, 0, 0)
    lines = [
        f"{ts(t,  0)} | INFO  | Bot: PO_Processing_Main | Session: AA-SESSION-20240710-001 | Started",
        f"{ts(t,  2)} | INFO  | [Excel Basic - Open Spreadsheet] File: C:\\RPA\\Data\\PurchaseOrders.xlsx opened",
        f"{ts(t,  4)} | INFO  | [Excel Basic - Get Cell] Sheet: Orders, Range: A2:G50 - 48 rows loaded",
        f"{ts(t,  6)} | INFO  | Loop: Processing PO row 1 of 48 | PO Number: PO-2024-0550",
        f"{ts(t,  8)} | INFO  | [Browser - Open Browser] Navigating to http://sap.company.com - Page loaded",
        f"{ts(t, 10)} | INFO  | [Object Cloning - Click] Clicked: btnLogin | Login successful",
        f"{ts(t, 12)} | INFO  | [Object Cloning - Set Text] Set inputPONumber: PO-2024-0550",
        f"{ts(t, 14)} | INFO  | [Object Cloning - Click] Clicked: btnSubmitPO",
        f"{ts(t, 16)} | INFO  | [String - Trim] Confirmation code trimmed: CONF-7732",
        f"{ts(t, 18)} | INFO  | [Log to File] PO-2024-0550 submitted. Amount: $12500.00 - Status: Approved",
        f"{ts(t, 60)} | INFO  | Loop completed | 48 POs processed | 0 errors",
        f"{ts(t, 62)} | INFO  | Bot: PO_Processing_Main | Status: Completed | Duration: 62s | Items: 48",
    ]
    return "\n".join(lines)


# ===========================================================================
# AUTOMATION ANYWHERE ERROR — Object Cloning stale selector after UI update
# ===========================================================================

AA_ERROR_BOT = json.dumps({
    "botName": "PurchaseOrder_Processing_Error",
    "botVersion": "2.0.9",
    "platform": "Automation Anywhere A360",
    "description": "PO processing - legacy hardcoded object IDs that break after SAP UI update",
    "variables": [
        {"name": "sPONumber", "type": "String"},
        {"name": "nAmount", "type": "Number"}
    ],
    "tasks": [
        {
            "id": "TASK-002",
            "name": "PO_Processing_Main",
            "type": "TaskBot",
            "steps": [
                {"package": "Excel Basic", "action": "Open Spreadsheet", "path": "C:\\RPA\\Data\\PurchaseOrders.xlsx"},
                {"package": "Browser", "action": "Open Browser", "url": "http://sap.company.com"},
                {"package": "Object Cloning", "action": "Click", "object": "btnLogin_v1"},
                {"package": "Object Cloning", "action": "Set Text",
                 "object": "inputPO_old_id_9F2A",
                 "note": "BUG: hardcoded legacy HTML ID - changed to input_PONumber_v2 after SAP upgrade"},
                {"package": "Object Cloning", "action": "Click", "object": "btnSubmit_legacy"}
            ],
            "errorHandler": None
        }
    ]
}, indent=2)


def build_aa_error_log():
    t = datetime(2024, 7, 11, 14, 45, 0)
    lines = [
        f"{ts(t,  0)} | INFO  | Bot: PO_Processing_Main | Session: AA-SESSION-20240711-003 | Started",
        f"{ts(t,  2)} | INFO  | [Excel Basic - Open Spreadsheet] File: C:\\RPA\\Data\\PurchaseOrders.xlsx opened",
        f"{ts(t,  4)} | INFO  | [Excel Basic - Get Cell] Sheet: Orders - 48 rows loaded",
        f"{ts(t,  6)} | INFO  | Loop: Processing PO row 1 | PO Number: PO-2024-0598",
        f"{ts(t,  8)} | INFO  | [Browser - Open Browser] http://sap.company.com - Page loaded",
        f"{ts(t, 10)} | INFO  | [Object Cloning - Click] Clicking btnLogin_v1 - Login OK",
        f"{ts(t, 11)} | INFO  | [Object Cloning - Set Text] Locating object: inputPO_old_id_9F2A",
        f"{ts(t, 13)} | ERROR | [Object Cloning - Set Text] ObjectNotFoundException: Unable to find object 'inputPO_old_id_9F2A' on screen.",
        f"{ts(t, 13)} | ERROR | Detail: HTML ID 'inputPO_old_id_9F2A' does not exist. SAP portal upgraded on 2024-07-11. New ID is 'input_PONumber_v2'.",
        f"{ts(t, 13)} | ERROR |    at AA.ObjectCloning.FindElement(ObjectProperties props)",
        f"{ts(t, 13)} | ERROR |    at AA.ObjectCloning.SetText(String value)",
        f"{ts(t, 13)} | ERROR |    at AA.TaskEngine.ExecuteAction(BotAction action) [step 4 of PO_Processing_Main]",
        f"{ts(t, 14)} | WARN  | No error handler configured for this task - bot will terminate",
        f"{ts(t, 15)} | ERROR | Bot: PO_Processing_Main | Status: Failed | Error: ObjectNotFoundException | Duration: 15s",
    ]
    return "\n".join(lines)


# ===========================================================================
# POWER AUTOMATE SUCCESS
# ===========================================================================

PA_SUCCESS_DEFINITION = json.dumps({
    "name": "LeaveApproval_AutoNotify",
    "description": "Automated leave approval - SharePoint trigger to Outlook notification",
    "version": "1.0.0",
    "triggers": {
        "When_an_item_is_created_or_modified": {
            "type": "ApiConnectionWebhook",
            "connection": "sharepoint",
            "site": "https://company.sharepoint.com/sites/HR",
            "list": "LeaveRequests"
        }
    },
    "actions": {
        "Scope_Process_Leave_Request": {
            "type": "Scope",
            "actions": {
                "Get_Manager_Details": {
                    "type": "ApiConnection",
                    "connection": "office365",
                    "operation": "GetUser"
                },
                "Condition_Check_Leave_Type": {
                    "type": "If",
                    "expression": "triggerBody.LeaveType eq Annual",
                    "true_actions": ["HTTP_Call_HR_System"],
                    "false_actions": ["Send_Info_Email"]
                },
                "HTTP_Call_HR_System": {
                    "type": "Http",
                    "method": "POST",
                    "uri": "https://hrsystem.company.com/api/leave/approve",
                    "headers": {"Content-Type": "application/json"},
                    "body": {"employeeId": "triggerBody.EmployeeID", "days": "triggerBody.Days"}
                },
                "Send_Approval_Email": {
                    "type": "ApiConnection",
                    "connection": "office365",
                    "operation": "SendEmail"
                },
                "Update_SharePoint_Status": {
                    "type": "ApiConnection",
                    "connection": "sharepoint",
                    "operation": "UpdateItem",
                    "list": "LeaveRequests",
                    "field": "Status"
                }
            }
        }
    }
}, indent=2)


def build_pa_success_log():
    t = datetime(2024, 8, 5, 10, 0, 0)
    lines = [
        f"{ts(t, 0)} | INFO  | Flow: LeaveApproval_AutoNotify | Run ID: 08585f3a-run-001 | Trigger fired",
        f"{ts(t, 1)} | INFO  | Trigger: When_an_item_is_created_or_modified | SharePoint item ID: 1042 | Employee: Emily Chen",
        f"{ts(t, 2)} | INFO  | Action: Scope_Process_Leave_Request | Scope started",
        f"{ts(t, 3)} | INFO  | Action: Get_Manager_Details | Manager retrieved: David Lee (d.lee@company.com)",
        f"{ts(t, 4)} | INFO  | Action: Condition_Check_Leave_Type | LeaveType: Annual | Condition: TRUE",
        f'{ts(t, 5)} | INFO  | Action: HTTP_Call_HR_System | POST https://hrsystem.company.com/api/leave/approve | Status: 200 OK',
        f'{ts(t, 6)} | INFO  | Action: HTTP_Call_HR_System | Response: approvalId=APR-2024-0812 status=Approved',
        f"{ts(t, 7)} | INFO  | Action: Send_Approval_Email | Email sent to emily.chen@company.com and d.lee@company.com",
        f"{ts(t, 8)} | INFO  | Action: Update_SharePoint_Status | Item 1042 updated - Status: Approved",
        f"{ts(t, 9)} | INFO  | Action: Scope_Process_Leave_Request | Scope completed successfully",
        f"{ts(t,10)} | INFO  | Flow: LeaveApproval_AutoNotify | Run ID: 08585f3a-run-001 | Status: Succeeded | Duration: 10s",
    ]
    return "\n".join(lines)


# ===========================================================================
# POWER AUTOMATE ERROR — HTTP 401 expired token on HR System API
# ===========================================================================

PA_ERROR_DEFINITION = json.dumps({
    "name": "LeaveApproval_AutoNotify_Error",
    "description": "Leave approval flow - expired Bearer token on HR System HTTP action",
    "version": "1.0.0",
    "triggers": {
        "When_an_item_is_created_or_modified": {
            "type": "ApiConnectionWebhook",
            "connection": "sharepoint",
            "list": "LeaveRequests"
        }
    },
    "actions": {
        "Scope_Process_Leave_Request": {
            "type": "Scope",
            "actions": {
                "Get_Manager_Details": {
                    "type": "ApiConnection",
                    "connection": "office365",
                    "operation": "GetUser"
                },
                "HTTP_Call_HR_System": {
                    "type": "Http",
                    "method": "POST",
                    "uri": "https://hrsystem.company.com/api/leave/approve",
                    "headers": {
                        "Authorization": "Bearer HR_API_Token_parameter",
                        "Content-Type": "application/json"
                    },
                    "body": {"employeeId": "triggerBody.EmployeeID"},
                    "note": "BUG: HR_API_Token parameter contains expired token (issued 2024-07-07, expired after 30 days)"
                },
                "Send_Approval_Email": {
                    "type": "ApiConnection",
                    "connection": "office365",
                    "operation": "SendEmail",
                    "runAfter": "HTTP_Call_HR_System"
                },
                "Update_SharePoint_Status": {
                    "type": "ApiConnection",
                    "connection": "sharepoint",
                    "operation": "UpdateItem",
                    "runAfter": "Send_Approval_Email"
                }
            }
        }
    },
    "parameters": {
        "HR_API_Token": {
            "type": "SecureString",
            "description": "Bearer token for HR System API - MUST BE ROTATED EVERY 30 DAYS"
        }
    }
}, indent=2)


def build_pa_error_log():
    t = datetime(2024, 8, 6, 11, 30, 0)
    lines = [
        f"{ts(t, 0)} | INFO  | Flow: LeaveApproval_AutoNotify_Error | Run ID: 08585f3a-run-047 | Trigger fired",
        f"{ts(t, 1)} | INFO  | Trigger: When_an_item_is_created_or_modified | SharePoint item ID: 1089 | Employee: Marcus Webb",
        f"{ts(t, 2)} | INFO  | Action: Scope_Process_Leave_Request | Scope started",
        f"{ts(t, 3)} | INFO  | Action: Get_Manager_Details | Manager: Sarah Park (s.park@company.com)",
        f"{ts(t, 4)} | INFO  | Action: HTTP_Call_HR_System | POST https://hrsystem.company.com/api/leave/approve",
        f"{ts(t, 5)} | ERROR | Action: HTTP_Call_HR_System | HTTP request failed",
        f"{ts(t, 5)} | ERROR | StatusCode: 401 Unauthorized",
        f'{ts(t, 5)} | ERROR | Response: error=invalid_token error_description=The access token has expired. Issued: 2024-07-07T00:00:00Z. Expired after 30 days.',
        f"{ts(t, 5)} | ERROR | Request headers: Authorization=Bearer [REDACTED] Content-Type=application/json",
        f"{ts(t, 6)} | ERROR | Action: Scope_Process_Leave_Request | Scope failed - dependent actions skipped",
        f"{ts(t, 6)} | WARN  | Action: Send_Approval_Email | Skipped - runAfter condition: HTTP_Call_HR_System=Failed",
        f"{ts(t, 6)} | WARN  | Action: Update_SharePoint_Status | Skipped - runAfter condition: Send_Approval_Email=Skipped",
        f"{ts(t, 7)} | ERROR | Flow: LeaveApproval_AutoNotify_Error | Run ID: 08585f3a-run-047 | Status: Failed | Duration: 7s",
        f"{ts(t, 7)} | ERROR | FailedAction: HTTP_Call_HR_System | Code: InvalidAuthenticationToken | Message: 401 Unauthorized - token expired",
    ]
    return "\n".join(lines)


# ===========================================================================
# BUILD ALL
# ===========================================================================

def build_all():
    print("\n=== UiPath ===")
    write_zip(BASE / "uipath/success/UiPath_InvoiceProcessing_Success.zip", {
        "project.json": UIPATH_SUCCESS_PROJECT,
        "Main.xaml": UIPATH_SUCCESS_MAIN,
        "Process.xaml": UIPATH_SUCCESS_PROCESS,
        "Framework/InitAllSettings.xaml": '<Activity DisplayName="InitAllSettings"><Sequence><Log Level="Information" Message="Settings loaded"/></Sequence></Activity>',
        "Framework/GetAppCredential.xaml": '<Activity DisplayName="GetAppCredential"><Sequence><GetCredential AssetName="SAPCredential"/></Sequence></Activity>',
        "Framework/GetTransactionData.xaml": '<Activity DisplayName="GetTransactionData"><Sequence><GetQueueItem QueueName="InvoiceQueue"/></Sequence></Activity>',
        "Framework/SetTransactionStatus.xaml": '<Activity DisplayName="SetTransactionStatus"><Sequence><SetTransactionStatus Status="Successful"/></Sequence></Activity>',
        "Framework/OpenApplication.xaml": '<Activity DisplayName="OpenApplication"><Sequence><UseApplicationBrowser DisplayName="Open SAP"/></Sequence></Activity>',
        "Framework/CloseApplication.xaml": '<Activity DisplayName="CloseApplication"><Sequence><CloseApplication/></Sequence></Activity>',
    })
    write_log(BASE / "uipath/success/ExecutionLog_Success.json", build_uipath_success_log())

    write_zip(BASE / "uipath/error/UiPath_InvoiceProcessing_NullRef_Error.zip", {
        "project.json": UIPATH_ERROR_PROJECT,
        "Main.xaml": UIPATH_SUCCESS_MAIN,
        "Process.xaml": UIPATH_ERROR_PROCESS,
        "Framework/InitAllSettings.xaml": '<Activity DisplayName="InitAllSettings"><Sequence><Log Level="Information" Message="Settings loaded"/></Sequence></Activity>',
        "Framework/GetAppCredential.xaml": '<Activity DisplayName="GetAppCredential"><Sequence><GetCredential AssetName="SAPCredential"/></Sequence></Activity>',
        "Framework/GetTransactionData.xaml": '<Activity DisplayName="GetTransactionData"><Sequence><GetQueueItem QueueName="InvoiceQueue"/></Sequence></Activity>',
        "Framework/SetTransactionStatus.xaml": '<Activity DisplayName="SetTransactionStatus"><Sequence><SetTransactionStatus Status="Failed"/></Sequence></Activity>',
        "Framework/OpenApplication.xaml": '<Activity DisplayName="OpenApplication"><Sequence><UseApplicationBrowser DisplayName="Open SAP"/></Sequence></Activity>',
        "Framework/CloseApplication.xaml": '<Activity DisplayName="CloseApplication"><Sequence><CloseApplication/></Sequence></Activity>',
    })
    write_log(BASE / "uipath/error/ExecutionLog_NullReferenceException.json", build_uipath_error_log())

    print("\n=== Blue Prism ===")
    write_zip(BASE / "blue_prism/success/BluePrism_EmployeeOnboarding_Success.zip", {
        "EmployeeOnboarding_Success.bprelease": BP_SUCCESS_BPRELEASE,
    })
    write_log(BASE / "blue_prism/success/SessionLog_Success.txt", build_bp_success_log())

    write_zip(BASE / "blue_prism/error/BluePrism_EmployeeOnboarding_RPCError.zip", {
        "EmployeeOnboarding_Error.bprelease": BP_ERROR_BPRELEASE,
    })
    write_log(BASE / "blue_prism/error/SessionLog_RPCServerUnavailable.txt", build_bp_error_log())

    print("\n=== Automation Anywhere ===")
    write_zip(BASE / "automation_anywhere/success/AA_PurchaseOrder_Success.zip", {
        "bot.json": AA_SUCCESS_BOT,
        "PO_Processing_Main.atmx": "<!-- Automation Anywhere A360 TaskBot: PO_Processing_Main -->",
    })
    write_log(BASE / "automation_anywhere/success/BotLog_Success.txt", build_aa_success_log())

    write_zip(BASE / "automation_anywhere/error/AA_PurchaseOrder_ObjectCloning_Error.zip", {
        "bot.json": AA_ERROR_BOT,
        "PO_Processing_Main.atmx": "<!-- Automation Anywhere A360 TaskBot: PO_Processing_Main (legacy selectors) -->",
    })
    write_log(BASE / "automation_anywhere/error/BotLog_ObjectNotFoundException.txt", build_aa_error_log())

    print("\n=== Power Automate ===")
    write_zip(BASE / "power_automate/success/PowerAutomate_LeaveApproval_Success.zip", {
        "definition.json": PA_SUCCESS_DEFINITION,
        "manifest.json": json.dumps({
            "name": "LeaveApproval_AutoNotify",
            "version": "1.0.0",
            "connections": ["sharepoint", "office365"]
        }, indent=2),
    })
    write_log(BASE / "power_automate/success/FlowRunLog_Success.txt", build_pa_success_log())

    write_zip(BASE / "power_automate/error/PowerAutomate_LeaveApproval_HTTP401_Error.zip", {
        "definition.json": PA_ERROR_DEFINITION,
        "manifest.json": json.dumps({
            "name": "LeaveApproval_AutoNotify_Error",
            "version": "1.0.0",
            "connections": ["sharepoint", "office365"]
        }, indent=2),
    })
    write_log(BASE / "power_automate/error/FlowRunLog_HTTP401_Error.txt", build_pa_error_log())

    print("\nAll 8 project ZIPs + 8 execution logs generated.")


if __name__ == "__main__":
    build_all()
