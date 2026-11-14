import { apiRequest } from './client'

/** Phase 6 environment-only scenario simulation contract. */

export type ScenarioMode = 'BASELINE' | 'HOT_SCENARIO' | 'DRY_SCENARIO' | 'CUSTOM'
export type SimulationStatus = 'COMPLETED' | 'INSUFFICIENT_EVIDENCE'

export interface SimulationScenario {
  mode: ScenarioMode
  label: string
  temperature_delta_c: string
  rainfall_multiplier: string
  is_hypothetical: boolean
  adjustment_basis: string
  bounds: {
    temperature_delta_c: [string, string]
    rainfall_multiplier: [string, string]
  }
}

export type SimulationMetricValue = string | number | null
export type SimulationMetrics = Record<string, SimulationMetricValue>

export interface SimulationStep {
  checkpoint: string
  label: string
  horizon_months: number
  /** Null until an approved regional calendar can anchor a real date. */
  as_of_date: string | null
  status: SimulationStatus
  metrics: SimulationMetrics
  missing_inputs: string[]
  applied_adjustments: {
    temperature_delta_c: string
    rainfall_multiplier: string
    applied_to: string[]
  }
  assumptions: string[]
  limitations: string[]
}

export interface SimulationParameterAvailability {
  units: string
  available_days: number
  missing_days: number
}

export interface SimulationSource {
  provider: string
  parameter: string
  units: string
  product: string
  data_category: string
  native_resolution_note: string | null
  time_standard: string
  access_date: string | null
}

export interface SimulationBaseline {
  period: {
    start: string | null
    end: string | null
    latest_observation: string | null
    days_expected: number
    freshness: string
  }
  metrics: SimulationMetrics | null
  parameters: Record<string, SimulationParameterAvailability>
  sources: SimulationSource[]
  missing_inputs: string[]
}

export interface SimulationDifference {
  baseline: SimulationMetricValue
  scenario: SimulationMetricValue
  change: SimulationMetricValue
}

export interface SimulationRun {
  simulation_id: string
  farm_id: number
  scenario: SimulationScenario
  engine_version: string
  status: SimulationStatus
  baseline: SimulationBaseline
  differences: Record<string, SimulationDifference>
  comparison: {
    supported: boolean
    method: string
    ranked: boolean
    score: null
  }
  crop_level_outcomes: string
  hypothetical_notice: string
  limitations: string[]
  steps: SimulationStep[]
  input_sha256: string
  created_at: string
}

export interface SimulationList {
  count: number
  results: SimulationRun[]
}

export interface CreateSimulationPayload {
  scenario_mode?: ScenarioMode
  window_days?: number
  temperature_delta_c?: string
  rainfall_multiplier?: string
}

export function createSimulation(
  farmId: number,
  payload: CreateSimulationPayload,
): Promise<SimulationRun> {
  return apiRequest<SimulationRun>(`/api/v1/farms/${farmId}/simulations/`, {
    method: 'POST',
    body: payload,
    auth: true,
  })
}

export function listSimulations(farmId: number): Promise<SimulationList> {
  return apiRequest<SimulationList>(`/api/v1/farms/${farmId}/simulations/`, { auth: true })
}

export function getSimulation(simulationId: string): Promise<SimulationRun> {
  return apiRequest<SimulationRun>(`/api/v1/simulations/${simulationId}/`, { auth: true })
}

export function getSimulationSteps(
  simulationId: string,
): Promise<{ simulation_id: string; engine_version: string; steps: SimulationStep[] }> {
  return apiRequest(`/api/v1/simulations/${simulationId}/steps/`, { auth: true })
}
