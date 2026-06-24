import React, { useRef } from 'react'
import styles from '@/styles/PhotoInput.module.css'

interface PhotoInputProps {
  onFileSelect: (file: File) => void
  disabled?: boolean
}

export const PhotoInput: React.FC<PhotoInputProps> = ({ onFileSelect, disabled = false }) => {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      onFileSelect(file)
    }
  }

  return (
    <div className={styles.container}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        disabled={disabled}
      />

      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      <div className={styles.buttons}>
        <button
          onClick={() => cameraInputRef.current?.click()}
          disabled={disabled}
          className={styles.cameraButton}
        >
          📷 拍照
        </button>

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className={styles.fileButton}
        >
          📁 选择图片
        </button>
      </div>

      <p className={styles.hint}>支持 JPEG、PNG、WebP，最大 10MB</p>
    </div>
  )
}
