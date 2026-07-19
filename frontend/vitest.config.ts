import path from 'node:path'

import { defineConfig } from 'vitest/config'

export default defineConfig({
  // Vitest's built-in oxc transform handles TSX; no babel react plugin needed.
  test: {
    environment: 'jsdom',
    // Globals let Testing Library register its afterEach DOM cleanup.
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
})
