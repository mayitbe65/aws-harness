import api from '@/services/api'

export interface ReviewItemResponse {
  question_id: string
  photo_url: string
  recognized_text: string
  subject: string
  difficulty: number
  error_count: number
  reviewed_count: number
  last_error_time: string
  last_reviewed_time?: string
  next_review_time: string
  priority: number
}

export interface RecommendationListResponse {
  items: ReviewItemResponse[]
  total_questions: number
  mastered_count: number
  total_by_subject: Record<string, number>
  generated_at: string
}

export interface MarkReviewedRequest {
  reviewed: boolean
}

export interface StudyStatsResponse {
  total_questions: number
  mastered_count: number
  mastery_rate: number
  reviewed_today: number
  average_errors_per_question: number
}

export const recommendationService = {
  getRecommendations: (limit: number = 10) =>
    api.get<RecommendationListResponse>('/api/recommendations/plan', {
      params: { limit },
    }),

  markReviewed: (planId: string, reviewed: boolean) =>
    api.post(`/api/recommendations/mark-reviewed/${planId}`, {
      reviewed,
    }),

  getStats: () =>
    api.get<StudyStatsResponse>('/api/recommendations/stats'),
}
