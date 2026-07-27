import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

const Login = lazy(() => import('./pages/Login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const UploadProject = lazy(() => import('./pages/UploadProject'))
const UploadLog = lazy(() => import('./pages/UploadLog'))
const AnalysisProgress = lazy(() => import('./pages/AnalysisProgress'))
const RCAResults = lazy(() => import('./pages/RCAResults'))
const History = lazy(() => import('./pages/History'))

const Spinner = () => (
  <div className="min-h-screen flex items-center justify-center bg-surface-1">
    <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
  </div>
)

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Spinner />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/upload/project" element={<UploadProject />} />
              <Route path="/upload/log" element={<UploadLog />} />
              <Route path="/analysis/:id/progress" element={<AnalysisProgress />} />
              <Route path="/analysis/:id/results" element={<RCAResults />} />
              <Route path="/history" element={<History />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
