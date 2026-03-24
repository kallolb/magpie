import { test, expect } from '@playwright/test'

test.describe('Page Screenshots', () => {
  test('Dashboard', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'e2e/screenshots/01-dashboard.png', fullPage: true })
  })

  test('Browse', async ({ page }) => {
    await page.goto('/browse')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'e2e/screenshots/02-browse.png', fullPage: true })
  })

  test('Download', async ({ page }) => {
    await page.goto('/download')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'e2e/screenshots/03-download.png', fullPage: true })
  })

  test('Search - empty', async ({ page }) => {
    await page.goto('/search')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'e2e/screenshots/04-search-empty.png', fullPage: true })
  })

  test('Compilations - list', async ({ page }) => {
    await page.goto('/compilations')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'e2e/screenshots/05-compilations.png', fullPage: true })
  })

  test('Analytics', async ({ page }) => {
    await page.goto('/analytics')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'e2e/screenshots/06-analytics.png', fullPage: true })
  })

  test('Settings', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: 'e2e/screenshots/07-settings.png', fullPage: true })
  })
})

test.describe('Sidebar & Navigation', () => {
  test('Sidebar shows all nav items and logo', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Verify sidebar items
    const sidebar = page.locator('aside')
    await expect(sidebar.getByText('Dashboard')).toBeVisible()
    await expect(sidebar.getByText('Browse')).toBeVisible()
    await expect(sidebar.getByText('Download')).toBeVisible()
    await expect(sidebar.getByText('Search')).toBeVisible()
    await expect(sidebar.getByText('Compilations')).toBeVisible()
    await expect(sidebar.getByText('Analytics')).toBeVisible()
    await expect(sidebar.getByText('Settings')).toBeVisible()

    // Logo (desktop version, the mobile one is hidden at this viewport)
    await expect(sidebar.locator('img[alt="Magpie"]').nth(1)).toBeVisible()

    await page.screenshot({ path: 'e2e/screenshots/08-sidebar.png' })
  })

  test('Active nav item highlights on navigation', async ({ page }) => {
    await page.goto('/analytics')
    await page.waitForLoadState('networkidle')

    // Analytics link should be highlighted
    const analyticsLink = page.locator('aside a[href="/analytics"]')
    await expect(analyticsLink).toHaveClass(/bg-indigo/)

    await page.screenshot({ path: 'e2e/screenshots/09-nav-highlight.png' })
  })
})

test.describe('Search Page', () => {
  test('Scope selector renders three options', async ({ page }) => {
    await page.goto('/search')
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('button', { name: 'All' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Videos' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Compilations' })).toBeVisible()

    await page.screenshot({ path: 'e2e/screenshots/10-search-scope.png' })
  })
})

test.describe('Compilations Page', () => {
  test('Shows empty state with create button', async ({ page }) => {
    await page.goto('/compilations')
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('button', { name: /New Compilation/ })).toBeVisible()

    await page.screenshot({ path: 'e2e/screenshots/11-compilations-empty.png' })
  })

  test('Create compilation flow', async ({ page }) => {
    await page.goto('/compilations')
    await page.waitForLoadState('networkidle')

    // Click new compilation
    await page.getByRole('button', { name: /New Compilation/ }).click()
    await expect(page.getByPlaceholder('Compilation title...')).toBeVisible()

    await page.screenshot({ path: 'e2e/screenshots/12-compilations-create.png' })
  })
})

test.describe('Analytics Page', () => {
  test('Shows summary cards and section headers', async ({ page }) => {
    await page.goto('/analytics')
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('heading', { name: 'Analytics', exact: true })).toBeVisible()
    await expect(page.getByText('Total Storage')).toBeVisible()
    await expect(page.getByText('Total Videos')).toBeVisible()
    await expect(page.getByText('Avg Duration')).toBeVisible()

    // Section headers
    await expect(page.getByText('Storage Analytics')).toBeVisible()
    await expect(page.getByText('Video Collection')).toBeVisible()
    await expect(page.getByText('Content Analytics')).toBeVisible()

    await page.screenshot({ path: 'e2e/screenshots/13-analytics-sections.png', fullPage: true })
  })
})
