import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { RecognitionResponse } from '@/services/recognition'
import { questionService } from '@/services/question'
import { QualityIndicator } from './QualityIndicator'
import styles from '@/styles/RecognitionResult.module.css'

interface RecognitionResultProps {
  result: RecognitionResponse
  photo?: File
  onReset: () => void
}


export const RecognitionResult: React.FC<RecognitionResultProps> = ({
  result,
  onReset,
}) => {
  const navigate = useNavigate()
  const [editedText, setEditedText] = useState(result.result?.recognized_text || '')
  const [subject, setSubject] = useState('math')
  const [difficulty, setDifficulty] = useState(3)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    if (!editedText.trim()) {
      setError('题目内容不能为空')
      return
    }

    setIsSaving(true)
    setError('')

    try {
      await questionService.create({
        photo_url: result.photo_url || undefined,
        recognized_text: editedText,
        confidence: result.result?.confidence || 0,
        subject,
        difficulty,
        tags: result.result?.has_formulas ? 'formulas' : '',
      })

      // Success - navigate to dashboard
      navigate('/', { replace: true })
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || '保存失败'
      setError(message)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className={styles.container}>
      <QualityIndicator quality={result.quality} confidence={result.result?.confidence} />

      <div className={styles.content}>
        <div className={styles.section}>
          <h3>识别结果</h3>
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            className={styles.textarea}
            placeholder="题目内容"
            rows={6}
          />
          {result.result?.has_formulas && <p className={styles.tag}>📐 包含数学公式</p>}
          {result.result?.has_diagrams && <p className={styles.tag}>📊 包含图表</p>}
        </div>

        <div className={styles.section}>
          <div className={styles.form}>
            <div className={styles.group}>
              <label>科目</label>
              <select value={subject} onChange={(e) => setSubject(e.target.value)}>
                <option value="math">数学</option>
                <option value="physics">物理</option>
                <option value="chemistry">化学</option>
                <option value="english">英语</option>
                <option value="biology">生物</option>
                <option value="history">历史</option>
                <option value="politics">政治</option>
                <option value="geography">地理</option>
              </select>
            </div>

            <div className={styles.group}>
              <label>难度: {difficulty}</label>
              <input
                type="range"
                min="1"
                max="5"
                value={difficulty}
                onChange={(e) => setDifficulty(parseInt(e.target.value))}
                className={styles.slider}
              />
              <div className={styles.difficultyLabels}>
                <span>简单</span>
                <span>困难</span>
              </div>
            </div>
          </div>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.actions}>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className={styles.saveButton}
          >
            {isSaving ? '保存中...' : '保存为题目'}
          </button>
          <button onClick={onReset} className={styles.retryButton} disabled={isSaving}>
            重新拍照
          </button>
        </div>

        <p className={styles.tip}>
          {result.quality === 'high'
            ? '识别质量高，可以直接保存'
            : result.quality === 'medium'
            ? '请检查识别结果是否准确后再保存'
            : '识别失败，请手动输入或重新拍照'}
        </p>
      </div>
    </div>
  )
}
