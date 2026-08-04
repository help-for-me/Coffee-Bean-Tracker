export default function Field({ label, value, onChange, type = 'text' }) {
  return (
    <div>
      <label className="block text-xs text-gray-600">{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1"
      />
    </div>
  )
}
