import { expect, test } from '@playwright/test';

test('player completes a mocked Steam redirect and sees their profile', async ({ page }) => {
  let signedIn = false;
  await page.route('**/api/v1/auth/session', async (route) => {
    if (!signedIn) {
      await route.fulfill({ status: 401, body: 'Unauthorized' });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        steamId: '76561198000000000',
        personaName: 'Example Player',
        avatarUrl: 'https://steamcdn-a.akamaihd.net/example.jpg',
        profileStatus: 'AVAILABLE',
      }),
    });
  });
  await page.route('**/api/v1/auth/steam/login', async (route) => {
    await route.fulfill({
      status: 302,
      headers: { location: '/mock-steam/login' },
    });
  });
  await page.route('**/api/v1/auth/steam/callback?**', async (route) => {
    signedIn = true;
    await route.fulfill({
      status: 302,
      headers: { location: '/' },
    });
  });

  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Log in with Steam' })).toBeVisible();
  await expect(page.locator('input[type="password"]')).toHaveCount(0);

  await page.getByRole('button', { name: 'Log in with Steam' }).click();
  await expect(page).toHaveURL(/127\.0\.0\.1:5173\/mock-steam\/login/);
  await page.setContent(`
    <main>
      <h1>Mock Steam Community sign-in</h1>
      <label>Password <input type="password" /></label>
      <button onclick="window.location.href='http://127.0.0.1:5173/api/v1/auth/steam/callback?state=e2e&openid.mode=id_res'">
        Authenticate
      </button>
    </main>`);
  await expect(page.locator('input[type="password"]')).toHaveCount(1);
  await page.getByRole('button', { name: 'Authenticate' }).click();

  await expect(page).toHaveURL(/127\.0\.0\.1:5173\/$/);
  await expect(page.getByText('Example Player')).toBeVisible();
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
});
