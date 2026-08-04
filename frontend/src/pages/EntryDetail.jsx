import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { deleteEntry, deleteRating, getEntry, photoUrl, reextractEntry, updateEntry, updateRating } from '../api'
import { beanProfileDisplayName } from '../utils/beanProfileDisplay'
import Field from '../components/Field'
import RatingRow from '../components/RatingRow'

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
  ['roast_location', 'Roasted in'],
]

const BAG_DETAIL_EDIT_FIELDS = [
  ['origin_country', 'Origin country', 'text'],
  ['region', 'Region', 'text'],
  ['farm_producer', 'Farm/producer', 'text'],
  ['altitude_m', 'Altitude (m)', 'number'],
  ['variety', 'Variety', 'text'],
  ['process', 'Process', 'text'],
  ['co_ferment_ingredient', 'Co-ferment ingredient', 'text'],
  ['certifications', 'Certifications', 'text'],
  ['roast_level', 'Roast level', 'text'],
  ['printed_tasting_notes', 'Printed tasting notes', 'text'],
  ['roast_date', 'Roast date', 'date'],
  ['bag_weight_g', 'Bag weight (g)', 'number'],
  ['batch_number', 'Batch number', 'text'],
  ['roast_location', 'Roasted in', 'text'],
]

function Value({ value }) {
  return value === null || value === undefined || value === '' ? (
    <span className="text-gray-400">Not identified</span>
  ) : (
    <span>{value}</span>
  )
}

function PhotoGrid({ photos }) {
  return (
    <div className="mb-4 flex flex-wrap gap-2">
      {photos.map((photo) => (
        <a key={photo.id} href={photoUrl(photo.id)} target="_blank" rel="noreferrer">
          <img
            src={photoUrl(photo.id)}
            alt=""
            className="h-24 w-24 rounded object-cover border border-gray-200"
          />
        </a>
      ))}
    </div>
  )
}

