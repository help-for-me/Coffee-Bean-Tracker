export const emptyAdvancedRating = {
  acidityScore: '',
  bodyScore: '',
  sweetnessScore: '',
  brewStyle: '',
  repurchase: '',
}

export function ratingPayloadFromAdvanced(advanced) {
  return {
    acidity_score: advanced.acidityScore ? Number(advanced.acidityScore) : null,
    body_score: advanced.bodyScore ? Number(advanced.bodyScore) : null,
    sweetness_score: advanced.sweetnessScore ? Number(advanced.sweetnessScore) : null,
    brew_style: advanced.brewStyle || null,
    repurchase: advanced.repurchase || null,
  }
}
