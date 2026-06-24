/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect, useCallback } from 'react'
import {
  recommendationService,
  StudyStatsResponse,
} from '@/services/recommendation'

export const useStudyStats = () => {
  const [stats, setStats] = useState<StudyStatsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await recommendationService.getStats()
      setStats(response.data)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to load stats')
    } finally {
      setIsLoading(false)
    }
  }, [])

   
  useEffect(() => {
    void fetch()
  }, [fetch])

  return { stats, isLoading, error, refetch: fetch }
}
