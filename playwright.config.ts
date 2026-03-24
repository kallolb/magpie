import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/screenshots',
  use: {
    baseURL: 'http://localhost:3000',
    screenshot: 'on',
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
})
