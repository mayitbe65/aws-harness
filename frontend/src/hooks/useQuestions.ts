 
import { useState, useEffect, useCallback } from 'react'
import type { Question } from '@/types/models'
import { questionService } from '@/services/question'

interface UseQuestionsOptions {
  page?: number
  pageSize?: number
  subject?: string
  needsReviewOnly?: boolean
}

export const useQuestions = (options: UseQuestionsOptions = {}) => {
  const { page = 1, pageSize = 20, subject, needsReviewOnly = false } = options

  const [questions, setQuestions] = useState<Question[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await questionService.list(page, pageSize, subject, needsReviewOnly)
      setQuestions(response.data.items)
      setTotal(response.data.total)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to load questions')
    } finally {
      setIsLoading(false)
    }
  }, [page, pageSize, subject, needsReviewOnly])

   
  useEffect(() => {
    void fetch()
  }, [fetch])

  return { questions, total, isLoading, error, refetch: fetch }
}
