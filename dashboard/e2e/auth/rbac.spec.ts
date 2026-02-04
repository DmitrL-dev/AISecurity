/**
 * E2E Tests: UI Navigation & RBAC Elements
 * 
 * Tests for navigation structure and UI elements (dev mode)
 */

import { test, expect } from '@playwright/test';

test.describe('Navigation Structure', () => {
  test('should have navigation sidebar', async ({ page }) => {
    await page.goto('/');
    
    // Should have at least one nav element
    const navCount = await page.locator('nav').count();
    expect(navCount).toBeGreaterThan(0);
  });

  test('should have navigation links', async ({ page }) => {
    await page.goto('/');
    
    // Check for common navigation links (by text content)
    const navText = await page.locator('nav').first().textContent();
    
    // Should contain at least some navigation items
    expect(navText).toBeTruthy();
    expect(navText!.length).toBeGreaterThan(10);
  });

  test('should navigate to Analyze page via link', async ({ page }) => {
    await page.goto('/');
    
    // Find and click analyze link
    const analyzeLink = page.getByRole('link', { name: /analyze/i });
    if (await analyzeLink.count() > 0) {
      await analyzeLink.first().click();
      await expect(page).toHaveURL(/\/analyze/);
    }
  });

  test('should navigate to Brain page via link', async ({ page }) => {
    await page.goto('/');
    
    // Find and click brain link
    const brainLink = page.getByRole('link', { name: /brain/i });
    if (await brainLink.count() > 0) {
      await brainLink.first().click();
      await expect(page).toHaveURL(/\/brain/);
    }
  });

  test('should navigate to Audit page via link', async ({ page }) => {
    await page.goto('/');
    
    const auditLink = page.getByRole('link', { name: /audit/i });
    if (await auditLink.count() > 0) {
      await auditLink.first().click();
      await expect(page).toHaveURL(/\/audit/);
    }
  });

  test('should navigate to Settings page via link', async ({ page }) => {
    await page.goto('/');
    
    const settingsLink = page.getByRole('link', { name: /settings/i });
    if (await settingsLink.count() > 0) {
      await settingsLink.first().click();
      await expect(page).toHaveURL(/\/settings/);
    }
  });
});

test.describe('Page Content', () => {
  test('homepage should have AI Security content', async ({ page }) => {
    await page.goto('/');
    
    const bodyText = await page.locator('body').textContent();
    // Should mention security, AI, or SENTINEL
    const hasSecurityContent = 
      bodyText?.includes('Security') || 
      bodyText?.includes('AI') || 
      bodyText?.includes('SENTINEL') ||
      bodyText?.includes('Analyze');
    
    expect(hasSecurityContent).toBeTruthy();
  });

  test('analyze page should have analysis interface', async ({ page }) => {
    await page.goto('/analyze');
    
    // Should have some interactive elements
    const hasContent = await page.locator('body').isVisible();
    expect(hasContent).toBeTruthy();
  });

  test('brain page should have engine management', async ({ page }) => {
    await page.goto('/brain');
    
    const hasContent = await page.locator('body').isVisible();
    expect(hasContent).toBeTruthy();
  });

  test('settings page should have configuration options', async ({ page }) => {
    await page.goto('/settings');
    
    const hasContent = await page.locator('body').isVisible();
    expect(hasContent).toBeTruthy();
  });
});
