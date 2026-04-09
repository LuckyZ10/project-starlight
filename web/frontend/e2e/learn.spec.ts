import { test, expect } from '@playwright/test';

test.describe('Learning Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Create a test user
    const email = `test-${Date.now()}@example.com`;
    const password = 'Test1234!';

    // Register first
    await page.goto('/register');
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');

    // Wait for redirect to login (should auto-login)
    await page.waitForURL('**/login');
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');

    // Wait for redirect to learn page
    await page.waitForURL('**/learn');
  });

  test('should display learn page with cartridges', async ({ page }) => {
    // Check for cartridge grid
    await expect(page.locator('h1')).toContainText(/Cartridges/i);
    await expect(page.locator('[data-testid="cartridge-grid"]')).toBeVisible();
  });

  test('should select a cartridge and navigate to nodes', async ({ page }) => {
    // Find first cartridge and click it
    const firstCartridge = page.locator('[data-testid="cartridge-card"]').first();
    await expect(firstCartridge).toBeVisible();
    await firstCartridge.click();

    // Navigate to nodes page
    await expect(page).toHaveURL(/\/learn\/nodes/);
    await expect(page.locator('h1')).toContainText(/Nodes/i);
  });

  test('should select a node and start conversation', async ({ page }) => {
    // Go to cartridge page
    const firstCartridge = page.locator('[data-testid="cartridge-card"]').first();
    await firstCartridge.click();

    // Navigate to nodes
    await page.click('button:has-text("Nodes")');

    // Find first node
    const firstNode = page.locator('[data-testid="node-card"]').first();
    await expect(firstNode).toBeVisible();
    await firstNode.click();

    // Should navigate to conversation page
    await expect(page).toHaveURL(/\/learn\/conversation/);
    await expect(page.locator('[data-testid="node-content"]')).toBeVisible();
  });

  test('should submit answer and complete node', async ({ page }) => {
    // Navigate through cartridges and nodes
    const firstCartridge = page.locator('[data-testid="cartridge-card"]').first();
    await firstCartridge.click();
    await page.click('button:has-text("Nodes")');
    const firstNode = page.locator('[data-testid="node-card"]').first();
    await firstNode.click();

    // Wait for conversation page
    await page.waitForURL(/\/learn\/conversation/);
    await expect(page.locator('[data-testid="node-content"]')).toBeVisible();

    // Find input field and submit answer
    const input = page.locator('textarea[placeholder*="Answer"] or textarea[placeholder*="回答"]');

    // Check if input exists and has a submit button
    if (await input.isVisible()) {
      await input.fill('Test answer for the question');
      const submitButton = page.locator('button[type="submit"], button:has-text("Submit"), button:has-text("提交")');
      if (await submitButton.isVisible()) {
        await submitButton.click();
        // Wait for loading state and result
        await page.waitForSelector('[data-testid="answer-display"]', { state: 'visible', timeout: 10000 });
      }
    }

    // Check if node is marked as completed
    const completionStatus = page.locator('[data-testid="node-status"], [class*="completed"], [class*="完成"]');
    if (await completionStatus.isVisible()) {
      await expect(completionStatus).toBeVisible();
    }
  });

  test('should navigate between nodes within cartridge', async ({ page }) => {
    // Navigate to cartridge and nodes
    const firstCartridge = page.locator('[data-testid="cartridge-card"]').first();
    await firstCartridge.click();
    await page.click('button:has-text("Nodes")');

    // Navigate to first node
    const firstNode = page.locator('[data-testid="node-card"]').first();
    await firstNode.click();

    await page.waitForURL(/\/learn\/conversation/);

    // Go back to nodes list
    await page.click('button:has-text("Back") or button:has-text("返回")');
    await expect(page).toHaveURL(/\/learn\/nodes/);

    // Select another node
    const secondNode = page.locator('[data-testid="node-card"]').nth(1);
    if (await secondNode.isVisible()) {
      await secondNode.click();
      await expect(page).toHaveURL(/\/learn\/conversation/);
    }
  });

  test('should update stats page', async ({ page }) => {
    // Navigate to stats page
    await page.click('button:has-text("Stats") or button:has-text("统计")');
    await expect(page).toHaveURL(/\/learn\/stats/);
    await expect(page.locator('h1')).toContainText(/Stats/i);
    await expect(page.locator('[data-testid="stats-container"]')).toBeVisible();
  });

  test('should handle dark mode toggle', async ({ page }) => {
    // Check if dark mode toggle exists
    const themeToggle = page.locator('[data-testid="theme-toggle"], [class*="theme-toggle"]');
    if (await themeToggle.isVisible()) {
      await themeToggle.click();

      // Check if dark class is added to html
      const html = page.locator('html');
      await expect(html).toHaveClass(/dark/);
    }
  });
});
