import api from '@/services/api'
import type { Question } from '@/types/models'

export interface QuestionListResponse {
  items: Question[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface CreateQuestionRequest {
  photo_url?: string
  recognized_text: string
  confidence: number
  subject: string
  difficulty: number
  tags?: string
}

export interface UpdateQuestionRequest {
  recognized_text?: string
  subject?: string
  difficulty?: number
  tags?: string
  needs_review?: boolean
  review_notes?: string
}

export const questionService = {
  list: (page: number, pageSize: number, subject?: string, needsReviewOnly?: boolean) =>
    api.get<QuestionListResponse>('/api/questions', {
      params: {
        page,
        page_size: pageSize,
        ...(subject && { subject }),
        ...(needsReviewOnly && { needs_review_only: needsReviewOnly }),
      },
    }),

  get: (questionId: string) =>
    api.get<Question>(`/api/questions/${questionId}`),

  create: (data: CreateQuestionRequest) =>
    api.post<Question>('/api/questions/create', data),

  update: (questionId: string, data: UpdateQuestionRequest) =>
    api.put<Question>(`/api/questions/${questionId}`, data),

  delete: (questionId: string) =>
    api.delete(`/api/questions/${questionId}`),
}
