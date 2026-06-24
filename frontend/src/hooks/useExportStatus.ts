import { useState, useEffect } from 'react'
import { exportService } from '@/services/export'
import type { SnapshotStatusResponse } from '@/services/export'

export const useExportStatus = (snapshotId: string, enabled: boolean = true) => {
  const [status, setStatus] = useState<SnapshotStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!enabled || !snapshotId) return

    const poll = async () => {
      setIsLoading(true)
      try {
        const response = await exportService.getStatus(snapshotId)
        setStatus(response.data)

        // Continue polling if not completed or failed
        if (
          response.data.status === 'pending' ||
          response.data.status === 'generating'
        ) {
          setTimeout(poll, 2000) // Poll every 2 seconds
        }
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } }
        setError(error.response?.data?.detail || 'Status check failed')
      } finally {
        setIsLoading(false)
      }
    }

    poll()
  }, [snapshotId, enabled])

  return { status, isLoading, error }
}
