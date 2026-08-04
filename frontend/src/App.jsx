import { BrowserRouter, Routes, Route } from 'react-router-dom'
import TabBar from './components/TabBar'
import Home from './pages/Home'
import History from './pages/History'
import Insights from './pages/Insights'
import Export from './pages/Export'
import NewEntry from './pages/NewEntry'
import RatePrevious from './pages/RatePrevious'
import EntryDetail from './pages/EntryDetail'

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-svh flex-col bg-white text-gray-900">
        <main className="flex-1 pb-12">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/history" element={<History />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/export" element={<Export />} />
            <Route path="/entries/new" element={<NewEntry />} />
            <Route path="/entries/rate" element={<RatePrevious />} />
            <Route path="/entries/:id" element={<EntryDetail />} />
          </Routes>
        </main>
        <TabBar />
      </div>
    </BrowserRouter>
  )
}

export default App
