import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import {
  getDataJob,
  jobIdFromError,
  requestScan,
  type DataJob,
  type ScanJobStatus,
} from '../../api/environment'
import { ApiError } from '../../api/types'
import { Banner } from '../Field'

const POLL_INTERVAL_MS = 2500

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Your session has expired. Sign in again to continue.'
    if (error.status === 404) {
      return 'This farm does not exist or belongs to another account.'
    }
    if (error.status === 503) {
      return 'The background worker is unavailable, so the scan was not queued. Nothing new was retrieved.'
    }
    return error.message
  }
  return 'An unexpected error occurred while requesting the scan.'
}

function jobLabel(status: ScanJobStatus): string {
  switch (status) {
    case 'PENDING':
      return 'Queued'
    case 'RUNNING':
      return 'Running'
    case 'SUCCEEDED':
      return 'Succeeded'
    case 'PARTIALLY_SUCCEEDED':
      return 'Partially succeeded'
    case 'FAILED':
      return 'Failed'
  }
}

function jobTone(status: ScanJobStatus): 'good' | 'warn' | 'bad' | 'neutral' {
  if (status === 'SUCCEEDED') return 'good'
  if (status === 'PARTIALLY_SUCCEEDED') return 'warn'
  if (status === 'FAILED') return 'bad'
  return 'neutral'
}

function isActive(status: ScanJobStatus | undefined): boolean {
  return status === 'PENDING' || status === 'RUNNING'
}

interface ScanNotice {
  tone: 'info' | 'warning' | 'success'
  title: string
  body: string
}

function JobDetails({ job }: { job: DataJob }) {
  return (
    <div className="env-job" role="status" aria-live="polite">
      <div className="env-job-head">
        <strong>
          {isActive(job.status) ? <span className="env-spinner" aria-hidden="true" /> : null}
          Scan {jobLabel(job.status).toLowerCase()}
        </strong>
        <span className={`env-tag env-tag-${jobTone(job.status)}`}>
          {jobLabel(job.status)}
        </span>
      </div>

      <dl className="env-job-meta">
        <div>
          <dt>Requested range</dt>
          <dd>
            {job.requested_start} → {job.requested_end}
          </dd>
        </div>
        <div>
          <dt>Days requested</dt>
          <dd>{job.days_requested}</dd>
        </div>
        <div>
          <dt>Days stored</dt>
          <dd>{job.days_stored === null ? 'Not reported yet' : job.days_stored}</dd>
        </div>
        <div>
          <dt>Days missing</dt>
          <dd>{job.days_missing === null ? 'Not reported yet' : job.days_missing}</dd>
        </div>
      </dl>

      <p className="env-method">
        Parameters: {job.parameters.length ? job.parameters.join(', ') : 'provider default'}
      </p>

      {job.status === 'FAILED' ? (
        <p className="env-job-error">
          <strong>{job.error_code ? `${job.error_code}: ` : 'Scan failed: '}</strong>
          {job.error_message || 'The provider job did not complete.'}
        </p>
      ) : null}

      {job.status === 'PARTIALLY_SUCCEEDED' ? (
        <p className="env-job-error">
          Some days or parameters were not stored. The dashboard only shows what was actually
          retrieved; missing days stay missing.
        </p>
      ) : null}

      <details className="env-details">
        <summary>Job reference</summary>
        <p className="env-method">
          <code>{job.job_id}</code> · {job.provider.replace(/_/g, ' ')}
        </p>
      </details>
    </div>
  )
}

