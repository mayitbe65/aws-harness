export interface User {
  user_id: string
  email: string
  name: string
  role: 'admin' | 'student'
  created_at: string
}

export interface Question {
  question_id: string
  user_id: string
  photo_url: string
  recognized_text: string
  confidence: number
  subject: string
  difficulty: number
  error_count: number
  needs_review: boolean
  review_notes?: string
  tags?: string
  created_at: string
  updated_at: string
}
