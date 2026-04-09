import { test, expect } from '@playwright/test';

test.describe('Register Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register');
  });

  test('should display registration form', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/Register/i);
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should validate empty fields', async ({ page }) => {
    await page.click('button[type="submit"]');

    // Should show error or redirect back
    await expect(page).toHaveURL(/register/);
  });

  test('should validate email format', async ({ page }) => {
    await page.fill('input[name="email"]', 'invalid-email');
    await page.fill('input[name="password"]', 'Test1234!');
    await page.click('button[type="submit"]');

    // Should show error
    await expect(page).toHaveURL(/register/);
  });

  test('should validate password length', async ({ page }) => {
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'short');
    await page.click('button[type="submit"]');

    // Should show error
    await expect(page).toHaveURL(/register/);
  });

  test('should register successfully', async ({ page }) => {
    const email = `register-test-${Date.now()}@example.com`;
    const password = 'Test1234!';

    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');

    // Should redirect to login or learn page
    await expect(page).toHaveURL(/login/, { timeout: 5000 });
  });

  test('should handle duplicate email', async ({ page }) => {
    // Create a test user first
    const email = `duplicate-test-${Date.now()}@example.com`;
    const password = 'Test1234!';

    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/login/);

    // Try to register again
    await page.goto('/register');
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');

    // Should stay on register page or show error
    await expect(page).toHaveURL(/register/);
  });
});
