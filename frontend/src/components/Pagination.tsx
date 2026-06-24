import React from 'react'
import styles from '@/styles/Pagination.module.css'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}

export const Pagination: React.FC<PaginationProps> = ({
  page,
  pageSize,
  total,
  onPageChange,
}) => {
  const totalPages = Math.ceil(total / pageSize)

  const hasPrev = page > 1
  const hasNext = page < totalPages

  return (
    <div className={styles.pagination}>
      <button
        disabled={!hasPrev}
        onClick={() => onPageChange(page - 1)}
        className={styles.button}
      >
        上一页
      </button>

      <span className={styles.info}>
        第 {page} 页 / 共 {totalPages} 页 ({total} 条)
      </span>

      <button
        disabled={!hasNext}
        onClick={() => onPageChange(page + 1)}
        className={styles.button}
      >
        下一页
      </button>
    </div>
  )
}
