import React, { useState } from 'react'
import type { ReviewItemResponse } from '@/services/recommendation'
import styles from '@/styles/ReviewModal.module.css'

interface ReviewModalProps {
  question: ReviewItemResponse
  onReviewComplete: (reviewed: boolean) => Promise<void>
  onClose: () => void
}

export const ReviewModal: React.FC<ReviewModalProps> = ({
  question,
  onReviewComplete,
  onClose,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleReview = async (reviewed: boolean) => {
    setIsSubmitting(true)
    try {
      await onReviewComplete(reviewed)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeButton} onClick={onClose}>
          ✕
        </button>

        <img src={question.photo_url} alt="question" className={styles.image} />

        <div className={styles.content}>
          <p className={styles.text}>{question.recognized_text}</p>

          <div className={styles.meta}>
            <span>科目: {question.subject}</span>
            <span>难度: {question.difficulty}/5</span>
            <span>错误: {question.error_count}</span>
          </div>

          <div className={styles.actions}>
            <button
              onClick={() => handleReview(true)}
              disabled={isSubmitting}
              className={styles.correctButton}
            >
              ✓ 做对了
            </button>

            <button
              onClick={() => handleReview(false)}
              disabled={isSubmitting}
              className={styles.wrongButton}
            >
              ✗ 做错了
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
