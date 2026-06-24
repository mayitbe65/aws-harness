import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useQuestions } from '@/hooks/useQuestions'
import { useAuthGuard } from '@/hooks/useAuthGuard'
import { QuestionCard } from '@/components/QuestionCard'
import { QuestionFilters } from '@/components/QuestionFilters'
import { Pagination } from '@/components/Pagination'
import { questionService } from '@/services/question'
import styles from '@/styles/Dashboard.module.css'

export const Dashboard: React.FC = () => {
  useAuthGuard()
  const { currentUser, logout } = useAuth()

  const [page, setPage] = useState(1)
  const [subject, setSubject] = useState('')
  const [needsReviewOnly, setNeedsReviewOnly] = useState(false)

  const { questions, total, isLoading, error, refetch } = useQuestions({
    page,
    pageSize: 20,
    subject: subject || undefined,
    needsReviewOnly,
  })

  const handleDelete = async (questionId: string): Promise<void> => {
    try {
      await questionService.delete(questionId)
      await refetch()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  if (isLoading && questions.length === 0) {
    return <div className={styles.loading}>加载中...</div>
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>错题宝</h1>
        <div className={styles.userMenu}>
          <span>{currentUser?.email}</span>
          <button onClick={logout}>登出</button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.toolbar}>
          <h2>题目列表</h2>
          <Link to="/upload" className={styles.uploadButton}>
            + 拍照上传
          </Link>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <QuestionFilters
          subject={subject}
          onSubjectChange={(s) => {
            setSubject(s)
            setPage(1)
          }}
          needsReviewOnly={needsReviewOnly}
          onNeedsReviewChange={(checked) => {
            setNeedsReviewOnly(checked)
            setPage(1)
          }}
        />

        <div className={styles.grid}>
          {questions.length === 0 ? (
            <p className={styles.empty}>还没有题目，去拍照上传一些吧！</p>
          ) : (
            questions.map((q) => (
              <QuestionCard key={q.question_id} question={q} onDelete={handleDelete} />
            ))
          )}
        </div>

        {total > 0 && (
          <Pagination
            page={page}
            pageSize={20}
            total={total}
            onPageChange={setPage}
          />
        )}

        <nav className={styles.nav}>
          <Link to="/">题目</Link>
          <Link to="/review">推荐</Link>
          <Link to="/export">导出</Link>
        </nav>
      </main>
    </div>
  )
}
