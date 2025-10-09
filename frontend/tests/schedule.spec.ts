import { expect, test } from "@playwright/test";

test.describe("Schedule workspace", () => {
  const technicians = [
    { id: "tech-1", email: "tech@example.com", role: "TECHNICIAN" },
    { id: "tech-2", email: "helper@example.com", role: "TECHNICIAN" },
  ];
  const bays = [
    { id: "bay-1", name: "Bay 1" },
    { id: "bay-2", name: "Bay 2" },
  ];

  test.beforeEach(async ({ page }) => {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 9, 0, 0, 0);
    const end = new Date(start.getTime() + 60 * 60 * 1000);

    const baseAppointments = [
      {
        id: "apt-1",
        title: "Brake inspection",
        startTime: start.toISOString(),
        endTime: end.toISOString(),
        technicianId: "tech-1",
        bayId: "bay-1",
      },
    ];

    await page.route("**/appointments", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(baseAppointments),
        });
        return;
      }
      route.fallback();
    });

    await page.route("**/appointments/calendar**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(baseAppointments),
      });
    });

    await page.route("**/users**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(technicians),
      });
    });

    await page.route("**/bays", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(bays),
      });
    });

    await page.goto("/schedule");
  });

  test("allows staff booking with assignments", async ({ page }) => {
    const newStart = new Date();
    newStart.setHours(14, 0, 0, 0);
    const newEnd = new Date(newStart.getTime() + 90 * 60 * 1000);

    let createRequestBody: Record<string, unknown> | undefined;
    let assignmentRequestBody: Record<string, unknown> | undefined;

    await page.route("**/appointments", async (route) => {
      if (route.request().method() === "POST") {
        createRequestBody = JSON.parse(route.request().postData() ?? "{}");
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: "apt-new",
            title: createRequestBody?.title,
            startTime: createRequestBody?.startTime,
            endTime: createRequestBody?.endTime,
            technicianId: createRequestBody?.technicianId ?? null,
            bayId: null,
          }),
        });
        return;
      }
      route.fallback();
    });

    await page.route("**/appointments/apt-new/assignment", async (route) => {
      assignmentRequestBody = JSON.parse(route.request().postData() ?? "{}");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message: "Assigned",
          appointment: {
            id: "apt-new",
            title: createRequestBody?.title,
            startTime: createRequestBody?.startTime,
            endTime: createRequestBody?.endTime,
            technicianId: assignmentRequestBody?.technicianId ?? null,
            bayId: assignmentRequestBody?.bayId ?? null,
          },
        }),
      });
    });

    const staffForm = page.locator("form").filter({ hasText: "Staff booking" });

    await staffForm.getByLabel("Title").fill("Alignment consultation");
    await staffForm
      .getByLabel("Start")
      .fill(newStart.toISOString().slice(0, 16));
    await staffForm
      .getByLabel("End")
      .fill(newEnd.toISOString().slice(0, 16));
    await staffForm.getByLabel("Vehicle ID").fill("VH-2001");
    await staffForm.getByLabel("Technician").selectOption("tech-2");
    await staffForm.getByLabel("Bay").selectOption("bay-2");
    await staffForm.getByLabel("Reason").fill("Customer reported pull to the right.");

    await staffForm.getByRole("button", { name: /create appointment/i }).click();

    await expect.poll(() => createRequestBody).not.toBeUndefined();
    await expect.poll(() => assignmentRequestBody).not.toBeUndefined();

    expect(createRequestBody).toMatchObject({
      title: "Alignment consultation",
      vehicleId: "VH-2001",
    });
    expect(assignmentRequestBody).toMatchObject({
      technicianId: "tech-2",
      bayId: "bay-2",
    });

    await expect(page.getByText("Alignment consultation")).toBeVisible();
  });

  test("supports drag and drop rescheduling", async ({ page }) => {
    const start = new Date();
    start.setHours(9, 0, 0, 0);
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    const shiftedStart = new Date(start.getTime() + 2 * 60 * 60 * 1000);
    const shiftedEnd = new Date(end.getTime() + 2 * 60 * 60 * 1000);

    let rescheduleBody: Record<string, unknown> | undefined;

    await page.route("**/appointments/apt-1/reschedule", async (route) => {
      rescheduleBody = JSON.parse(route.request().postData() ?? "{}");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message: "Appointment rescheduled",
          appointment: {
            id: "apt-1",
            title: "Brake inspection",
            startTime: shiftedStart.toISOString(),
            endTime: shiftedEnd.toISOString(),
            technicianId: "tech-1",
            bayId: "bay-1",
          },
        }),
      });
    });

    const event = page.locator('[data-event-id="apt-1"]');
    await event.waitFor();
    const box = await event.boundingBox();
    if (!box) {
      throw new Error("Event bounding box not found");
    }

    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2 + 160, { steps: 10 });
    await page.mouse.up();

    await expect.poll(() => rescheduleBody).not.toBeUndefined();

    expect(rescheduleBody).toMatchObject({
      appointmentId: "apt-1",
    });
    const receivedStart = new Date(String(rescheduleBody?.startTime));
    expect(receivedStart.getHours()).toBeGreaterThan(start.getHours());
  });
});
