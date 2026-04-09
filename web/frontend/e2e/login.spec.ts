import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/Login/i);
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should validate empty fields', async ({ page }) => {
    await page.click('button[type="submit"]');

    // Should show error or redirect
    // This depends on the implementation
    await expect(page).toHaveURL(/login/);
  });

  test('should validate email format', async ({ page }) => {
    await page.fill('input[name="email"]', 'invalid-email');
    await page.fill('input[name="password"]', 'Test1234!');
    await page.click('button[type="submit"]');

    // Should show error or redirect back to login
    await expect(page).toHaveURL(/login/);
  });

  test('should validate password length', async ({ page }) => {
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'short');
    await page.click('button[type="submit"]');

    // Should show error or redirect back to login
    await expect(page).toHaveURL(/login/);
  });

  test('should login successfully', async ({ page }) => {
    // Create a test user
    const email = `login-test-${Date.now()}@example.com`;
    const password = 'Test1234!';

    // Register first
    await page.goto('/register');
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');

    // Should redirect to login or learn page
    await page.waitForURL(/login/, { timeout: 5000 });

    // Then login
    await page.goto('/login');
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');

    // Should redirect to learn page
    await expect(page).toHaveURL(/\/learn/);
  });

  test('should handle wrong credentials', async ({ page }) => {
    await page.fill('input[name="email"]', 'nonexistent@example.com');
    await page.fill('input[name="password"]', 'WrongPassword123!');
    await page.click('button[type="submit"]');

    // Should stay on login page or show error
    await expect(page).toHaveURL(/login/);
  });
});
