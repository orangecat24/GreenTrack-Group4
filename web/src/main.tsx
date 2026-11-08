import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'

// Unlike Razor, the server sends an HTML shell. React owns just this root and
// updates its DOM after state changes; it does not reload a new page per tab.
createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
)
