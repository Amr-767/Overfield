import type { Farm } from '../api/types'

const numberFormat = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
})

export function formatHectares(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '—'
  return `${numberFormat.format(numeric)} ha`
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export function areaSourceLabel(source: Farm['area_source']): string {
  return source === 'GEOMETRY_DERIVED'
    ? 'Calculated from your boundary'
    : 'Reported by you (not GIS-calculated)'
}

export function precisionLabel(precision: Farm['spatial_precision']): string {
  return precision === 'HIGH' ? 'High — drawn boundary' : 'Low — point only'
}
