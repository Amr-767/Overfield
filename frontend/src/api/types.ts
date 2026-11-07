/** Response shape for GET /api/v1/health/ (Phase 1B contract). */
export interface HealthResponse {
  status: string
  database: string
  timestamp: string
  /** Optional; omitted until a later readiness field is added. */
  postgis?: string
}

export class ApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}
