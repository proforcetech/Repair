import { expect, test, type Route } from "@playwright/test";

const loginRoute = "**/api/auth/login";

async function respondJson(route: Route, status: number, body: Record<string, unknown>) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

test.describe("Authentication flows", () => {
  test("allows sign in without 2FA", async ({ page }) => {
    await page.route(loginRoute, async (route) => {
      const payload = JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>;
      expect(payload.email).toBe("tech@example.com");
      expect(payload.password).toBe("StrongPass123!");
      await respondJson(route, 200, { success: true });
    });

    await page.goto("/login");
    await page.getByLabel(/email address/i).fill("tech@example.com");
    await page.getByLabel(/password/i).fill("StrongPass123!");
    await page.getByRole("button", { name: /sign in/i }).click();

    await page.waitForURL("**/");
  });

  test("handles sign in with 2FA challenge", async ({ page }) => {
    let secondStepCalled = false;

    await page.route(loginRoute, async (route) => {
      const payload = JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>;

      if ("twoFactorToken" in payload) {
        secondStepCalled = true;
        await respondJson(route, 200, { success: true });
        return;
      }

      await respondJson(route, 401, {
        success: false,
        requiresTwoFactor: true,
        message: "Two-factor required",
      });
    });

    await page.goto("/login");
    await page.getByLabel(/email address/i).fill("twofa@example.com");
    await page.getByLabel(/password/i).fill("StrongPass123!");
    await page.getByRole("button", { name: /sign in/i }).click();

    await page.waitForURL("**/2fa");

    await page.getByLabel(/one-time passcode/i).fill("123456");
    await page.getByRole("button", { name: /verify/i }).click();

    await page.waitForURL("**/");
    expect(secondStepCalled).toBe(true);
  });

  test("confirms password reset flow", async ({ page }) => {
    await page.route("**/api/auth/reset-password", async (route) => {
      await respondJson(route, 200, {
        success: true,
        message: "Password has been reset.",
      });
    });

    await page.goto("/reset-password?token=test-token-123456");

    await page.getByLabel(/reset token/i).fill("test-token-123456");
    await page.getByLabel(/new password/i).fill("NewPassword123!");
    await page.getByLabel(/confirm password/i).fill("NewPassword123!");
    await page.getByRole("button", { name: /update password/i }).click();

    await expect(page.getByText(/password has been reset/i)).toBeVisible();
  });
});
