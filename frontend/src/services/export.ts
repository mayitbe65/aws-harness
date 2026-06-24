import api from '@/services/api'

export interface ExportRequest {
  question_ids: string[]
  format: 'pdf' | 'html'
  group_by: 'subject' | 'difficulty' | 'none'
  include_answers: boolean
}

export interface ExportResponse {
  snapshot_id: string
  status: string
  message: string
  estimated_time: number
}

export interface SnapshotStatusResponse {
  snapshot_id: string
  status: 'pending' | 'generating' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
  file_url?: string
  error_message?: string
}

export interface ExportHistoryResponse {
  snapshots: SnapshotStatusResponse[]
  total: number
}

export const exportService = {
  requestPdf: (data: ExportRequest) =>
    api.post<ExportResponse>('/api/export/pdf', data),

  getStatus: (snapshotId: string) =>
    api.get<SnapshotStatusResponse>(`/api/export/${snapshotId}`),

  download: (snapshotId: string) =>
    api.get(`/api/export/${snapshotId}/download`, {
      responseType: 'blob',
    }),

  getHistory: (page: number = 1, pageSize: number = 10) =>
    api.get<ExportHistoryResponse>('/api/export', {
      params: { page, page_size: pageSize },
    }),
}
