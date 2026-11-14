import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  compareRotations,
  generateRotation,
  getCropCalendar,
  getCropProfile,
  getFarmsForRotation,
  getRotationAssessment,
  getRotationEnvironment,
  getRotationExplanation,
  getRotationFarmContext,
  listCropProfiles,
  type CropProfile,
  type CropSummary,
  type RotationAssessment,
  type RotationOption,
} from '../api/rotation'
import { ApiError } from '../api/types'
import { Banner } from '../components/Field'
import { FarmMap } from '../components/FarmMap'
import { formatDate, formatHectares } from '../lib/format'

function displayError(error: unknown): string {
  if (!(error instanceof ApiError)) return 'An unexpected error occurred. Please try again.'
  if (error.status === 401) return 'Your session has expired. Sign in again to continue.'
  if (error.status === 403 || error.status === 404) return 'This resource is unavailable for your account. Check farm access and try again.'
  return error.message
}

function freshnessLabel(status: string | undefined): string {
  if (status === 'STALE') return 'Stale'
  if (status === 'RECENT') return 'Recent'
  if (status === 'FRESH') return 'Fresh'
  return 'Unknown'
}

function MissingList({ items }: { items: Array<{ name: string; reason: string }> }) {
  if (!items.length) return <p className="rotation-muted">No missing inputs were reported.</p>
  return <ul className="rotation-list">{items.map((item, index) => <li key={`${item.name}-${index}`}><strong>{item.name.replace(/_/g, ' ')}</strong><span>{item.reason}</span></li>)}</ul>
}

function TraitValue({ value, unit }: { value: string | boolean | null | undefined; unit?: string | null }) {
  if (value === null || value === undefined || value === '') return <span className="rotation-unknown">Not recorded</span>
  return <>{String(value)}{unit ? ` ${unit}` : ''}</>
}

function CropProfilePanel({ crop, onClose }: { crop: CropProfile; onClose: () => void }) {
  return (
    <div className="rotation-modal-backdrop" role="presentation" onClick={onClose}>
      <section className="rotation-modal" role="dialog" aria-modal="true" aria-labelledby="crop-profile-title" onClick={(event) => event.stopPropagation()}>
        <div className="rotation-section-head"><div><p className="step-kicker">Crop evidence</p><h2 id="crop-profile-title">{crop.name}</h2></div><button className="button button-ghost" onClick={onClose}>Close</button></div>
        <p className="rotation-muted">{[crop.scientific_name, crop.crop_family].filter(Boolean).join(' · ') || 'No scientific name or family recorded'}</p>
        {crop.characteristics.length ? <div className="rotation-traits">{crop.characteristics.map((trait) => <article className="rotation-trait" key={trait.id}>
          <div className="rotation-section-head"><strong>{trait.characteristic_name.replace(/_/g, ' ')}</strong><span className={`rotation-tag ${trait.validation_status === 'VALID' ? 'tag-good' : 'tag-warn'}`}>{trait.validation_status.replace(/_/g, ' ')}</span></div>
          <p><TraitValue value={trait.normalized_value ?? trait.normalized_text ?? trait.normalized_boolean ?? trait.original_value} unit={trait.normalized_unit || trait.original_unit} /></p>
          <p className="rotation-muted">{trait.geographic_applicability.replace(/_/g, ' ')}{trait.geographic_scope ? ` · ${trait.geographic_scope}` : ''}{trait.temporal_applicability ? ` · ${trait.temporal_applicability}` : ''}</p>
          <SourceDetails source={trait.source} recordId={trait.source_record_identifier} recordUrl={trait.source_record_url} evidence={trait.evidence_reference} />
        </article>)}</div> : <Banner tone="warning" title="No validated traits recorded">This profile does not contain characteristics that can be presented as known.</Banner>}
        {crop.missing_characteristics.length ? <Banner tone="warning" title="Missing characteristics"><ul>{crop.missing_characteristics.map((trait) => <li key={trait}>{trait.replace(/_/g, ' ')} — <span className="rotation-unknown">Not recorded</span></li>)}</ul></Banner> : null}
      </section>
    </div>
  )
}

