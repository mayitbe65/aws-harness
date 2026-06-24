export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user_id: string
  role: string
  expires_in: number
}

export interface User {
  user_id: string
  email: string
  name?: string
  role: 'admin' | 'student'
}

export interface Question {
  question_id: string
  user_id: string
  photo_url: string
  recognized_text: string
  confidence: number
  subject: string
  difficulty: number
  needs_review: boolean
  created_at: string
}

export interface ApiError {
  detail?: string
  message?: string
}
