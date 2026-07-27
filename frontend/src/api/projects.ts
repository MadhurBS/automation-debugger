import apiClient from './client'

export interface Project {
  id: string
  name: string
  description?: string
  platform: string
  original_filename: string
  file_size_bytes: number
  project_metadata?: Record<string, unknown>
  workflow_structure?: Record<string, unknown>
  dependencies?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ProjectListResponse {
  items: Project[]
  total: number
  page: number
  size: number
  pages: number
}

export interface DetectPlatformResult {
  platform: string
  confidence: number
  filename: string
}

export const detectPlatform = async (file: File): Promise<DetectPlatformResult> => {
  const formData = new FormData()
  formData.append('file', file)
  // Do NOT set Content-Type manually — axios must let the browser set it
  // so it includes the multipart boundary automatically.
  const res = await apiClient.post<DetectPlatformResult>('/projects/detect-platform', formData)
  return res.data
}

export const uploadProject = async (formData: FormData): Promise<Project> => {
  const res = await apiClient.post<Project>('/projects/upload', formData)
  return res.data
}

export const uploadLogs = async (projectId: string, files: File[]): Promise<void> => {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  await apiClient.post(`/projects/${projectId}/logs`, formData)
}

export const pasteErrorText = async (projectId: string, errorText: string): Promise<void> => {
  await apiClient.post('/projects/paste-error', {
    project_id: projectId,
    error_text: errorText,
  })
}

export const listProjects = async (page = 1, size = 20, platform?: string): Promise<ProjectListResponse> => {
  const params: Record<string, unknown> = { page, size }
  if (platform) params.platform = platform
  const res = await apiClient.get<ProjectListResponse>('/projects', { params })
  return res.data
}

export const getProject = async (id: string): Promise<Project> => {
  const res = await apiClient.get<Project>(`/projects/${id}`)
  return res.data
}

export const deleteProject = async (id: string): Promise<void> => {
  await apiClient.delete(`/projects/${id}`)
}