export default function EntryDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [entry, setEntry] = useState(null)
  const [error, setError] = useState(null)
  const [editingDetails, setEditingDetails] = useState(false)
  const [detailsForm, setDetailsForm] = useState(null)
  const [savingDetails, setSavingDetails] = useState(false)
  const [reextracting, setReextracting] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const loadEntry = () => getEntry(id).then(setEntry).catch((e) => setError(e.message))

  useEffect(() => {
    loadEntry()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  if (error) return <div className="p-6 text-sm text-red-600">{error}</div>
  if (!entry) return <div className="p-6 text-sm text-gray-500">Loading...</div>

  const startEditingDetails = () => {
    const form = {}
    for (const [key] of BAG_DETAIL_EDIT_FIELDS) {
      form[key] = entry[key] ?? ''
    }
    form.co_ferment_status = entry.co_ferment_status
    form.price_paid = entry.price_paid ?? ''
    form.currency = entry.currency ?? ''
    setDetailsForm(form)
    setEditingDetails(true)
  }

  const handleSaveDetails = async () => {
    setSavingDetails(true)
    setError(null)
    try {
      const payload = { co_ferment_status: detailsForm.co_ferment_status }
      for (const [key, , type] of BAG_DETAIL_EDIT_FIELDS) {
        const raw = detailsForm[key]
        payload[key] = raw === '' ? null : type === 'number' ? Number(raw) : raw
      }
      payload.price_paid = detailsForm.price_paid === '' ? null : Number(detailsForm.price_paid)
      payload.currency = detailsForm.currency || null
      const updated = await updateEntry(entry.id, payload)
      setEntry(updated)
      setEditingDetails(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingDetails(false)
    }
  }

  const handleReextract = async () => {
    setReextracting(true)
    try {
      const updated = await reextractEntry(entry.id)
      setEntry(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setReextracting(false)
    }
  }

  const handleDeleteEntry = async () => {
    if (!window.confirm('Delete this entry? This also removes its photos and ratings. This cannot be undone.')) {
      return
    }
    setDeleting(true)
    try {
      await deleteEntry(entry.id)
      navigate('/history')
    } catch (err) {
      setError(err.message)
      setDeleting(false)
    }
  }

  const handleSaveRating = async (ratingId, data) => {
    const updated = await updateRating(entry.id, ratingId, data)
    setEntry(updated)
  }

  const handleDeleteRating = async (ratingId) => {
    const updated = await deleteRating(entry.id, ratingId)
    setEntry(updated)
  }

  return (
    <div className="mx-auto max-w-md p-6 pb-24">
      <Link to="/history" className="mb-4 block text-sm text-purple-700">
        ← Back to History
      </Link>

      <span className="mb-2 inline-block rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-600">
        {entry.entry_type === 'bag' ? 'Bag' : 'Cafe'}
      </span>
      <h1 className="text-lg font-semibold text-gray-900">
        {beanProfileDisplayName(entry.bean_profile, entry.extraction_status)}
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
        {entry.photos.length > 0 && (
          <button
            type="button"
            onClick={handleReextract}
            disabled={reextracting || entry.extraction_status === 'pending'}
            className="mt-2 rounded-md border border-purple-700 px-3 py-1 text-xs font-medium text-purple-700 disabled:opacity-50"
          >
            {reextracting ? 'Re-running...' : 'Re-run AI extraction'}
          </button>
        )}
      </div>

      {entry.photos.length > 0 && (
        <>
          <h2 className="mb-2 text-sm font-semibold text-gray-900">Photos</h2>
          <PhotoGrid photos={entry.photos} />
        </>
      )}

      {entry.related_photos.length > 0 && (
        <>
          <h2 className="mb-2 text-sm font-semibold text-gray-900">Photos from other entries of this bean</h2>
          <PhotoGrid photos={entry.related_photos} />
        </>
      )}

      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Bag details</h2>
        {!editingDetails ? (
          <button type="button" onClick={startEditingDetails} className="text-xs font-medium text-purple-700">
            Edit
          </button>
        ) : (
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setEditingDetails(false)}
              className="text-xs font-medium text-gray-500"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSaveDetails}
              disabled={savingDetails}
              className="text-xs font-medium text-purple-700 disabled:opacity-50"
            >
              {savingDetails ? 'Saving...' : 'Save'}
            </button>
          </div>
        )}
      </div>

      {editingDetails ? (
        <div className="mb-4 grid grid-cols-2 gap-3 rounded-md border border-gray-200 p-3 text-sm">
          {BAG_DETAIL_EDIT_FIELDS.map(([key, label, type]) => (
            <Field
              key={key}
              label={label}
              type={type}
              value={detailsForm[key]}
              onChange={(e) => setDetailsForm((f) => ({ ...f, [key]: e.target.value }))}
            />
          ))}
          <div>
            <label className="block text-xs text-gray-600">Co-ferment</label>
            <select
              value={detailsForm.co_ferment_status}
              onChange={(e) => setDetailsForm((f) => ({ ...f, co_ferment_status: e.target.value }))}
              className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1"
            >
              <option value="unknown">Unknown</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </div>
          <Field
            label="Price paid"
            type="number"
            value={detailsForm.price_paid}
            onChange={(e) => setDetailsForm((f) => ({ ...f, price_paid: e.target.value }))}
          />
          <Field
            label="Currency"
            value={detailsForm.currency}
            onChange={(e) => setDetailsForm((f) => ({ ...f, currency: e.target.value }))}
          />
        </div>
      ) : (
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
      )}

      {entry.farms.length > 0 && (
        <>
          <h2 className="mb-2 text-sm font-semibold text-gray-900">Farms</h2>
          <ul className="mb-4 divide-y divide-gray-200 rounded-md border border-gray-200 text-sm">
            {entry.farms.map((farm, i) => (
              <li key={`${farm.farm_name}-${i}`} className="flex items-center justify-between p-3">
                <span>{farm.farm_name}</span>
                <Value value={farm.location} />
              </li>
            ))}
          </ul>
        </>
      )}

      <h2 className="mb-2 text-sm font-semibold text-gray-900">
        Ratings ({entry.ratings.length})
      </h2>
      <ul className="mb-6 divide-y divide-gray-200 rounded-md border border-gray-200">
        {entry.ratings.map((rating) => (
          <RatingRow
            key={rating.id}
            rating={rating}
            onSave={(data) => handleSaveRating(rating.id, data)}
            onDelete={() => handleDeleteRating(rating.id)}
          />
        ))}
      </ul>

      <button
        type="button"
        onClick={handleDeleteEntry}
        disabled={deleting}
        className="text-sm font-medium text-red-600 disabled:opacity-50"
      >
        {deleting ? 'Deleting...' : 'Delete entry'}
      </button>
    </div>
  )
}
