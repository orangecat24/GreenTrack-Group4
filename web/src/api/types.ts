// These interfaces mirror api/app/models.py. They describe JSON, so Python's
// timezone-aware datetimes arrive as ISO strings rather than JavaScript Dates.
export interface WindowQuery {
  household_id: string
  start: string
  end: string
}

export type Grain = 'hourly' | 'daily'

export interface ConsumptionPoint {
  household_id: string
  timestamp: string
  interval_end: string
  energy_kwh: number
}

export interface AnomalyPoint {
  household_id: string
  timestamp: string
  interval_end: string
  observed_kwh: number
  expected_kwh: number
  score: number
  reason: string
}

export interface ForecastPoint extends ConsumptionPoint {
  forecast_origin: string
  method: 'illustrative_previous_day'
}

export interface ReadResponse<T> {
  household_id: string
  items: T[]
  units: Record<string, string>
  requested_start: string
  requested_end: string
  covered_start: string | null
  covered_end: string | null
  next_cursor: string | null
  is_demo: boolean
  timezone_note: string
}

export interface ConsumptionResponse extends ReadResponse<ConsumptionPoint> {
  grain: Grain
}

export interface ForecastResponse extends ReadResponse<ForecastPoint> {
  forecast_origin: string
  target_start: string
  target_end: string
  note: string
}

export interface ChatRequest extends WindowQuery {
  request_type: 'chat' | 'weekly_summary'
  message?: string
}

export interface ChatResponse {
  household_id: string
  request_type: ChatRequest['request_type']
  requested_start: string
  requested_end: string
  status: 'placeholder'
  answer: string
  citations: { title: string; url: string }[]
  assistant_connected: boolean
  is_demo: boolean
}
