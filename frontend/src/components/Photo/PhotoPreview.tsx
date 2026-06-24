import React from 'react'
import styles from '@/styles/PhotoPreview.module.css'

interface PhotoPreviewProps {
  src: string
  alt?: string
}

export const PhotoPreview: React.FC<PhotoPreviewProps> = ({ src, alt = 'Preview' }) => {
  return (
    <div className={styles.container}>
      <img src={src} alt={alt} className={styles.image} />
    </div>
  )
}
