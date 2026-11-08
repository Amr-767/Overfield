import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="page">
      <section className="empty-state">
        <h3>Page not found</h3>
        <p>That page does not exist.</p>
        <Link to="/" className="button button-primary">
          Back to home
        </Link>
      </section>
    </div>
  )
}
