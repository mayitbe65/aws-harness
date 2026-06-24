import React from 'react'
import type { ReviewItemResponse } from '@/services/recommendation'
import styles from '@/styles/ReviewCard.module.css'

interface ReviewCardProps {
  question: ReviewItemResponse
  isSelected: boolean
  onClick: () => void
}

export const ReviewCard: React.FC<ReviewCardProps> = ({
  question,
  isSelected,
  onClick,
}) => {
  const nextReviewDays = Math.ceil(
    (new Date(question.next_review_time).getTime() - new Date().getTime()) /
      (1000 * 60 * 60 * 24)
  )

  return (
    <div
      className={`${styles.card} ${isSelected ? styles.selected : ''}`}
      onClick={onClick}
    >
      <img src={question.photo_url} alt="question" className={styles.image} />

      <div className={styles.content}>
        <p className={styles.text}>
          {question.recognized_text.substring(0, 60)}
          {question.recognized_text.length > 60 ? '...' : ''}
        </p>

        <div className={styles.meta}>
          <span className={styles.priority}>
            优先级: {(question.priority * 100).toFixed(0)}%
          </span>
          <span className={styles.difficulty}>难度: {question.difficulty}</span>
          <span className={styles.errors}>错误: {question.error_count}</span>
        </div>

        <div className={styles.schedule}>
          下次复习: {nextReviewDays > 0 ? `${nextReviewDays}天后` : '今天'}
        </div>
      </div>
    </div>
  )
}
