import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { Login } from '@/pages/Login'
import { Dashboard } from '@/pages/Dashboard'
import { QuestionDetail } from '@/pages/QuestionDetail'
import { QuestionEdit } from '@/pages/QuestionEdit'
import { PhotoUpload } from '@/pages/PhotoUpload'
import { ReviewPlan } from '@/pages/ReviewPlan'
import { Export } from '@/pages/Export'

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<PhotoUpload />} />
          <Route path="/question/:id" element={<QuestionDetail />} />
          <Route path="/question/:id/edit" element={<QuestionEdit />} />
          <Route path="/review" element={<ReviewPlan />} />
          <Route path="/export" element={<Export />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
