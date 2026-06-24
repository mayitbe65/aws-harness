import React from 'react'
import styles from '@/styles/QualityIndicator.module.css'

type Quality = 'high' | 'medium' | 'low'

const qualityConfig = {
  high: {
    label: '识别质量高',
    icon: '✓',
    color: '#4caf50',
    description: '可直接保存',
  },
  medium: {
    label: '识别质量一般',
    icon: '⚠',
    color: '#ff9800',
    description: '需要人工审核或编辑',
  },
  low: {
    label: '识别失败',
    icon: '✗',
    color: '#f44336',
    description: '建议重新拍照或手动输入',
  },
}

interface QualityIndicatorProps {
  quality: Quality
  confidence?: number
}

export const QualityIndicator: React.FC<QualityIndicatorProps> = ({
  quality,
  confidence,
}) => {
  const config = qualityConfig[quality]

  return (
    <div className={styles.container} style={{ borderColor: config.color }}>
      <div className={styles.icon} style={{ color: config.color }}>
        {config.icon}
      </div>
      <div className={styles.content}>
        <p className={styles.label}>{config.label}</p>
        <p className={styles.description}>{config.description}</p>
        {confidence !== undefined && (
          <p className={styles.confidence}>置信度: {(confidence * 100).toFixed(0)}%</p>
        )}
      </div>
    </div>
  )
}
