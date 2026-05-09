import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import './globals.css'
import App from './App'
import { useSettings } from './store/settings'
import { applyTheme, watchSystemTheme } from './theme'

function Bootstrap() {
  const theme = useSettings((s) => s.theme)
  const load = useSettings((s) => s.load)

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    applyTheme(theme)
    return watchSystemTheme(theme)
  }, [theme])

  return <App />
}

const root = document.getElementById('root')!
createRoot(root).render(
  <StrictMode>
    <Bootstrap />
  </StrictMode>
)
