import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import Home from './pages/Home'
import LegacyHome from './pages/LegacyHome'
import Procedures from './pages/Procedures'
import Fines from './pages/Fines'
import Directory from './pages/Directory'
import Advisories from './pages/Advisories'
import Chat from './pages/Chat'
import './tokens.css'
import './styles.css'

const router = createBrowserRouter([
  { path: '/', element: <Home /> },
  { path: '/legacy-home', element: <LegacyHome /> },
  { path: '/procedures', element: <Procedures /> },
  { path: '/fines', element: <Fines /> },
  { path: '/directory', element: <Directory /> },
  { path: '/advisories', element: <Advisories /> },
  { path: '/chat', element: <Chat /> },
], {
  future: {
    v7_startTransition: true,
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider theme={{ algorithm: theme.defaultAlgorithm }}>
      <RouterProvider router={router} />
    </ConfigProvider>
  </React.StrictMode>
)

