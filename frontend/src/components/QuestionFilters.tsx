import React from 'react'
import styles from '@/styles/QuestionFilters.module.css'

interface QuestionFiltersProps {
  subject?: string
  onSubjectChange: (subject: string) => void
  needsReviewOnly: boolean
  onNeedsReviewChange: (checked: boolean) => void
}

export const QuestionFilters: React.FC<QuestionFiltersProps> = ({
  subject = '',
  onSubjectChange,
  needsReviewOnly,
  onNeedsReviewChange,
}) => {
  return (
    <div className={styles.filters}>
      <div className={styles.group}>
        <label>科目</label>
        <select value={subject} onChange={(e) => onSubjectChange(e.target.value)}>
          <option value="">全部</option>
          <option value="math">数学</option>
          <option value="physics">物理</option>
          <option value="chemistry">化学</option>
          <option value="biology">生物</option>
          <option value="english">英语</option>
        </select>
      </div>

      <div className={styles.group}>
        <label>
          <input
            type="checkbox"
            checked={needsReviewOnly}
            onChange={(e) => onNeedsReviewChange(e.target.checked)}
          />
          {' '}仅显示需审核
        </label>
      </div>
    </div>
  )
}
