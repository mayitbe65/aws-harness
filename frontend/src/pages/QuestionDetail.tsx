import React from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuestion } from '@/hooks/useQuestion'
import { useAuthGuard } from '@/hooks/useAuthGuard'
import styles from '@/styles/QuestionDetail.module.css'

const SUBJECT_LABELS: Record<string, string> = {
  math: '数学',
  physics: '物理',
  chemistry: '化学',
  biology: '生物',
  english: '英语',
}

export const QuestionDetail: React.FC = () => {
  useAuthGuard()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const questionId = id || ''
  const { question, isLoading, error } = useQuestion(questionId)

  if (!id) return <div>无效的题目 ID</div>
  if (isLoading) return <div className={styles.loading}>加载中...</div>
  if (error) return <div className={styles.error}>{error}</div>
  if (!question) return <div>题目不存在</div>

  return (
    <div className={styles.container}>
      <h1>题目详情</h1>

      {question.photo_url && (
        <img
          src={question.photo_url}
          alt="question"
          className={styles.image}
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
        />
      )}

      <div className={styles.infoSection}>
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>题目内容</span>
          <p className={styles.infoValue}>{question.recognized_text}</p>
        </div>

        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>科目</span>
          <span className={styles.infoValue}>
            {SUBJECT_LABELS[question.subject] ?? question.subject}
          </span>
        </div>

        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>难度</span>
          <span className={styles.infoValue}>
            {'★'.repeat(question.difficulty)}{'☆'.repeat(5 - question.difficulty)}
          </span>
        </div>

        {question.tags && (
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>标签</span>
            <div className={styles.tags}>
              {question.tags.split(',').filter(Boolean).map((tag) => (
                <span key={tag.trim()} className={styles.tag}>{tag.trim()}</span>
              ))}
            </div>
          </div>
        )}

        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>错误次数</span>
          <span className={styles.infoValue}>{question.error_count}</span>
        </div>

        {question.needs_review && (
          <div className={styles.reviewBadge}>需审核</div>
        )}

        {question.review_notes && (
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>审核备注</span>
            <p className={styles.infoValue}>{question.review_notes}</p>
          </div>
        )}
      </div>

      <div className={styles.actions}>
        <Link to={`/question/${id}/edit`} className={styles.editButton}>
          编辑
        </Link>
        <button type="button" onClick={() => navigate('/')} className={styles.backButton}>
          返回
        </button>
      </div>
    </div>
  )
}
