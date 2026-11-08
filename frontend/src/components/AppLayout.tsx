import { Outlet } from 'react-router-dom'

import { Layout } from './Layout'

export function AppLayout() {
  return (
    <Layout wide>
      <Outlet />
    </Layout>
  )
}
