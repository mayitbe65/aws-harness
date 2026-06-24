import React from 'react'
import type { ReviewItemResponse } from '@/services/recommendation'
import { ReviewCard } from './ReviewCard'
import styles from '@/styles/RecommendList.module.css'

interface RecommendListProps {
  items: ReviewItemResponse[]
  selectedIdx: number | null
  onSelectIdx: (idx: number) => void
  isEmpty: boolean
}

export const RecommendList: React.FC<RecommendListProps> = ({
  items,
  selectedIdx,
  onSelectIdx,
  isEmpty,
}) => {
  if (isEmpty) {
    return <p className={styles.empty}>太棒了！所有题目都已掌握 🎉</p>
  }

  return (
    <div className={styles.grid}>
      {items.map((q, idx) => (
        <ReviewCard
          key={q.question_id}
          question={q}
          isSelected={selectedIdx === idx}
          onClick={() => onSelectIdx(idx)}
        />
      ))}
    </div>
  )
}
