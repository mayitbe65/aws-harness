import React, { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import styles from '@/styles/Login.module.css'

export const Login: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [formError, setFormError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { login, isLoading, error } = useAuth()
  const navigate = useNavigate()

  const validateForm = (): boolean => {
    if (!email || !password) {
      setFormError('邮箱和密码不能为空')
      return false
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      setFormError('请输入有效的邮箱地址')
      return false
    }

    if (password.length < 6) {
      setFormError('密码至少需要 6 个字符')
      return false
    }

    return true
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setFormError('')

    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setFormError(error.response?.data?.detail || '登录失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  const displayError = formError || error

  return (
    <div className={styles.loginContainer}>
      <div className={styles.loginBox}>
        <h1 className={styles.title}>错题宝</h1>
        <p className={styles.subtitle}>智能学习系统</p>

        <form onSubmit={handleSubmit} className={styles.form}>
          {displayError && (
            <div className={styles.errorAlert}>
              {displayError}
            </div>
          )}

          <div className={styles.formGroup}>
            <label htmlFor="email">邮箱</label>
            <input
              id="email"
              type="email"
              placeholder="student@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isSubmitting}
              className={styles.input}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password">密码</label>
            <input
              id="password"
              type="password"
              placeholder="输入密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isSubmitting}
              className={styles.input}
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting || isLoading}
            className={styles.submitButton}
          >
            {isSubmitting ? '登录中...' : '登录'}
          </button>
        </form>

        <p className={styles.footer}>
          还没有账号？请联系管理员
        </p>
      </div>
    </div>
  )
}
