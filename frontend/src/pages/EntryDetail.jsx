import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getEntry } from '../api'

const BAG_DETAIL_FIELDS = [
  ['origin_country', 'Origin country'],
  ['region', 'Region'],
  ['farm_producer', 'Farm/producer'],
  ['altitude_m', 'Altitude (m)'],
  ['variety', 'Variety'],
  ['process', 'Process'],
  ['co_ferment_status', 'Co-ferment'],
  ['co_ferment_ingredient', 'Co-ferment ingredient'],
  ['certifications', 'Certifications'],
  ['roast_level', 'Roast level'],
  ['printed_tasting_notes', 'Printed tasting notes'],
  ['roast_date', 'Roast date'],
  ['bag_weight_g', 'Bag weight (g)'],
  ['batch_number', 'Batch number'],
]

function Value({ value }) {
  return value === null || value === undefined || value === '' ? (
    <span className="text-gray-400">Not identified</span>
  ) : (
    <span>{value}</span>
  )
}

export default function EntryDetail() {
  const { id } = useParams()
  const [entry, setEntry] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getEntry(id).then(setEntry).catch((e) => setError(e.message))
  }, [id])

  if (error) return <div className="p-6 text-sm text-red-600">{error}</div>
  if (!entry) return <div className="p-6 text-sm text-gray-500">Loading...</div>

  return (
    <div className="mx-auto max-w-md p-6 pb-24">
      <Link to="/history" className="mb-4 block text-sm text-purple-700">
        ← Back to History
      </Link>

      <span className="mb-2 inline-block rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-600">
        {entry.entry_type === 'bag' ? 'Bag' : 'Cafe'}
      </span>
      <h1 className="text-lg font-semibold text-gray-900">
        {entry.bean_profile.roaster} — {entry.bean_profile.bean_name}
      </h1>
      {entry.cafe_name && <p className="text-sm text-gray-500">{entry.cafe_name}</p>}
      <p className="mb-4 text-sm text-gray-500">
        {entry.entry_date ?? entry.date_entered.slice(0, 10)}
      </p>

      <div className="mb-4 rounded-md border border-gray-200 p-3 text-sm">
        <p>
          <span className="text-gray-500">Extraction status: </span>
          <span className="font-medium">{entry.extraction_status}</span>
        </p>
        {entry.extraction_source && (
          <p>
            <span className="text-gray-500">Source: </span>
            <span className="font-medium">{entry.extraction_source}</span>
          </p>
        )}
      </div>

      <h2 className="mb-2 text-sm font-semibold text-gray-900">Bag details</h2>
      <div className="mb-4 grid grid-cols-2 gap-y-2 rounded-md border border-gray-200 p-3 text-sm">
        {BAG_DETAIL_FIELDS.map(([key, label]) => (
          <div key={key} className="col-span-2 grid grid-cols-2">
            <span className="text-gray-500">{label}</span>
            <Value value={entry[key]} />
          </div>
        ))}
        <div className="col-span-2 grid grid-cols-2">
          <span className="text-gray-500">Price paid</span>
          <Value value={entry.price_paid ? `${entry.price_paid} ${entry.currency}` : null} />
        </div>
      </div>

      <h2 className="mb-2 text-sm font-semibold text-gray-900">
        Ratings ({entry.ratings.length})
      </h2>
      <ul className="divide-y divide-gray-200 rounded-md border border-gray-200">
        {entry.ratings.map((rating) => (
          <li key={rating.id} className="p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-purple-700">{rating.score}</span>
              <span className="text-gray-500">{rating.date_entered.slice(0, 10)}</span>
            </div>
            {rating.narrative_notes && <p className="mt-1">{rating.narrative_notes}</p>}
            {(rating.acidity_score || rating.body_score || rating.sweetness_score) && (
              <p className="mt-1 text-gray-500">
                {rating.acidity_score ? `Acidity ${rating.acidity_score} ` : ''}
                {rating.body_score ? `Body ${rating.body_score} ` : ''}
                {rating.sweetness_score ? `Sweetness ${rating.sweetness_score}` : ''}
              </p>
            )}
            {rating.brew_style && <p className="text-gray-500">{rating.brew_style}</p>}
            {rating.repurchase && <p className="text-gray-500">Repurchase: {rating.repurchase}</p>}
          </li>
        ))}
      </ul>
    </div>
  )
}
