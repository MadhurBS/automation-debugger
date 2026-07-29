# Test Samples — RPA Automation Debugger

Ready-to-upload test files for the **AI-Powered RPA Automation Debugger**.  
Each tool has one **success** project + log and one **error** project + log.

---

## Directory Structure

```
test-samples/
├── uipath/
│   ├── success/
│   │   ├── UiPath_InvoiceProcessing_Success.zip        ← Upload as project
│   │   └── ExecutionLog_Success.json                   ← Upload as log
│   └── error/
│       ├── UiPath_InvoiceProcessing_NullRef_Error.zip  ← Upload as project
│       └── ExecutionLog_NullReferenceException.json    ← Upload as log
│
├── blue_prism/
│   ├── success/
│   │   ├── BluePrism_EmployeeOnboarding_Success.zip    ← Upload as project
│   │   └── SessionLog_Success.txt                      ← Upload as log
│   └── error/
│       ├── BluePrism_EmployeeOnboarding_RPCError.zip   ← Upload as project
│       └── SessionLog_RPCServerUnavailable.txt         ← Upload as log
│
├── automation_anywhere/
│   ├── success/
│   │   ├── AA_PurchaseOrder_Success.zip                ← Upload as project
│   │   └── BotLog_Success.txt                          ← Upload as log
│   └── error/
│       ├── AA_PurchaseOrder_ObjectCloning_Error.zip    ← Upload as project
│       └── BotLog_ObjectNotFoundException.txt          ← Upload as log
│
└── power_automate/
    ├── success/
    │   ├── PowerAutomate_LeaveApproval_Success.zip     ← Upload as project
    │   └── FlowRunLog_Success.txt                      ← Upload as log
    └── error/
        ├── PowerAutomate_LeaveApproval_HTTP401_Error.zip ← Upload as project
        └── FlowRunLog_HTTP401_Error.txt                  ← Upload as log
```

---

## What Each Test Contains

### UiPath

| | Success | Error |
|---|---|---|
| **Project** | REFramework invoice processing — 5 workflows (Main, Process, Init, GetTransaction, CloseApp), TryCatch, full packages | Same REFramework structure but `Process.xaml` calls `in_TransactionItem.SpecificContent()` on a null variable |
| **Error Type** | — | `System.NullReferenceException` |
| **Failed Activity** | — | `Extract Invoice Amount` (Assign activity in Process.xaml) |
| **Root Cause** | — | Queue returned no items → `in_TransactionItem` is `Nothing` → null dereference on line 12 |
| **Log Format** | UiPath JSON array (`timeStamp`, `level`, `activityInfo`, `Exception`) | Same |
| **REFramework State** | All 4 states complete successfully | Fails in **Process Transaction** state |

### Blue Prism

| | Success | Error |
|---|---|---|
| **Project** | `Employee_Onboarding` process — Main Page with Navigate/Read/Loop/Action stages, `HR_Portal_BO` Business Object | `Employee_Onboarding_v2` — same but adds Navigate stage that launches IE11 |
| **Error Type** | — | `COMException: The RPC server is unavailable (0x800706BA)` |
| **Failed Stage** | — | **Navigate to Benefits Page** (Navigate stage, IE11 not installed on robot) |
| **Root Cause** | — | Internet Explorer 11 not available on robot machine. COM automation fails with RPC error. |
| **Log Format** | NLog-style: `YYYY-MM-DD HH:MM:SS | LEVEL | [Page] Stage: name \| detail` | Same |

### Automation Anywhere

| | Success | Error |
|---|---|---|
| **Project** | `PO_Processing_Main` TaskBot — Excel Basic, Browser, Object Cloning, Log to File packages | Same bot but with hardcoded legacy HTML element IDs |
| **Error Type** | — | `ObjectNotFoundException` |
| **Failed Action** | — | **Object Cloning - Set Text** on `inputPO_old_id_9F2A` |
| **Root Cause** | — | SAP portal was upgraded on 2024-07-11; element ID changed from `inputPO_old_id_9F2A` to `input_PONumber_v2`. Hardcoded legacy selector no longer exists. |
| **Log Format** | NLog-style with `[Package - Action]` prefix | Same |

### Power Automate (Cloud)

| | Success | Error |
|---|---|---|
| **Project** | `LeaveApproval_AutoNotify` Cloud flow — SharePoint trigger → Scope → Get Manager → HTTP call → Send Email → Update SP | Same flow but `HR_API_Token` parameter contains an expired token |
| **Error Type** | — | HTTP `401 Unauthorized` — `invalid_token` |
| **Failed Action** | — | **HTTP_Call_HR_System** (POST to `https://hrsystem.company.com/api/leave/approve`) |
| **Root Cause** | — | Bearer token issued 2024-07-07, expired after 30 days. Downstream actions `Send_Approval_Email` and `Update_SharePoint_Status` are skipped due to `runAfter` dependency. |
| **Log Format** | NLog-style with `Action: name \| detail` | Same |

---

## How to Use

1. Open the app at **http://localhost:3000**
2. Go to **Upload Project**
3. Upload the `.zip` file (project)
4. Go to **Upload Log** for the same project
5. Upload the matching `.log` / `.json` / `.txt` log file
6. Click **Run Analysis**
7. View results in the **Runtime Analysis** tab

### Expected Debugger Output — Error Cases

| Tool | Expected Exception | Expected Workflow/Page | Expected Activity/Stage |
|---|---|---|---|
| UiPath | `System.NullReferenceException` | `Process.xaml` | `Extract Invoice Amount` (Assign) |
| Blue Prism | `COMException 0x800706BA` | `Main Page` | `Navigate to Benefits Page` |
| Automation Anywhere | `ObjectNotFoundException` | `PO_Processing_Main` | `Object Cloning - Set Text` |
| Power Automate | HTTP `401 Unauthorized` | `Scope_Process_Leave_Request` | `HTTP_Call_HR_System` |

---

## Regenerating

To regenerate all files (e.g. after modifying content):

```bash
cd test-samples
python generate_samples.py
```
