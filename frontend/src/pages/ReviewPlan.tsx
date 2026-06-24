import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthGuard } from '@/hooks/useAuthGuard'
import { useRecommendations } from '@/hooks/useRecommendations'
import { useMarkReviewed } from '@/hooks/useMarkReviewed'
import { useStudyStats } from '@/hooks/useStudyStats'
import { useAuth } from '@/hooks/useAuth'
import { RecommendList } from '@/components/Recommendation/RecommendList'
import { ReviewModal } from '@/components/Recommendation/ReviewModal'
import { StudyStatsPanel } from '@/components/Recommendation/StudyStatsPanel'
import styles from '@/styles/ReviewPlan.module.css'

export const ReviewPlan: React.FC = () => {
  useAuthGuard()
  const { logout } = useAuth()

  const { data, isLoading, error, refetch } = useRecommendations(10)
  const { stats } = useStudyStats()
  const { markReviewed, isLoading: isMarking } = useMarkReviewed()

  const [selectedQuestionIdx, setSelectedQuestionIdx] = useState<number | null>(null)

  const handleReviewComplete = async (reviewed: boolean) => {
    if (selectedQuestionIdx === null || !data) return

    const question = data.items[selectedQuestionIdx]

    try {
      await markReviewed(question.question_id, reviewed)

      // Move to next question
      if (selectedQuestionIdx < data.items.length - 1) {
        setSelectedQuestionIdx(selectedQuestionIdx + 1)
      } else {
        setSelectedQuestionIdx(null)
        await refetch()
      }
    } catch (err) {
      console.error('Review failed:', err)
    }
  }

  if (isLoading) return <div className={styles.loading}>加载中...</div>

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>错题宝</h1>
        <div className={styles.userMenu}>
          <button onClick={logout}>登出</button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.content}>
          {stats && <StudyStatsPanel stats={stats} />}

          <div className={styles.section}>
            <h2>推荐复习</h2>

            {error && <div className={styles.error}>{error}</div>}

            <RecommendList
              items={data?.items || []}
              selectedIdx={selectedQuestionIdx}
              onSelectIdx={setSelectedQuestionIdx}
              isEmpty={!data || data.items.length === 0}
            />
          </div>
        </div>
      </main>

      {selectedQuestionIdx !== null && data && (
        <ReviewModal
          question={data.items[selectedQuestionIdx]}
          onReviewComplete={handleReviewComplete}
          onClose={() => setSelectedQuestionIdx(null)}
        />
      )}

      <nav className={styles.nav}>
        <Link to="/">题目</Link>
        <Link to="/review">推荐</Link>
        <Link to="/export">导出</Link>
      </nav>
    </div>
  )
}
