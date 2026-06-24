import React, { useState } from 'react'
import type { Question } from '@/types/models'
import styles from '@/styles/ExportForm.module.css'

interface ExportFormProps {
  questions: Question[]
  onSubmit: (data: {
    questionIds: string[]
    format: 'pdf' | 'html'
    groupBy: 'subject' | 'difficulty' | 'none'
    includeAnswers: boolean
  }) => Promise<void>
  isLoading?: boolean
}

export const ExportForm: React.FC<ExportFormProps> = ({
  questions,
  onSubmit,
  isLoading,
}) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [format, setFormat] = useState<'pdf' | 'html'>('pdf')
  const [groupBy, setGroupBy] = useState<'subject' | 'difficulty' | 'none'>('subject')
  const [includeAnswers, setIncludeAnswers] = useState(false)
  const [error, setError] = useState('')

  const toggleQuestion = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const toggleAll = () => {
    if (selectedIds.size === questions.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(questions.map((q) => q.question_id)))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (selectedIds.size === 0) {
      setError('请至少选择一个题目')
      return
    }

    try {
      await onSubmit({
        questionIds: Array.from(selectedIds),
        format,
        groupBy,
        includeAnswers,
      })
    } catch (err: unknown) {
      const error = err as { message?: string }
      setError(error.message || 'Export failed')
    }
  }

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <div className={styles.section}>
        <h3>选择题目</h3>
        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.selectAll}>
          <label>
            <input
              type="checkbox"
              checked={selectedIds.size === questions.length && questions.length > 0}
              onChange={toggleAll}
            />
            {' '}全选 ({selectedIds.size}/{questions.length})
          </label>
        </div>

        <div className={styles.questionList}>
          {questions.map((q) => (
            <div key={q.question_id} className={styles.questionItem}>
              <label>
                <input
                  type="checkbox"
                  checked={selectedIds.has(q.question_id)}
                  onChange={() => toggleQuestion(q.question_id)}
                />
                <span className={styles.text}>
                  {q.recognized_text.substring(0, 60)}... ({q.subject})
                </span>
              </label>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.section}>
        <h3>导出设置</h3>

        <div className={styles.formGroup}>
          <label>导出格式</label>
          <select value={format} onChange={(e) => setFormat(e.target.value as any)}>
            <option value="pdf">PDF（推荐）</option>
            <option value="html">HTML（可打印）</option>
          </select>
        </div>

        <div className={styles.formGroup}>
          <label>分组方式</label>
          <select value={groupBy} onChange={(e) => setGroupBy(e.target.value as any)}>
            <option value="subject">按科目</option>
            <option value="difficulty">按难度</option>
            <option value="none">不分组</option>
          </select>
        </div>

        <div className={styles.formGroup}>
          <label>
            <input
              type="checkbox"
              checked={includeAnswers}
              onChange={(e) => setIncludeAnswers(e.target.checked)}
            />
            {' '}包含答案（如可用）
          </label>
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading || selectedIds.size === 0}
        className={styles.submitButton}
      >
        {isLoading ? '生成中...' : '生成导出'}
      </button>
    </form>
  )
}
