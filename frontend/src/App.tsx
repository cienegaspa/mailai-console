import { Routes, Route } from 'react-router-dom'

import Layout from './components/Layout'
import RunsList from './pages/RunsList'
import RunDetail from './pages/RunDetail'
import EvidenceViewer from './pages/EvidenceViewer'
import Accounts from './pages/Accounts'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<RunsList />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/runs/:runId" element={<RunDetail />} />
        <Route path="/runs/:runId/evidence/:threadId" element={<EvidenceViewer />} />
      </Routes>
    </Layout>
  )
}

export default App