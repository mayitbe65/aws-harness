import { useState, useCallback } from 'react'
import { recognitionService } from '@/services/recognition'
import type { RecognitionResponse } from '@/services/recognition'

export const usePhotoUpload = () => {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string>('')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [recognition, setRecognition] = useState<RecognitionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFileSelect = useCallback((selectedFile: File) => {
    // Validate file type
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(selectedFile.type)) {
      setError('只支持 JPEG、PNG、WebP 格式')
      return
    }

    // Validate file size (10MB max)
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('文件大小不能超过 10MB')
      return
    }

    setFile(selectedFile)
    setError(null)

    // Create preview
    const reader = new FileReader()
    reader.onload = (e) => {
      setPreview(e.target?.result as string)
    }
    reader.readAsDataURL(selectedFile)
  }, [])

  const upload = useCallback(async () => {
    if (!file) {
      setError('请选择图片')
      return
    }

    setIsUploading(true)
    setUploadProgress(0)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await recognitionService.upload(formData)
      setRecognition(response.data)

      // Simulate progress completion
      setUploadProgress(100)
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || '上传失败'
      setError(message)
    } finally {
      setIsUploading(false)
    }
  }, [file])

  const reset = useCallback(() => {
    setFile(null)
    setPreview('')
    setRecognition(null)
    setUploadProgress(0)
    setError(null)
  }, [])

  return {
    file,
    preview,
    isUploading,
    uploadProgress,
    recognition,
    error,
    handleFileSelect,
    upload,
    reset,
  }
}
