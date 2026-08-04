// A provisional profile (roaster "Unidentified") is a placeholder for a
// bag entry submitted with only a photo, waiting on extraction to resolve
// a real identity - never show the raw placeholder name to the user.
export function beanProfileDisplayName({ roaster, bean_name: beanName, is_provisional: isProvisional }, extractionStatus) {
  if (!isProvisional) {
    return `${roaster} — ${beanName}`
  }
  if (extractionStatus === 'pending') {
    return 'Identifying from photo…'
  }
  return 'Not identified — needs a manual name'
}