function SourceDetails({ source, recordId, recordUrl, evidence }: {
  source: { dataset_identifier?: string; publisher?: string; dataset_version?: string | null; license?: string | null; attribution?: string | null; landing_page_url?: string | null }
  recordId?: string
  recordUrl?: string | null
  evidence?: string | null
}) {
  return <details className="rotation-source"><summary>Source and evidence</summary><dl className="rotation-definition-list">
    <div><dt>Dataset</dt><dd>{source.dataset_identifier || 'Not specified'}{source.dataset_version ? ` · ${source.dataset_version}` : ''}</dd></div>
    <div><dt>Publisher</dt><dd>{source.publisher || 'Not specified'}</dd></div>
    <div><dt>Record</dt><dd>{recordUrl ? <a href={recordUrl} target="_blank" rel="noreferrer">{recordId || recordUrl}</a> : recordId || 'Not supplied'}</dd></div>
    <div><dt>Evidence reference</dt><dd>{evidence || 'Not supplied'}</dd></div>
    <div><dt>Licence / attribution</dt><dd>{[source.license, source.attribution].filter(Boolean).join(' · ') || 'Not specified'}</dd></div>
    {source.landing_page_url ? <div><dt>Dataset page</dt><dd><a href={source.landing_page_url} target="_blank" rel="noreferrer">Open source</a></dd></div> : null}
  </dl></details>
}

function OptionCard({ option, selected, onSelect, onExplain }: {
  option: RotationOption
  selected: boolean
  onSelect: () => void
  onExplain: () => void
}) {
  return <article className={`rotation-option${selected ? ' rotation-option-selected' : ''}`}>
    <div className="rotation-option-header"><div><p className="step-kicker">{option.strategy_type === 'BASELINE' ? 'History comparison' : 'Evidence-feasible sequence'}</p><h3>{option.strategy_type === 'BASELINE' ? 'Your recorded history' : option.option_id}</h3></div><span className="rotation-tag tag-neutral">Not ranked</span></div>
    <p className="rotation-option-reason">{option.why_suggested}</p>
    <ol className="rotation-season-list">{option.seasons.map((season, index) => <li key={`${season.season_code}-${index}`}>
      <span className="season-index">{String(index + 1).padStart(2, '0')}</span>
      <span className="season-main"><strong>{season.crop_name || season.crop_code || 'Crop not identified'}</strong><small>{season.season_code || 'Season not recorded'}{season.start_date ? ` · ${formatDate(season.start_date)}` : ''}{season.end_date ? ` – ${formatDate(season.end_date)}` : ''}</small></span>
      {season.source ? <span className="rotation-tag tag-neutral">{season.source.replace(/_/g, ' ')}</span> : null}
    </li>)}</ol>
    {option.score !== null ? <p className="rotation-muted">Score: {option.score}</p> : null}
    {option.data_gaps.length ? <div className="rotation-inline-gap"><strong>Data gaps</strong><ul>{option.data_gaps.map((gap, index) => <li key={index}>{gap}</li>)}</ul></div> : null}
    <div className="rotation-option-actions"><button type="button" className="button button-primary" onClick={onExplain}>Read explanation</button><button type="button" className="button button-ghost" aria-pressed={selected} onClick={onSelect}>{selected ? 'Selected for comparison' : 'Select to compare'}</button></div>
  </article>
}

