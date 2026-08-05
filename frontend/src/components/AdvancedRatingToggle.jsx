import AdvancedRatingFields from './AdvancedRatingFields'

// Same "+/- Advanced" show/hide button on both the New Entry and Rate a
// Previous Bean forms, wrapping AdvancedRatingFields itself.
export default function AdvancedRatingToggle({ show, onToggle, value, onChange }) {
  return (
    <>
      <button type="button" onClick={onToggle} className="mb-2 block text-sm font-medium text-purple-700">
        {show ? '- Advanced' : '+ Advanced'}
      </button>
      {show && <AdvancedRatingFields value={value} onChange={onChange} />}
    </>
  )
}
