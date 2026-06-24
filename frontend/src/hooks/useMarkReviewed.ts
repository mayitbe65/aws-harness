import { useState } from 'react'
import { recommendationService } from '@/services/recommendation'

export const useMarkReviewed = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const markReviewed = async (questionId: string, reviewed: boolean) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await recommendationService.markReviewed(questionId, reviewed)
      return response.data
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      const message = error.response?.data?.detail || 'Failed to mark review'
      setError(message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  return { markReviewed, isLoading, error }
}
