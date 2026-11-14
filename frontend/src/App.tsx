import { Route, Routes } from 'react-router-dom'

import { AppLayout } from './components/AppLayout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { EnvironmentalDashboardPage } from './pages/EnvironmentalDashboardPage'
import { FarmDetailPage } from './pages/FarmDetailPage'
import { FarmsPage } from './pages/FarmsPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { RegisterPage } from './pages/RegisterPage'
import { RotationExplorerPage } from './pages/RotationExplorerPage'
import { SimulationPage } from './pages/SimulationPage'

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="farms" element={<FarmsPage />} />
          <Route path="rotation" element={<RotationExplorerPage />} />
          <Route path="simulations" element={<SimulationPage />} />
          <Route path="farms/:farmId/environment" element={<EnvironmentalDashboardPage />} />
          <Route path="farms/:farmId" element={<FarmDetailPage />} />
          <Route path="onboarding" element={<OnboardingPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App
