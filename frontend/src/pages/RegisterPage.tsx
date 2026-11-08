import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError } from '../api/types'
import { useAuth } from '../auth/auth-context'
import { Banner } from '../components/Field'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    username: '',
    email: '',
    displayName: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  const update = (patch: Partial<typeof form>) => setForm({ ...form, ...patch })

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setFieldErrors({})

    const issues: Record<string, string> = {}
    if (!form.username.trim()) issues.username = 'Choose a username.'
    if (form.password.length < 8) issues.password = 'Use at least 8 characters.'
    if (form.password !== form.confirmPassword) issues.confirmPassword = 'Passwords do not match.'
    if (Object.keys(issues).length > 0) {
      setFieldErrors(issues)
      return
    }

    setSubmitting(true)
    try {
      await register({
        username: form.username.trim(),
        password: form.password,
        email: form.email.trim(),
        display_name: form.displayName.trim(),
      })
      navigate('/onboarding', { replace: true })
    } catch (caught) {
      if (caught instanceof ApiError) {
        setFieldErrors(caught.fieldMessages)
        setError(caught.message)
      } else {
        setError('Registration failed. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-layout">
      <section className="auth-card">
        <header className="step-header">
          <p className="step-kicker">Get started</p>
          <h2>Create your farmer account</h2>
          <p className="step-lead">
            Your farm boundaries and soil information stay private to your account.
          </p>
        </header>

        {error ? <Banner tone="error">{error}</Banner> : null}

        <form onSubmit={handleSubmit} className="form-stack" noValidate>
          <div className={`field${fieldErrors.username ? ' field-invalid' : ''}`}>
            <label className="field-label" htmlFor="register-username">
              Username
            </label>
            <input
              id="register-username"
              className="input"
              autoComplete="username"
              value={form.username}
              onChange={(event) => update({ username: event.target.value })}
            />
            {fieldErrors.username ? <p className="field-error">{fieldErrors.username}</p> : null}
          </div>

          <div className="field">
            <label className="field-label" htmlFor="register-name">
              Your name <span className="field-optional">optional</span>
            </label>
            <input
              id="register-name"
              className="input"
              autoComplete="name"
              value={form.displayName}
              onChange={(event) => update({ displayName: event.target.value })}
            />
          </div>

          <div className={`field${fieldErrors.email ? ' field-invalid' : ''}`}>
            <label className="field-label" htmlFor="register-email">
              Email <span className="field-optional">optional</span>
            </label>
            <input
              id="register-email"
              className="input"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={(event) => update({ email: event.target.value })}
            />
            {fieldErrors.email ? <p className="field-error">{fieldErrors.email}</p> : null}
          </div>

          <div className={`field${fieldErrors.password ? ' field-invalid' : ''}`}>
            <label className="field-label" htmlFor="register-password">
              Password
            </label>
            <input
              id="register-password"
              className="input"
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={(event) => update({ password: event.target.value })}
            />
            {fieldErrors.password ? <p className="field-error">{fieldErrors.password}</p> : null}
          </div>

          <div className={`field${fieldErrors.confirmPassword ? ' field-invalid' : ''}`}>
            <label className="field-label" htmlFor="register-confirm">
              Confirm password
            </label>
            <input
              id="register-confirm"
              className="input"
              type="password"
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={(event) => update({ confirmPassword: event.target.value })}
            />
            {fieldErrors.confirmPassword ? (
              <p className="field-error">{fieldErrors.confirmPassword}</p>
            ) : null}
          </div>

          <button type="submit" className="button button-primary button-large" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-switch">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </div>
  )
}
