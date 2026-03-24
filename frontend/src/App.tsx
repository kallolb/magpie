import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import Dashboard from '@/pages/Dashboard'
import Browse from '@/pages/Browse'
import Download from '@/pages/Download'
import VideoView from '@/pages/VideoView'
import Search from '@/pages/Search'
import Settings from '@/pages/Settings'
import Analytics from '@/pages/Analytics'
import Compilations from '@/pages/Compilations'
import CompilationEditor from '@/pages/CompilationEditor'

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/browse" element={<Browse />} />
          <Route path="/download" element={<Download />} />
          <Route path="/video/:id" element={<VideoView />} />
          <Route path="/search" element={<Search />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/compilations" element={<Compilations />} />
          <Route path="/compilations/:id" element={<CompilationEditor />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  )
}
