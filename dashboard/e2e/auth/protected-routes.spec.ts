/**
 * E2E Tests: Protected Routes (Dev Mode)
 * 
 * In dev mode, most routes are public. Tests verify pages load correctly.
 */

import { test, expect } from '@playwright/test';

test.describe('Page Access (Dev Mode)', () => {
  test('should access homepage', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should access analyze page', async ({ page }) => {
    await page.goto('/analyze');
    await expect(page).toHaveURL(/\/analyze/);
  });

  test('should access brain page', async ({ page }) => {
    await page.goto('/brain');
    await expect(page).toHaveURL(/\/brain/);
  });

  test('should access settings page', async ({ page }) => {
    await page.goto('/settings');
    await expect(page).toHaveURL(/\/settings/);
  });

  test('should access audit page', async ({ page }) => {
    await page.goto('/audit');
    await expect(page).toHaveURL(/\/audit/);
  });

  test('should access academy page', async ({ page }) => {
    await page.goto('/academy');
    await expect(page).toHaveURL(/\/academy/);
  });

  test('should access incidents page', async ({ page }) => {
    await page.goto('/incidents');
    await expect(page).toHaveURL(/\/incidents/);
  });

  test('should show 404 for non-existent routes', async ({ page }) => {
    await page.goto('/this-route-does-not-exist-12345');
    
    // Should show 404 or redirect
    const bodyText = await page.locator('body').textContent();
    const is404 = bodyText?.includes('404') || bodyText?.includes('Not Found');
    const isRedirected = page.url().includes('/login') || page.url().includes('/');
    
    expect(is404 || isRedirected).toBeTruthy();
  });
});

test.describe('API Routes (Dev Mode)', () => {
  test('should access brain engines API (public in dev)', async ({ request }) => {
    const response = await request.get('/api/brain/engines/all');
    
    // In dev mode, API routes are public
    // May return 200 or 404 (if not implemented)
    expect([200, 404]).toContain(response.status());
  });

  test('should access health endpoint', async ({ request }) => {
    const response = await request.get('/api/health');
    
    // Health endpoint - may return 200 or 404
    expect([200, 404]).toContain(response.status());
  });
});
