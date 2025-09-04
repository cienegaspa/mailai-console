import { Routes, Route } from 'react-router-dom'

import Layout from './components/Layout'
import RunsList from './pages/RunsList'
import RunDetail from './pages/RunDetail'
import EvidenceViewer from './pages/EvidenceViewer'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<RunsList />} />
        <Route path="/runs/:runId" element={<RunDetail />} />
        <Route path="/runs/:runId/evidence/:threadId" element={<EvidenceViewer />} />
      </Routes>
    </Layout>
  )
}

export default App