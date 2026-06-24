import { useState } from 'react'
import { exportService } from '@/services/export'
import type { ExportRequest, ExportResponse } from '@/services/export'

export const useExport = () => {
  const [isRequesting, setIsRequesting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const requestExport = async (data: ExportRequest): Promise<ExportResponse | null> => {
    setIsRequesting(true)
    setError(null)
    try {
      const response = await exportService.requestPdf(data)
      return response.data
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      const message = error.response?.data?.detail || 'Export request failed'
      setError(message)
      return null
    } finally {
      setIsRequesting(false)
    }
  }

  return { requestExport, isRequesting, error }
}
