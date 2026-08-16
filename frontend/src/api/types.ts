export type Product = {
  id: number
  name: string
  full_name: string
  brand: string
  category: string
  description: string
  abv: number
  serving_ml: number | null
  alcohol_ml: number | null
  alcohol_grams: number | null
  taste_features: Record<string, number>
  image_url: string | null
  recommendable: boolean
  is_active: boolean
}

export type RecommendationItem = {
  product_id: number
  product_key: string
  name: string
  brand: string
  category: string
  abv: number
  serving_ml: number | null
  alcohol_ml: number | null
  alcohol_grams: number | null
  image_url: string | null
  taste_match_pct: number
  cosine_distance: number
  abv_reduction: number
  abv_reduction_pct: number
  alcohol_ml_reduction: number | null
  alcohol_ml_reduction_pct: number | null
}

export type RecommendationResponse = {
  selected: Product
  recommendations: RecommendationItem[]
  reason: string | null
  message: string | null
}

export type LadderStep = {
  step: number
  label: string
  product_id: number | null
  product_key: string
  name: string
  abv: number
  alcohol_ml: number | null
  taste_match_pct: number | null
}

export type User = {
  id: number
  email: string
  display_name: string
  role: 'user' | 'admin'
  research_consent?: boolean
}

export type Reward = {
  id: number
  name: string
  description: string
  image_url: string | null
  points_cost: number
  stock: number
  active: boolean
}

export type Redemption = {
  id: number
  reward_id: number
  reward_name?: string
  points_spent: number
  redemption_code: string
  status: 'pending' | 'redeemed' | 'cancelled'
  created_at: string
  redeemed_at: string | null
}

export type Badge = {
  id: number
  name: string
  description: string
  icon: string
  earned_at?: string
}

export type ApiError = {
  error: { code: string; message: string; details?: Record<string, unknown> }
}
