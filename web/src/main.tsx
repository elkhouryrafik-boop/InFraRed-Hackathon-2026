import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './components/Hud.css' // global: HUD + overlays + spinner styles
import './components/DrawPanel.css' // draw / "design anywhere" control panel

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
