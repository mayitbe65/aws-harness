import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Question } from '@/types/models'
import styles from '@/styles/QuestionCard.module.css'

interface QuestionCardProps {
  question: Question
  onDelete?: (id: string) => Promise<void>
}

export const QuestionCard: React.FC<QuestionCardProps> = ({ question, onDelete }) => {
  const [isDeleting, setIsDeleting] = useState(false)

  const handleDelete = async (): Promise<void> => {
    if (!window.confirm('确认删除此题目？')) return

    setIsDeleting(true)
    try {
      await onDelete?.(question.question_id)
    } catch (err) {
      console.error('Delete failed:', err)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className={styles.card}>
      <img src={question.photo_url} alt="question" className={styles.image} />

      <div className={styles.content}>
        <h3 className={styles.text}>
          {question.recognized_text.substring(0, 80)}...
        </h3>

        <div className={styles.meta}>
          <span className={styles.subject}>{question.subject}</span>
          <span className={styles.difficulty}>难度: {question.difficulty}</span>
          <span className={styles.errors}>错误: {question.error_count}</span>
        </div>

        {question.needs_review && (
          <div className={styles.badge}>需审核</div>
        )}

        <div className={styles.actions}>
          <Link to={`/question/${question.question_id}`} className={styles.button}>
            编辑
          </Link>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className={styles.deleteButton}
          >
            {isDeleting ? '删除中...' : '删除'}
          </button>
        </div>
      </div>
    </div>
  )
}
