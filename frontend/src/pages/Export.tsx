import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthGuard } from '@/hooks/useAuthGuard'
import { useQuestions } from '@/hooks/useQuestions'
import { useExport } from '@/hooks/useExport'
import { useExportStatus } from '@/hooks/useExportStatus'
import { useExportHistory } from '@/hooks/useExportHistory'
import { ExportForm } from '@/components/Export/ExportForm'
import { ExportProgress } from '@/components/Export/ExportProgress'
import { ExportHistory } from '@/components/Export/ExportHistory'
import styles from '@/styles/Export.module.css'

export const Export: React.FC = () => {
  useAuthGuard()

  const { questions } = useQuestions({ pageSize: 100 })
  const { requestExport, isRequesting } = useExport()
  const { history, download } = useExportHistory()

  const [currentSnapshotId, setCurrentSnapshotId] = useState<string | null>(null)
  const { status } = useExportStatus(currentSnapshotId || '', !!currentSnapshotId)

  const handleExportRequest = async (data: {
    questionIds: string[]
    format: 'pdf' | 'html'
    groupBy: 'subject' | 'difficulty' | 'none'
    includeAnswers: boolean
  }) => {
    const response = await requestExport({
      question_ids: data.questionIds,
      format: data.format,
      group_by: data.groupBy,
      include_answers: data.includeAnswers,
    })

    if (response) {
      setCurrentSnapshotId(response.snapshot_id)
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>错题宝</h1>
        <Link to="/">← 返回</Link>
      </header>

      <main className={styles.main}>
        <div className={styles.content}>
          {!currentSnapshotId ? (
            <ExportForm
              questions={questions}
              onSubmit={handleExportRequest}
              isLoading={isRequesting}
            />
          ) : (
            <div className={styles.progress}>
              <ExportProgress status={status} onDownload={download} />
              <button
                onClick={() => setCurrentSnapshotId(null)}
                className={styles.backButton}
              >
                新建导出
              </button>
            </div>
          )}

          <div className={styles.history}>
            <ExportHistory history={history} onDownload={download} />
          </div>
        </div>
      </main>

      <nav className={styles.nav}>
        <Link to="/">题目</Link>
        <Link to="/review">推荐</Link>
        <Link to="/export">导出</Link>
      </nav>
    </div>
  )
}
