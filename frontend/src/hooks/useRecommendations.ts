/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect, useCallback } from 'react'
import type { RecommendationListResponse } from '@/services/recommendation'
import { recommendationService } from '@/services/recommendation'

export const useRecommendations = (limit: number = 10) => {
  const [data, setData] = useState<RecommendationListResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await recommendationService.getRecommendations(limit)
      setData(response.data)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to load recommendations')
    } finally {
      setIsLoading(false)
    }
  }, [limit])

   
  useEffect(() => {
    void fetch()
  }, [fetch])

  return { data, isLoading, error, refetch: fetch }
}