export function ScanPanel({
  farmId,
  onSummaryRefresh,
}: {
  farmId: number
  onSummaryRefresh: () => void
}) {
  const [jobId, setJobId] = useState<string | null>(null)
  const [force, setForce] = useState(false)
  const [notice, setNotice] = useState<ScanNotice | null>(null)
  const refreshedJobRef = useRef<string | null>(null)

  const scanMutation = useMutation({
    mutationFn: () => requestScan(farmId, force ? { force: true } : {}),
    onSuccess: (response) => {
      setNotice(null)
      if (response.status === 'already_current') {
        setJobId(null)
        setNotice({
          tone: 'info',
          title: 'Stored observations already cover this window',
          body: `${response.detail} No provider request was made.`,
        })
        onSummaryRefresh()
        return
      }
      setJobId(response.job_id)
    },
    onError: (error) => {
      const runningJobId = jobIdFromError(error)
      if (runningJobId) {
        setJobId(runningJobId)
        const status = error instanceof ApiError ? error.status : undefined
        setNotice({
          tone: 'warning',
          title: status === 409 ? 'A scan is already running' : 'The scan did not start',
          body:
            status === 409
              ? 'The request was not queued again. Progress for the existing scan is shown below.'
              : errorText(error),
        })
      } else {
        setNotice(null)
      }
    },
  })

  const jobQuery = useQuery({
    queryKey: ['data-job', jobId],
    queryFn: () => getDataJob(jobId ?? ''),
    enabled: jobId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return isActive(status) ? POLL_INTERVAL_MS : false
    },
  })

  const job = jobQuery.data

  useEffect(() => {
    setJobId(null)
    setNotice(null)
    setForce(false)
    refreshedJobRef.current = null
    scanMutation.reset()
    // Reset the panel when navigating to another farm.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [farmId])

  useEffect(() => {
    if (!job) return
    if (job.status !== 'SUCCEEDED' && job.status !== 'PARTIALLY_SUCCEEDED') return
    if (refreshedJobRef.current === job.job_id) return
    refreshedJobRef.current = job.job_id
    onSummaryRefresh()
  }, [job, onSummaryRefresh])

  const busy = scanMutation.isPending || isActive(job?.status)
  const unresolvedJob = jobId !== null && jobQuery.isError
  const buttonLabel = scanMutation.isPending
    ? 'Requesting scan…'
    : isActive(job?.status)
      ? 'Scan in progress…'
      : 'Request NASA POWER scan'

  return (
    <section className="env-panel env-scan" aria-labelledby="env-scan-title">
      <div className="env-panel-head">
        <div>
          <p className="step-kicker">Observation refresh</p>
          <h2 id="env-scan-title">Request a NASA POWER scan</h2>
        </div>
        <span className="env-tag env-tag-neutral">NASA POWER · MERRA-2</span>
      </div>

      <p className="env-muted">
        Fetches daily grid-cell estimates for this farm&apos;s representative point. A scan does not
        measure the field, and no value is shown until it has been stored and read back from the
        API.
      </p>

      <div className="env-scan-controls">
        <button
          type="button"
          className="button button-primary"
          disabled={busy || unresolvedJob}
          onClick={() => scanMutation.mutate()}
        >
          {buttonLabel}
        </button>

        <label className="env-checkbox" htmlFor="env-scan-force">
          <input
            id="env-scan-force"
            type="checkbox"
            checked={force}
            disabled={busy}
            onChange={(event) => setForce(event.target.checked)}
          />
          Re-fetch days that already have stored observations
        </label>
      </div>

      {scanMutation.isError && !jobIdFromError(scanMutation.error) ? (
        <Banner tone="error" title="Could not request the scan">
          {errorText(scanMutation.error)}{' '}
          <button
            type="button"
            className="link-button"
            disabled={busy}
            onClick={() => scanMutation.mutate()}
          >
            Try again
          </button>
        </Banner>
      ) : null}

      {notice ? (
        <Banner tone={notice.tone} title={notice.title}>
          {notice.body}
        </Banner>
      ) : null}

      {jobQuery.isError ? (
        <Banner tone="warning" title="Could not read the scan status">
          {errorText(jobQuery.error)}{' '}
          <button type="button" className="link-button" onClick={() => void jobQuery.refetch()}>
            Check status again
          </button>
        </Banner>
      ) : null}

      {job ? <JobDetails job={job} /> : null}

      {job?.status === 'SUCCEEDED' ? (
        <p className="env-generated">
          The scan finished. The environmental summary below has been refreshed from stored
          observations.
        </p>
      ) : null}
    </section>
  )
}
