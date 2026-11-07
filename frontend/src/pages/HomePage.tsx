import { BackendStatus } from '../components/BackendStatus'

export function HomePage() {
  return (
    <div className="home">
      <section className="home-intro">
        <h2 className="home-title">AgroSpace Quest</h2>
        <p className="home-lead">
          Explainable crop-rotation decision support powered by NASA Earth data.
          This page verifies that the React frontend can reach the Django API.
        </p>
      </section>
      <BackendStatus />
    </div>
  )
}
