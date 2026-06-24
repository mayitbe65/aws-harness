import React from 'react'
import { Link } from 'react-router-dom'
import { useAuthGuard } from '@/hooks/useAuthGuard'
import { usePhotoUpload } from '@/hooks/usePhotoUpload'
import { PhotoInput } from '@/components/Photo/PhotoInput'
import { PhotoPreview } from '@/components/Photo/PhotoPreview'
import { RecognitionResult } from '@/components/Photo/RecognitionResult'
import styles from '@/styles/PhotoUpload.module.css'

export const PhotoUpload: React.FC = () => {
  useAuthGuard()

  const {
    file,
    preview,
    isUploading,
    uploadProgress,
    recognition,
    error,
    handleFileSelect,
    upload,
    reset,
  } = usePhotoUpload()

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1>错题宝</h1>
          <Link to="/" className={styles.backLink}>
            ← 返回
          </Link>
        </div>
      </header>

      <main className={styles.main}>
        {!recognition ? (
          <div className={styles.upload}>
            <h2>拍照上传错题</h2>

            {!preview ? (
              <PhotoInput onFileSelect={handleFileSelect} disabled={isUploading} />
            ) : (
              <div className={styles.previewSection}>
                <PhotoPreview src={preview} />

                {!isUploading && (
                  <button
                    onClick={() => handleFileSelect(file!)}
                    className={styles.changeButton}
                  >
                    更换图片
                  </button>
                )}
              </div>
            )}

            {error && !recognition && <div className={styles.error}>{error}</div>}

            {preview && !isUploading && !recognition && (
              <button onClick={upload} className={styles.recognizeButton}>
                🤖 识别题目
              </button>
            )}

            {isUploading && (
              <div className={styles.progressContainer}>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className={styles.progressText}>{uploadProgress}%</p>
              </div>
            )}
          </div>
        ) : (
          <RecognitionResult result={recognition} photo={file!} onReset={reset} />
        )}
      </main>
    </div>
  )
}
