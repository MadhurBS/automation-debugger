import apiClient from './client'

export interface RootCause {
  category: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  confidence: number
  evidence: string[]
  affected_workflow?: string
  affected_activity?: string
  suggested_fix: string
  preventive_recommendations: string[]
}

export interface StandardsViolation {
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  description: string
  location: string
  location_type: string
  recommendation: string
  platform: string
}

export interface CodeError {
  error_type: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  location: string
  line_hint: string
  fix: string
}

export interface AnalysisStatus {
  id: string
  status: 'pending' | 'parsing' | 'analyzing' | 'completed' | 'failed'
  project_id: string
  created_at: string
  updated_at: string
  error_message?: string
}

export interface LogCorrelation {
  exception_type: string
  message: string
  timestamp: string
  matched_workflow: string
  matched_activity: string
  stack_trace_snippet: string
}

export interface ProjectSummary {
  name?: string
  workflow_count?: number
  workflow_names?: string[]
  package_names?: string[]
  metadata?: Record<string, string>
}

export interface AnalysisReport extends AnalysisStatus {
  platform: string
  overall_confidence?: number
  ai_used: boolean
  root_causes?: { causes: RootCause[] }
  recommendations?: { items: string[] }
  standards_violations?: { violations: StandardsViolation[]; summary: string; passed_rules: string[] }
  code_errors?: { errors: CodeError[]; total: number }
  standards_score?: number
  log_correlation?: { correlations: LogCorrelation[] }
  project_summary?: ProjectSummary
  pdf_path?: string
  excel_path?: string
}

export interface AnalysisListResponse {
  items: AnalysisReport[]
  total: number
  page: number
  size: number
  pages: number
}

export const triggerAnalysis = async (projectId: string): Promise<AnalysisStatus> => {
  const res = await apiClient.post<AnalysisStatus>('/analysis/trigger', {
    project_id: projectId,
    use_ai: true,
    check_standards: true,
  })
  return res.data
}

export const getAnalysisStatus = async (id: string): Promise<AnalysisStatus> => {
  const res = await apiClient.get<AnalysisStatus>(`/analysis/${id}/status`)
  return res.data
}

export const getAnalysisResult = async (id: string): Promise<AnalysisReport> => {
  const res = await apiClient.get<AnalysisReport>(`/analysis/${id}`)
  return res.data
}

export const listAnalyses = async (page = 1, size = 20, projectId?: string): Promise<AnalysisListResponse> => {
  const params: Record<string, unknown> = { page, size }
  if (projectId) params.project_id = projectId
  const res = await apiClient.get<AnalysisListResponse>('/analysis', { params })
  return res.data
}

export const deleteAnalysis = async (id: string): Promise<void> => {
  await apiClient.delete(`/analysis/${id}`)
}
