import React, { useEffect, useState } from 'react'
import type { SnapshotStatusResponse } from '@/services/export'
import styles from '@/styles/ExportProgress.module.css'

interface ExportProgressProps {
  status: SnapshotStatusResponse | null
  onDownload: (snapshotId: string, format: string) => void
}

export const ExportProgress: React.FC<ExportProgressProps> = ({ status, onDownload }) => {
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTime((t) => t + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  if (!status) return null

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}分${secs}秒`
  }

  const getStatusColor = (s: string) => {
    switch (s) {
      case 'pending':
      case 'generating':
        return '#ff9800'
      case 'completed':
        return '#4caf50'
      case 'failed':
        return '#f44336'
      default:
        return '#999'
    }
  }

  const getStatusText = (s: string) => {
    switch (s) {
      case 'pending':
        return '等待中'
      case 'generating':
        return '生成中'
      case 'completed':
        return '已完成'
      case 'failed':
        return '失败'
      default:
        return '未知'
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3>导出进度</h3>
        <span className={styles.time}>{formatTime(elapsedTime)}</span>
      </div>

      <div className={styles.statusBar}>
        <div
          className={styles.status}
          style={{
            backgroundColor: getStatusColor(status.status),
            width:
              status.status === 'completed'
                ? '100%'
                : status.status === 'generating'
                  ? '60%'
                  : '30%',
          }}
        />
      </div>

      <p className={styles.statusText}>{getStatusText(status.status)}</p>

      {status.status === 'completed' && (
        <button
          onClick={() => onDownload(status.snapshot_id, 'export.pdf')}
          className={styles.downloadButton}
        >
          📥 下载文件
        </button>
      )}

      {status.status === 'failed' && (
        <p className={styles.error}>错误: {status.error_message || '导出失败'}</p>
      )}
    </div>
  )
}
