import React, { useState, useEffect, type FormEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuestion } from '@/hooks/useQuestion'
import { useAuthGuard } from '@/hooks/useAuthGuard'
import styles from '@/styles/QuestionDetail.module.css'

export const QuestionEdit: React.FC = () => {
  useAuthGuard()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [formData, setFormData] = useState({
    recognized_text: '',
    subject: 'math',
    difficulty: 3,
    tags: '',
    needs_review: false,
    review_notes: '',
  })
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const questionId = id || ''
  const { question, isLoading, error, update, delete: deleteQuestion } = useQuestion(questionId)

  useEffect(() => {
    if (question) {
      setFormData({
        recognized_text: question.recognized_text,
        subject: question.subject,
        difficulty: question.difficulty,
        tags: question.tags || '',
        needs_review: question.needs_review,
        review_notes: question.review_notes || '',
      })
    }
  }, [question])

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setIsSaving(true)
    setSaveError(null)
    try {
      await update(formData)
      navigate(`/question/${id}`, { replace: true })
    } catch (err) {
      setSaveError('保存失败，请重试')
      console.error('Save failed:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (): Promise<void> => {
    if (!window.confirm('确认删除此题目？')) return
    try {
      await deleteQuestion()
      navigate('/', { replace: true })
    } catch (err) {
      setSaveError('删除失败，请重试')
      console.error('Delete failed:', err)
    }
  }

  if (!id) return <div>无效的题目 ID</div>
  if (isLoading) return <div className={styles.loading}>加载中...</div>
  if (error) return <div className={styles.error}>{error}</div>
  if (!question) return <div>题目不存在</div>

  return (
    <div className={styles.container}>
      <h1>编辑题目</h1>

      {question.photo_url && (
        <img
          src={question.photo_url}
          alt="question"
          className={styles.image}
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
        />
      )}

      {saveError && <div className={styles.error}>{saveError}</div>}

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.group}>
          <label>题目内容</label>
          <textarea
            value={formData.recognized_text}
            onChange={(e) => setFormData({ ...formData, recognized_text: e.target.value })}
            rows={5}
            className={styles.textarea}
          />
        </div>

        <div className={styles.group}>
          <label>科目</label>
          <select
            value={formData.subject}
            onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
          >
            <option value="math">数学</option>
            <option value="physics">物理</option>
            <option value="chemistry">化学</option>
            <option value="biology">生物</option>
            <option value="english">英语</option>
          </select>
        </div>

        <div className={styles.group}>
          <label>难度 (1-5)</label>
          <input
            type="range"
            min="1"
            max="5"
            value={formData.difficulty}
            onChange={(e) => setFormData({ ...formData, difficulty: parseInt(e.target.value, 10) })}
          />
          <span>{formData.difficulty}</span>
        </div>

        <div className={styles.group}>
          <label>标签</label>
          <input
            type="text"
            value={formData.tags}
            onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
            placeholder="用逗号分隔多个标签"
          />
        </div>

        <div className={styles.group}>
          <label>
            <input
              type="checkbox"
              checked={formData.needs_review}
              onChange={(e) => setFormData({ ...formData, needs_review: e.target.checked })}
            />
            {' '}需要审核
          </label>
        </div>

        {formData.needs_review && (
          <div className={styles.group}>
            <label>审核备注</label>
            <textarea
              value={formData.review_notes}
              onChange={(e) => setFormData({ ...formData, review_notes: e.target.value })}
              rows={3}
            />
          </div>
        )}

        <div className={styles.actions}>
          <button type="submit" disabled={isSaving}>
            {isSaving ? '保存中...' : '保存'}
          </button>
          <button type="button" onClick={handleDelete}>
            删除
          </button>
          <button type="button" onClick={() => navigate(`/question/${id}`)}>
            取消
          </button>
        </div>
      </form>
    </div>
  )
}
