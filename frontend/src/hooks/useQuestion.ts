import { useState, useEffect, useCallback } from 'react'
import type { Question } from '@/types/models'
import { questionService, type UpdateQuestionRequest } from '@/services/question'

export const useQuestion = (questionId: string) => {
  const [question, setQuestion] = useState<Question | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await questionService.get(questionId)
      setQuestion(response.data)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to load question')
    } finally {
      setIsLoading(false)
    }
  }, [questionId])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    // Data fetching effect - calling setState in effect is intentional pattern
    void fetch()
  }, [fetch])

  const update = async (data: UpdateQuestionRequest): Promise<Question> => {
    try {
      const response = await questionService.update(questionId, data)
      setQuestion(response.data)
      return response.data
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      const errorMsg = error.response?.data?.detail || 'Failed to update question'
      setError(errorMsg)
      throw err
    }
  }

  const deleteQuestion = async (): Promise<void> => {
    try {
      await questionService.delete(questionId)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      const errorMsg = error.response?.data?.detail || 'Failed to delete question'
      setError(errorMsg)
      throw err
    }
  }

  return { question, isLoading, error, update, delete: deleteQuestion, refetch: fetch }
}
