import { useNavigate } from 'react-router-dom'

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-[calc(100svh-48px)] flex-col items-center justify-center gap-4 p-6">
      <h1 className="mb-4 text-xl font-semibold text-gray-900">Coffee Bean Tracker</h1>
      <button
        type="button"
        onClick={() => navigate('/entries/new')}
        className="w-full max-w-xs rounded-lg bg-purple-700 px-6 py-4 text-lg font-medium text-white active:bg-purple-800"
      >
        + New Entry
      </button>
      <button
        type="button"
        onClick={() => navigate('/entries/rate')}
        className="w-full max-w-xs rounded-lg border border-gray-300 px-6 py-4 text-lg font-medium text-gray-800 active:bg-gray-100"
      >
        Rate a Previous Bean
      </button>
    </div>
  )
}
