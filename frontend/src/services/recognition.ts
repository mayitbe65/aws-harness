import api from '@/services/api'

export interface RecognitionResultData {
  recognized_text: string
  confidence: number
  has_formulas: boolean
  has_diagrams: boolean
}

export interface RecognitionResponse {
  status: string
  quality: 'high' | 'medium' | 'low'
  result?: RecognitionResultData
  message: string
  needs_manual_review: boolean
  photo_url?: string
}

export const recognitionService = {
  upload: (formData: FormData) =>
    api.post<RecognitionResponse>('/api/recognition/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}
