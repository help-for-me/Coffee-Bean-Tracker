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

// The reverse of ratingPayloadFromAdvanced - starts an edit form from a
// rating the API already returned (snake_case) instead of a blank one.
export function advancedFromRating(rating) {
  return {
    acidityScore: rating.acidity_score ?? '',
    bodyScore: rating.body_score ?? '',
    sweetnessScore: rating.sweetness_score ?? '',
    brewStyle: rating.brew_style ?? '',
    repurchase: rating.repurchase ?? '',
  }
}
