import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
  build: {
    target: 'es2020',
    sourcemap: true,
    chunkSizeWarningLimit: 4000, // deck.gl + mapbox + 3d-tiles are large by nature
  },
  // deck.gl / loaders.gl ship a lot of optional deps; pre-bundle the heavy ones.
  optimizeDeps: {
    include: ['mapbox-gl', 'react-map-gl'],
  },
})
