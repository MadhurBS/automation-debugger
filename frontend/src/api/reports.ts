import apiClient from './client'

export const downloadPDF = async (reportId: string): Promise<void> => {
  const res = await apiClient.get(`/reports/${reportId}/pdf`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `rca_${reportId}.pdf`
  link.click()
  window.URL.revokeObjectURL(url)
}

export const downloadExcel = async (reportId: string): Promise<void> => {
  const res = await apiClient.get(`/reports/${reportId}/excel`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  }))
  const link = document.createElement('a')
  link.href = url
  link.download = `rca_${reportId}.xlsx`
  link.click()
  window.URL.revokeObjectURL(url)
}
