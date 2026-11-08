import type { ReactNode } from 'react'

interface FieldProps {
  id: string
  label: string
  hint?: string
  error?: string
  optional?: boolean
  children: ReactNode
}

export function Field({ id, label, hint, error, optional, children }: FieldProps) {
  return (
    <div className={`field${error ? ' field-invalid' : ''}`}>
      <label className="field-label" htmlFor={id}>
        {label}
        {optional ? <span className="field-optional">optional</span> : null}
      </label>
      {children}
      {hint ? <p className="field-hint">{hint}</p> : null}
      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}

type Tone = 'info' | 'success' | 'error' | 'warning'

interface BannerProps {
  tone?: Tone
  title?: string
  children: ReactNode
}

export function Banner({ tone = 'info', title, children }: BannerProps) {
  return (
    <div className={`banner banner-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      {title ? <p className="banner-title">{title}</p> : null}
      <div className="banner-body">{children}</div>
    </div>
  )
}
