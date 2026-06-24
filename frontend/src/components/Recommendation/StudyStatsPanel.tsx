import React from 'react'
import type { StudyStatsResponse } from '@/services/recommendation'
import styles from '@/styles/StudyStatsPanel.module.css'

interface StudyStatsPanelProps {
  stats: StudyStatsResponse
}

export const StudyStatsPanel: React.FC<StudyStatsPanelProps> = ({ stats }) => {
  return (
    <div className={styles.panel}>
      <h3>学习统计</h3>

      <div className={styles.grid}>
        <div className={styles.stat}>
          <div className={styles.label}>总题数</div>
          <div className={styles.value}>{stats.total_questions}</div>
        </div>

        <div className={styles.stat}>
          <div className={styles.label}>已掌握</div>
          <div className={styles.value}>{stats.mastered_count}</div>
        </div>

        <div className={styles.stat}>
          <div className={styles.label}>掌握度</div>
          <div className={styles.value}>{stats.mastery_rate.toFixed(1)}%</div>
          <div className={styles.bar}>
            <div
              className={styles.fill}
              style={{ width: `${Math.min(stats.mastery_rate, 100)}%` }}
            />
          </div>
        </div>

        <div className={styles.stat}>
          <div className={styles.label}>今日复习</div>
          <div className={styles.value}>{stats.reviewed_today}</div>
        </div>

        <div className={styles.stat}>
          <div className={styles.label}>平均错误</div>
          <div className={styles.value}>{stats.average_errors_per_question.toFixed(1)}</div>
        </div>
      </div>
    </div>
  )
}
