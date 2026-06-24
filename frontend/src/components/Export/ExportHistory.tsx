import React from 'react'
import type { ExportHistoryResponse } from '@/services/export'
import styles from '@/styles/ExportHistory.module.css'

interface ExportHistoryProps {
  history: ExportHistoryResponse | null
  onDownload: (snapshotId: string, format: string) => void
}

export const ExportHistory: React.FC<ExportHistoryProps> = ({ history, onDownload }) => {
  if (!history || history.snapshots.length === 0) {
    return <p className={styles.empty}>暂无导出历史</p>
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: '#ff9800',
      generating: '#ff9800',
      completed: '#4caf50',
      failed: '#f44336',
    }
    return colors[status] || '#999'
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: '等待中',
      generating: '生成中',
      completed: '已完成',
      failed: '失败',
    }
    return labels[status] || status
  }

  return (
    <div className={styles.container}>
      <h3>导出历史</h3>
      <div className={styles.list}>
        {history.snapshots.map((item) => (
          <div key={item.snapshot_id} className={styles.item}>
            <div className={styles.info}>
              <div className={styles.id}>ID: {item.snapshot_id.substring(0, 8)}...</div>
              <div className={styles.date}>{formatDate(item.created_at)}</div>
              <span
                className={styles.status}
                style={{ backgroundColor: getStatusBadge(item.status) }}
              >
                {getStatusLabel(item.status)}
              </span>
            </div>

            {item.status === 'completed' && (
              <button
                onClick={() => onDownload(item.snapshot_id, 'export.pdf')}
                className={styles.downloadBtn}
              >
                下载
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