export function RotationExplorerPage() {
  const [farmId, setFarmId] = useState<number | null>(null)
  const [planningSeasons, setPlanningSeasons] = useState(4)
  const [assessments, setAssessments] = useState<RotationAssessment[]>([])
  const [selectedOption, setSelectedOption] = useState<RotationOption | null>(null)
  const [selectedOptions, setSelectedOptions] = useState<RotationOption[]>([])
  const [selectedAssessmentIds, setSelectedAssessmentIds] = useState<string[]>([])
  const [lookupId, setLookupId] = useState('')
  const [showProfile, setShowProfile] = useState<CropProfile | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const latestAssessment = assessments[0]

  const farmsQuery = useQuery({ queryKey: ['farms'], queryFn: getFarmsForRotation })
  const selectedFarm = farmsQuery.data?.results.find((farm) => farm.id === farmId) ?? null
  const contextQuery = useQuery({ queryKey: ['farm', farmId, 'context'], queryFn: () => getRotationFarmContext(farmId as number), enabled: farmId !== null })
  const environmentQuery = useQuery({ queryKey: ['farm', farmId, 'environment', 'current'], queryFn: () => getRotationEnvironment(farmId as number), enabled: farmId !== null })
  const catalogQuery = useQuery({ queryKey: ['crop-catalog', selectedFarm?.region_code], queryFn: () => listCropProfiles(selectedFarm?.region_code ?? ''), enabled: Boolean(selectedFarm?.region_code) })
  const calendarQuery = useQuery({ queryKey: ['crop-calendar', selectedFarm?.region_code], queryFn: () => getCropCalendar(selectedFarm?.region_code ?? ''), enabled: Boolean(selectedFarm?.region_code) })

  const generateMutation = useMutation({
    mutationFn: () => {
      const priorities = contextQuery.data?.priorities ?? {}
      const priorityWeights = Object.keys(priorities).length ? priorities : undefined
      return generateRotation(farmId as number, {
        region_code: selectedFarm?.region_code || undefined,
        planning_seasons: planningSeasons,
        ...(priorityWeights ? { priority_weights: priorityWeights } : {}),
      })
    },
    onSuccess: (assessment) => {
      setAssessments((previous) => [assessment, ...previous.filter((item) => item.recommendation_id !== assessment.recommendation_id)])
      setSelectedOption(null)
      setSelectedOptions([])
      setSelectedAssessmentIds((previous) => previous.includes(assessment.recommendation_id) ? previous : [assessment.recommendation_id, ...previous].slice(0, 2))
    },
  })
  const comparisonMutation = useMutation({ mutationFn: ([first, second]: [string, string]) => compareRotations(first, second) })
  const retrieveMutation = useMutation({
    mutationFn: () => getRotationAssessment(lookupId.trim()),
    onSuccess: (assessment) => {
      setAssessments((previous) => [assessment, ...previous.filter((item) => item.recommendation_id !== assessment.recommendation_id)])
      setSelectedAssessmentIds((previous) => [assessment.recommendation_id, ...previous].slice(0, 2))
    },
  })
  const explanationQuery = useQuery({ queryKey: ['rotation-explanation', latestAssessment?.recommendation_id], queryFn: () => getRotationExplanation(latestAssessment?.recommendation_id ?? ''), enabled: Boolean(selectedOption && latestAssessment), retry: false })
  const comparisonAssessments = useMemo(() => assessments.filter((item) => selectedAssessmentIds.includes(item.recommendation_id)), [assessments, selectedAssessmentIds])

  async function openCropProfile(crop: CropSummary) {
    setProfileError(null)
    try {
      const profile = await getCropProfile(crop.id)
      setShowProfile(profile)
    } catch (error) {
      setProfileError(displayError(error))
    }
  }

  function toggleAssessment(id: string) {
    setSelectedAssessmentIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id].slice(-2))
  }

  if (farmsQuery.isPending) return <div className="page"><p className="page-loading" role="status">Loading your farms…</p></div>
  if (farmsQuery.isError) return <div className="page"><Banner tone="error" title="Could not load farms">{displayError(farmsQuery.error)} <button className="link-button" onClick={() => void farmsQuery.refetch()}>Try again</button></Banner></div>
  if (!farmsQuery.data.results.length) return <div className="page"><header className="page-header"><div><p className="step-kicker">Rotation workspace</p><h1 className="page-title">Plan with evidence</h1></div></header><section className="rotation-empty"><span className="rotation-icon" aria-hidden="true">↗</span><h2>Start with a farm</h2><p>Rotation assessments use your actual farm, recorded crop history, and approved crop evidence.</p><Link className="button button-primary" to="/onboarding">Add a farm</Link></section></div>

  const context = contextQuery.data
  const catalog = catalogQuery.data?.results ?? []

  return <div className="page rotation-workspace">
    <header className="rotation-hero">
      <div><p className="step-kicker">Overfield · decision support</p><h1 className="page-title">Crop rotation explorer</h1><p className="page-lead">Explore what your current farm data can support. Options are evidence-led, not guarantees or a substitute for an agronomist.</p></div>
      <div className="rotation-hero-note"><span aria-hidden="true">✳</span><div><strong>Evidence before advice</strong><small>Unknown stays unknown. No invented scores or crop traits.</small></div></div>
    </header>

    <section className="rotation-controls" aria-label="Rotation planning inputs">
      <label className="field" htmlFor="rotation-farm"><span className="field-label">Farm</span><select id="rotation-farm" className="input" value={farmId ?? ''} onChange={(event) => { setFarmId(event.target.value ? Number(event.target.value) : null); setAssessments([]); setSelectedOption(null); setSelectedOptions([]); setSelectedAssessmentIds([]) }}><option value="">Choose a farm</option>{farmsQuery.data.results.map((farm) => <option key={farm.id} value={farm.id}>{farm.name} · {farm.region_code || 'No region'}</option>)}</select></label>
      <label className="field" htmlFor="planning-seasons"><span className="field-label">Planning horizon</span><select id="planning-seasons" className="input" value={planningSeasons} onChange={(event) => setPlanningSeasons(Number(event.target.value))}>{[2, 3, 4, 5, 6, 8, 10, 12].map((count) => <option key={count} value={count}>{count} seasons</option>)}</select></label>
      <button className="button button-primary rotation-generate" disabled={!selectedFarm || generateMutation.isPending} onClick={() => generateMutation.mutate()}>{generateMutation.isPending ? 'Assessing evidence…' : 'Explore rotation options'}</button>
    </section>

    {!farmId ? <Banner tone="info" title="Choose a farm to begin">Farm details and history will load from your account.</Banner> : null}
    {farmId && !selectedFarm ? <Banner tone="warning" title="Farm unavailable">It is not in the farms returned for your account. Select a farm you own.</Banner> : null}
    {generateMutation.isError ? <Banner tone="error" title="Could not generate assessment">{displayError(generateMutation.error)} <button className="link-button" onClick={() => generateMutation.mutate()}>Try again</button></Banner> : null}

    {selectedFarm ? <>
      <div className="rotation-context-grid">
        <section className="rotation-panel rotation-farm-panel">
          <div className="rotation-section-head"><div><p className="step-kicker">01 · Farm context</p><h2>{selectedFarm.name}</h2></div><span className={`rotation-tag ${selectedFarm.spatial_precision === 'HIGH' ? 'tag-good' : 'tag-warn'}`}>{selectedFarm.spatial_precision === 'HIGH' ? 'Boundary mapped' : 'Point location'}</span></div>
          <p className="rotation-muted">{[selectedFarm.region_code, selectedFarm.country_code].filter(Boolean).join(' · ') || 'Region not set'} · {formatHectares(selectedFarm.area_hectares)}</p>
          <FarmMap mode="readonly" boundary={selectedFarm.boundary} marker={selectedFarm.location} zoom={12} className="rotation-map" />
          <Link className="link-button" to={`/farms/${selectedFarm.id}`}>View farm details</Link>
        </section>
        <section className="rotation-panel">
          <div><p className="step-kicker">02 · Crop history</p><h2>What has been recorded</h2></div>
          {contextQuery.isPending ? <p className="page-loading">Loading crop history…</p> : null}
          {contextQuery.isError ? <Banner tone="warning" title="History unavailable">{displayError(contextQuery.error)} <button className="link-button" onClick={() => void contextQuery.refetch()}>Retry</button></Banner> : null}
          {context ? context.current_crops.length ? <ol className="rotation-history">{context.current_crops.map((entry, index) => <li key={entry.id ?? `${entry.season}-${index}`}><span className="season-index">{String(index + 1).padStart(2, '0')}</span><span><strong>{entry.crop}</strong><small>{entry.season}</small></span><span className="rotation-tag tag-neutral">{entry.source?.replace(/_/g, ' ') || 'Source unknown'}</span></li>)}</ol> : <div className="rotation-subtle-empty"><strong>No crop history recorded</strong><p>History is optional, but without it a historical baseline cannot be established.</p></div> : null}
          {context ? <div className="rotation-farmer-context"><strong>Farmer-reported context</strong><p>Soil: {context.texture_class || 'Not provided'} · sample {context.sample_date ? formatDate(context.sample_date) : 'date unknown'}</p><p>Irrigation: {context.irrigation_available === null ? 'Not provided' : context.irrigation_available ? 'Reported available' : 'Reported unavailable'} · priorities: {Object.keys(context.priorities ?? {}).length ? Object.keys(context.priorities).join(', ').replace(/_/g, ' ') : 'not recorded'}</p></div> : null}
        </section>
      </div>

      <div className="rotation-context-grid">
        <section className="rotation-panel">
          <div className="rotation-section-head"><div><p className="step-kicker">03 · Crop knowledge</p><h2>Available crop catalogue</h2></div><span className="rotation-count">{catalogQuery.isSuccess ? catalogQuery.data.count : '—'} profiles</span></div>
          {!selectedFarm.region_code ? <Banner tone="warning" title="Farm region not configured">A region code is required to request crop profiles.</Banner> : null}
          {catalogQuery.isPending && selectedFarm.region_code ? <p className="page-loading">Checking regional crop evidence…</p> : null}
          {catalogQuery.isError ? <Banner tone="warning" title={catalogQuery.error instanceof ApiError && catalogQuery.error.status === 404 ? 'No crop catalogue for this region' : 'Crop catalogue unavailable'}>{displayError(catalogQuery.error)}</Banner> : null}
          {catalogQuery.isSuccess && catalog.length === 0 ? <div className="rotation-subtle-empty"><strong>No eligible crop profiles available</strong><p>No approved, region-eligible crop evidence was returned. The explorer will not invent crop traits or use unsupported regional data.</p></div> : null}
          {profileError ? <Banner tone="error" title="Could not open crop profile">{profileError}</Banner> : null}
          {catalog.length ? <ul className="rotation-crop-list">{catalog.map((crop) => <li key={crop.id}><div><strong>{crop.name}</strong><small>{[crop.scientific_name, crop.crop_family].filter(Boolean).join(' · ') || crop.code}</small><span className="rotation-tag tag-neutral">{crop.source_status.replace(/_/g, ' ')}</span></div><button className="button button-ghost" onClick={() => void openCropProfile(crop)}>View evidence</button></li>)}</ul> : null}
          {calendarQuery.isPending ? <p className="rotation-muted">Checking for an approved crop calendar…</p> : null}
          {calendarQuery.isError ? <p className="rotation-muted">Calendar unavailable: {calendarQuery.error instanceof ApiError && calendarQuery.error.status === 404 ? 'No approved calendar is configured for this region.' : displayError(calendarQuery.error)}</p> : null}
          {calendarQuery.data ? <div className="rotation-calendar"><strong>Calendar · {calendarQuery.data.calendar_version}</strong><small>{calendarQuery.data.seasons.map((season) => season.label).join(' · ') || 'No seasons defined'}</small>{calendarQuery.data.source.url ? <a href={calendarQuery.data.source.url} target="_blank" rel="noreferrer">Calendar source</a> : null}</div> : null}
        </section>

        <section className="rotation-panel">
          <div><p className="step-kicker">04 · Environmental context</p><h2>Conditions on record</h2></div>
          {environmentQuery.isPending ? <p className="page-loading">Loading environmental summary…</p> : null}
          {environmentQuery.isError ? <Banner tone="warning" title="Environmental data unavailable">{displayError(environmentQuery.error)} <button className="link-button" onClick={() => void environmentQuery.refetch()}>Retry</button></Banner> : null}
          {environmentQuery.data ? <>
            <div className="rotation-environment-meta"><span className={`rotation-tag ${environmentQuery.data.window.freshness === 'STALE' ? 'tag-warn' : 'tag-good'}`}>{freshnessLabel(environmentQuery.data.window.freshness)}</span><span>{environmentQuery.data.window.latest_observation ? `Latest observation ${formatDate(environmentQuery.data.window.latest_observation)}` : 'No observations recorded'}</span></div>
            <div className="rotation-indicators">{Object.values(environmentQuery.data.indicators).map((indicator) => <article key={indicator.code}><div className="rotation-section-head"><strong>{indicator.code}</strong><span className="rotation-tag tag-neutral">{indicator.status.replace(/_/g, ' ')}</span></div><p>{indicator.summary}</p>{indicator.sources.map((source) => <small key={`${source.provider}-${source.parameter}`}>{source.provider} · {source.product} · {source.parameter} · {source.units}</small>)}</article>)}</div>
            <p className="rotation-muted">Environmental observations are contextual evidence only; they are not field measurements or crop-suitability scores.</p>
          </> : null}
        </section>
      </div>

      <section className="rotation-results" aria-live="polite">
        <div className="rotation-results-heading"><div><p className="step-kicker">05 · Explore options</p><h2>Rotation assessment</h2><p className="rotation-muted">The backend evaluates the evidence available for this farm. Missing evidence stays visible.</p></div>{latestAssessment ? <span className={`rotation-tag ${latestAssessment.status === 'OPTIONS_AVAILABLE' ? 'tag-good' : 'tag-warn'}`}>{latestAssessment.status.replace(/_/g, ' ')}</span> : null}</div>
        {!latestAssessment && !generateMutation.isPending ? <div className="rotation-subtle-empty"><strong>Ready when you are</strong><p>Select a planning horizon and request an assessment. No recommendation is generated until you ask.</p></div> : null}
        {generateMutation.isPending ? <div className="rotation-loading" role="status"><span className="rotation-spinner" />Assessing approved crop evidence and farm history…</div> : null}
        {latestAssessment ? <>
          {latestAssessment.status === 'INSUFFICIENT_EVIDENCE' ? <Banner tone="warning" title="There is not enough evidence to recommend a rotation">This result is not a failed request. It is an explicit assessment of what is missing; no unsupported alternative is shown.</Banner> : null}
          <div className="rotation-result-meta"><span>Engine {latestAssessment.engine_version}</span><span>{latestAssessment.planning_horizon.season_count} seasons</span><span>Generated {formatDate(latestAssessment.generated_at)}</span><span>Score: not assessed</span></div>
          {latestAssessment.options.length ? <div className="rotation-options">{latestAssessment.options.map((option) => <OptionCard key={option.option_id} option={option} selected={selectedOptions.some((item) => item.option_id === option.option_id)} onSelect={() => setSelectedOptions((current) => current.some((item) => item.option_id === option.option_id) ? current.filter((item) => item.option_id !== option.option_id) : [...current, option].slice(-2))} onExplain={() => setSelectedOption(option)} />)}</div> : <div className="rotation-subtle-empty"><strong>No feasible rotation options returned</strong><p>The backend returned an empty option set. Review the missing evidence below; the interface will not invent a sequence.</p></div>}
          {selectedOptions.length > 0 ? <section className="rotation-panel rotation-option-comparison"><div className="rotation-section-head"><div><p className="step-kicker">Compare options</p><h3>Side-by-side evidence comparison</h3></div><button className="button button-ghost" onClick={() => setSelectedOptions([])}>Clear selection</button></div><p className="rotation-muted">This comparison summarizes the backend-provided options. It does not rank them or declare a winner.</p><div className="rotation-option-compare-grid">{selectedOptions.map((option) => <article key={option.option_id}><h4>{option.strategy_type === 'BASELINE' ? 'History comparison' : option.option_id}</h4><p>{option.why_suggested}</p><ol>{option.seasons.map((season, index) => <li key={`${season.season_code}-${index}`}><strong>{season.crop_name || season.crop_code || 'Crop unknown'}</strong><small>{season.season_code || 'Season unknown'}{season.start_date ? ` · ${formatDate(season.start_date)}` : ''}</small></li>)}</ol><p><strong>Score:</strong> {option.score === null ? 'Not assessed' : option.score}</p><p><strong>Evidence:</strong> {option.evidence.length ? option.evidence.join(', ') : 'Not provided'}</p><p><strong>Traits considered:</strong> {option.traits_considered.length || 'None'}</p><p><strong>Data gaps:</strong> {option.data_gaps.length ? option.data_gaps.join('; ') : 'None reported'}</p></article>)}</div></section> : null}
          <div className="rotation-evidence-grid">
            <section className="rotation-panel"><h3>Missing and incomplete information</h3><MissingList items={latestAssessment.missing} /></section>
            <section className="rotation-panel"><h3>Rejected alternatives and constraints</h3>{latestAssessment.rejected_alternatives.length ? <ul className="rotation-list">{latestAssessment.rejected_alternatives.map((item, index) => <li key={`${item.candidate ?? item.constraint}-${index}`}><strong>{item.candidate ?? item.constraint ?? 'Constraint'}</strong><span>{item.reason}</span></li>)}</ul> : <p className="rotation-muted">No alternatives were rejected by this assessment.</p>}{latestAssessment.constraints.length ? <details className="rotation-source"><summary>Applied constraints ({latestAssessment.constraints.length})</summary><pre>{JSON.stringify(latestAssessment.constraints, null, 2)}</pre></details> : null}</section>
          </div>
          <section className="rotation-panel"><h3>Limitations</h3><ul className="rotation-list">{latestAssessment.data_limitations.map((limitation, index) => <li key={index}><span>{limitation}</span></li>)}</ul><details className="rotation-source"><summary>Reproducibility details</summary><p>Input fingerprint: <code>{latestAssessment.input_sha256}</code></p><p>Method: {latestAssessment.methodology?.id ?? 'Not specified'} · {latestAssessment.methodology?.version ?? latestAssessment.engine_version}</p><p>Completeness: {latestAssessment.data_completeness.status} — {latestAssessment.data_completeness.reason}</p></details></section>
          {selectedOption ? <section className="rotation-panel rotation-explanation" aria-labelledby="rotation-explanation-title"><div className="rotation-section-head"><div><p className="step-kicker">06 · Explanation</p><h3 id="rotation-explanation-title">Why this option is shown</h3></div><button className="button button-ghost" onClick={() => setSelectedOption(null)}>Close</button></div><p>{selectedOption.why_suggested}</p>{explanationQuery.isError ? <Banner tone="warning" title="Full explanation endpoint unavailable">{displayError(explanationQuery.error)} The explanation below is from the generated assessment.</Banner> : null}{explanationQuery.isSuccess ? <p className="rotation-muted">{explanationQuery.data.explanation.why_presented}</p> : null}{explanationQuery.isLoading ? <p className="rotation-muted" role="status">Loading explanation provenance…</p> : null}{selectedOption.traits_considered.length ? <><h4>Traits considered</h4><ul className="rotation-traits-list">{selectedOption.traits_considered.map((trait, index) => <li key={`${trait.id}-${index}`}><strong>{trait.characteristic_name.replace(/_/g, ' ')}</strong>: <TraitValue value={trait.normalized_value ?? trait.normalized_text ?? trait.normalized_boolean ?? trait.original_value} unit={trait.normalized_unit || trait.original_unit} /><small>{trait.source.dataset_identifier} · {trait.geographic_applicability.replace(/_/g, ' ')}</small></li>)}</ul></> : <p className="rotation-muted">No crop traits were used to support this option.</p>}{selectedOption.evidence.length ? <p><strong>Evidence identifiers:</strong> {selectedOption.evidence.join(', ')}</p> : <Banner tone="warning" title="No evidence identifiers attached">This option has no evidence reference to show.</Banner>}{selectedOption.constraints_not_evaluated.length ? <><h4>Constraints not evaluated</h4><pre>{JSON.stringify(selectedOption.constraints_not_evaluated, null, 2)}</pre></> : null}{selectedOption.confidence ? <p><strong>Confidence:</strong> {selectedOption.confidence.status} {selectedOption.confidence.reason ? `— ${selectedOption.confidence.reason}` : ''}</p> : null}</section> : null}
          <section className="rotation-panel"><div className="rotation-section-head"><div><p className="step-kicker">Compare assessments</p><h3>Compare saved results</h3></div><span className="rotation-count">{assessments.length} loaded</span></div><form className="rotation-retrieve-form" onSubmit={(event) => { event.preventDefault(); retrieveMutation.mutate() }}><label className="field" htmlFor="rotation-result-id"><span className="field-label">Retrieve an existing assessment</span><input id="rotation-result-id" className="input" value={lookupId} onChange={(event) => setLookupId(event.target.value)} placeholder="Recommendation UUID" /></label><button className="button button-ghost" disabled={!lookupId.trim() || retrieveMutation.isPending}>Retrieve</button></form>{retrieveMutation.isError ? <Banner tone="error" title="Could not retrieve assessment">{displayError(retrieveMutation.error)}</Banner> : null}{assessments.length > 1 ? <><div className="rotation-saved-assessments">{assessments.map((assessment) => <label key={assessment.recommendation_id}><input type="checkbox" checked={selectedAssessmentIds.includes(assessment.recommendation_id)} onChange={() => toggleAssessment(assessment.recommendation_id)} />{assessment.status.replace(/_/g, ' ')} · {formatDate(assessment.generated_at)} · {assessment.recommendation_id.slice(0, 8)}</label>)}</div><button className="button button-ghost" disabled={selectedAssessmentIds.length !== 2 || comparisonMutation.isPending} onClick={() => comparisonMutation.mutate(selectedAssessmentIds as [string, string])}>Compare selected assessments</button></> : <p className="rotation-muted">Generate another assessment to compare stored evidence snapshots. Comparisons report evidence differences, not a best option.</p>}{comparisonMutation.isError ? <Banner tone="error" title="Comparison failed">{displayError(comparisonMutation.error)}</Banner> : null}{comparisonMutation.data ? <div className="rotation-comparison"><strong>{comparisonMutation.data.same_input ? 'Same input evidence' : 'Different input evidence'}</strong><p>{comparisonMutation.data.comparison_method}</p>{comparisonAssessments.map((assessment) => <p key={assessment.recommendation_id}>{assessment.recommendation_id.slice(0, 8)} · {assessment.status} · {assessment.options.length} option(s) · {assessment.missing.length} missing item(s)</p>)}</div> : null}</section>
        </> : null}
      </section>
      {showProfile ? <CropProfilePanel crop={showProfile} onClose={() => setShowProfile(null)} /> : null}
    </> : null}
  </div>
}
