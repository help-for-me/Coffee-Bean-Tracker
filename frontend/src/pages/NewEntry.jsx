import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import BeanProfileAutocomplete from '../components/BeanProfileAutocomplete'
import AdvancedRatingFields from '../components/AdvancedRatingFields'
import Field from '../components/Field'
import { createEntry } from '../api'
import { emptyAdvancedRating, ratingPayloadFromAdvanced } from '../utils/ratingPayload'

const initialDetails = {
  origin_country: '',
  region: '',
  farm_producer: '',
  altitude_m: '',
  variety: '',
  process: '',
  co_ferment_status: 'unknown',
  co_ferment_ingredient: '',
  certifications: '',
  roast_level: '',
  printed_tasting_notes: '',
  roast_date: '',
  bag_weight_g: '',
  batch_number: '',
  roast_location: '',
  price_paid: '',
  currency: 'CAD',
  entry_date: '',
}

export default function NewEntry() {
  const navigate = useNavigate()
  const [entryType, setEntryType] = useState('bag')
  const [roaster, setRoaster] = useState('')
  const [beanName, setBeanName] = useState('')
  const [cafeName, setCafeName] = useState('')
  const [score, setScore] = useState('')
  const [narrativeNotes, setNarrativeNotes] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [advanced, setAdvanced] = useState(emptyAdvancedRating)
  const [showDetails, setShowDetails] = useState(false)
  const [details, setDetails] = useState(initialDetails)
  const [photos, setPhotos] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const updateDetail = (key) => (e) => setDetails((d) => ({ ...d, [key]: e.target.value }))
  const photoPreviews = useMemo(() => photos.map((file) => URL.createObjectURL(file)), [photos])
  const removePhoto = (index) => setPhotos((prev) => prev.filter((_, i) => i !== index))

  const hasIdentity = roaster.trim() && beanName.trim()
  const identityFromPhotoAllowed = entryType === 'bag' && photos.length > 0

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    if (!hasIdentity && !identityFromPhotoAllowed) {
      setError('Roaster and bean name are required, unless attaching a photo to a bag entry.')
      return
    }
    if (score === '' || Number(score) < 0 || Number(score) > 10) {
      setError('Score must be between 0 and 10.')
      return
    }
    setSubmitting(true)
    try {
      await createEntry({
        entry_type: entryType,
        roaster: roaster.trim() || null,
        bean_name: beanName.trim() || null,
        cafe_name: entryType === 'cafe_cup' && cafeName.trim() ? cafeName.trim() : null,
        entry_date: details.entry_date || null,
        price_paid: details.price_paid ? Number(details.price_paid) : null,
        currency: details.currency || 'CAD',
        origin_country: details.origin_country || null,
        region: details.region || null,
        farm_producer: details.farm_producer || null,
        altitude_m: details.altitude_m ? Number(details.altitude_m) : null,
        variety: details.variety || null,
        process: details.process || null,
        co_ferment_status: details.co_ferment_status || 'unknown',
        co_ferment_ingredient: details.co_ferment_ingredient || null,
        certifications: details.certifications || null,
        roast_level: details.roast_level || null,
        printed_tasting_notes: details.printed_tasting_notes || null,
        roast_date: details.roast_date || null,
        bag_weight_g: details.bag_weight_g ? Number(details.bag_weight_g) : null,
        batch_number: details.batch_number || null,
        roast_location: details.roast_location || null,
        score: Number(score),
        narrative_notes: narrativeNotes.trim() || null,
        ...ratingPayloadFromAdvanced(advanced),
      }, photos)
      navigate('/history')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-md p-6 pb-24">
      <h1 className="mb-4 text-lg font-semibold text-gray-900">New Entry</h1>

      <div className="mb-4 flex gap-2">
        {['bag', 'cafe_cup'].map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => setEntryType(type)}
            className={`flex-1 rounded-md border px-3 py-2 text-sm font-medium ${
              entryType === type
                ? 'border-purple-700 bg-purple-700 text-white'
                : 'border-gray-300 text-gray-700'
            }`}
          >
            {type === 'bag' ? 'Bag' : 'Cafe cup'}
          </button>
        ))}
      </div>

      {entryType === 'cafe_cup' && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700">Cafe name</label>
          <input
            value={cafeName}
            onChange={(e) => setCafeName(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
          />
        </div>
      )}

      <div className="mb-4">
        {entryType === 'bag' && (
          <p className="mb-1 text-xs text-gray-500">
            Optional if you attach a bag photo below - extraction will identify it for you.
          </p>
        )}
        <BeanProfileAutocomplete
          roaster={roaster}
          beanName={beanName}
          onRoaster={setRoaster}
          onBeanName={setBeanName}
          onSelect={(profile) => {
            setRoaster(profile.roaster)
            setBeanName(profile.bean_name)
          }}
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">Score (0-10)</label>
        <input
          type="number"
          min="0"
          max="10"
          step="0.5"
          value={score}
          onChange={(e) => setScore(e.target.value)}
          required
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">Notes (optional)</label>
        <input
          value={narrativeNotes}
          onChange={(e) => setNarrativeNotes(e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
          placeholder="Chocolatey, bright finish..."
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">Photos (optional)</label>
        <p className="mb-1 text-xs text-gray-500">
          Bag label, menu board, or info card. Origin, process, roast level, and tasting notes get
          filled in automatically in the background.
        </p>
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => setPhotos(Array.from(e.target.files ?? []))}
          className="block w-full text-sm text-gray-700"
        />
        {photoPreviews.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {photoPreviews.map((src, i) => (
              <div key={src} className="relative">
                <img src={src} alt="" className="h-16 w-16 rounded object-cover" />
                <button
                  type="button"
                  onClick={() => removePhoto(i)}
                  className="absolute -right-1 -top-1 rounded-full bg-gray-800 px-1.5 text-xs text-white"
                >
                  x
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="mb-2 block text-sm font-medium text-purple-700"
      >
        {showAdvanced ? '- Advanced' : '+ Advanced'}
      </button>
      {showAdvanced && <AdvancedRatingFields value={advanced} onChange={setAdvanced} />}

      <button
        type="button"
        onClick={() => setShowDetails((v) => !v)}
        className="mb-2 block text-sm font-medium text-purple-700"
      >
        {showDetails ? '- Bean details' : '+ Bean details'}
      </button>
      {showDetails && (
        <div className="mb-4 grid grid-cols-2 gap-3 rounded-md border border-gray-200 p-3 text-sm">
          <Field label="Origin country" value={details.origin_country} onChange={updateDetail('origin_country')} />
          <Field label="Region" value={details.region} onChange={updateDetail('region')} />
          <Field label="Farm/producer" value={details.farm_producer} onChange={updateDetail('farm_producer')} />
          <Field label="Altitude (m)" type="number" value={details.altitude_m} onChange={updateDetail('altitude_m')} />
          <Field label="Variety" value={details.variety} onChange={updateDetail('variety')} />
          <Field label="Process" value={details.process} onChange={updateDetail('process')} />
          <div>
            <label className="block text-xs text-gray-600">Co-ferment</label>
            <select
              value={details.co_ferment_status}
              onChange={updateDetail('co_ferment_status')}
              className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1"
            >
              <option value="unknown">Unknown</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </div>
          <Field
            label="Co-ferment ingredient"
            value={details.co_ferment_ingredient}
            onChange={updateDetail('co_ferment_ingredient')}
          />
          <Field label="Certifications" value={details.certifications} onChange={updateDetail('certifications')} />
          <Field label="Roast level" value={details.roast_level} onChange={updateDetail('roast_level')} />
          <div className="col-span-2">
            <label className="block text-xs text-gray-600">Printed tasting notes</label>
            <input
              value={details.printed_tasting_notes}
              onChange={updateDetail('printed_tasting_notes')}
              className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1"
            />
          </div>
          <Field label="Roast date" type="date" value={details.roast_date} onChange={updateDetail('roast_date')} />
          <Field label="Bag weight (g)" type="number" value={details.bag_weight_g} onChange={updateDetail('bag_weight_g')} />
          <Field label="Batch number" value={details.batch_number} onChange={updateDetail('batch_number')} />
          <Field label="Roasted in" value={details.roast_location} onChange={updateDetail('roast_location')} />
          <Field label="Price paid" type="number" value={details.price_paid} onChange={updateDetail('price_paid')} />
          <Field label="Currency" value={details.currency} onChange={updateDetail('currency')} />
          <Field label="Entry date" type="date" value={details.entry_date} onChange={updateDetail('entry_date')} />
        </div>
      )}

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-purple-700 px-6 py-3 text-lg font-medium text-white disabled:opacity-50"
      >
        {submitting ? 'Saving...' : 'Save'}
      </button>
    </form>
  )
}
