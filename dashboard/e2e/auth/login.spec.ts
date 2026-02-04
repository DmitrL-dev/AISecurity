/**
 * E2E Tests: Login Flow
 * 
 * Tests for authentication flow in DEV MODE (most routes are public)
 */

import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login');
    
    // Login page should exist and load
    await expect(page).toHaveURL(/\/login/);
    
    // Should have some form or content
    await expect(page.locator('body')).toBeVisible();
  });

  test('should access brain page directly (dev mode - public routes)', async ({ page }) => {
    // In dev mode, /brain is public - no redirect to login
    await page.goto('/brain');
    
    // Should stay on brain page (not redirect)
    await expect(page).toHaveURL(/\/brain/);
    
    // Page should have content
    await expect(page.locator('body')).toBeVisible();
  });

  test('should access analyze page directly (dev mode)', async ({ page }) => {
    await page.goto('/analyze');
    await expect(page).toHaveURL(/\/analyze/);
  });

  test('should access settings page directly (dev mode)', async ({ page }) => {
    await page.goto('/settings');
    await expect(page).toHaveURL(/\/settings/);
  });

  test('should access audit page directly (dev mode)', async ({ page }) => {
    await page.goto('/audit');
    await expect(page).toHaveURL(/\/audit/);
  });

  test('should load homepage', async ({ page }) => {
    await page.goto('/');
    
    // Homepage should have main content with AI Security theme
    await expect(page.locator('body')).toContainText(/SENTINEL|Security|AI/i);
  });
});
