import { useState, useEffect } from 'react'
import { exportService } from '@/services/export'
import type { ExportHistoryResponse } from '@/services/export'

export const useExportHistory = () => {
  const [history, setHistory] = useState<ExportHistoryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = async (page: number = 1) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await exportService.getHistory(page, 10)
      setHistory(response.data)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to load history')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void fetch()
  }, [])

  const download = async (snapshotId: string, filename: string) => {
    try {
      const response = await exportService.download(snapshotId)
      const blob =
        response.data instanceof Blob
          ? response.data
          : new Blob([response.data], { type: 'application/octet-stream' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError('Download failed')
    }
  }

  return { history, isLoading, error, fetch, download }
}
