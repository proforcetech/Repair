import { test, expect } from "@playwright/test";

import { apiClient } from "@/lib/api/client";
import { submitWarrantyClaim } from "@/services/warranty";

test.describe("warranty portal uploads", () => {
  test("includes attachment when submitting a claim", async () => {
    const file = new File(["sample"], "evidence.txt", { type: "text/plain" });
    let received: FormData | null = null;

    const originalPost = apiClient.post.bind(apiClient);
    (apiClient as unknown as { post: typeof apiClient.post }).post = async (url, data, config) => {
      received = data as FormData;
      expect(url).toBe("/warranty/warranty");
      expect(config?.headers?.["Content-Type"]).toContain("multipart/form-data");
      return { data: { message: "ok" } } as unknown as Awaited<ReturnType<typeof originalPost>>;
    };

    try {
      await submitWarrantyClaim({ workOrderId: "WO-42", description: "Brake noise", attachment: file });
    } finally {
      (apiClient as unknown as { post: typeof apiClient.post }).post = originalPost;
    }

    expect(received).not.toBeNull();
    const entries = Array.from(received!.entries());
    expect(entries).toEqual(
      expect.arrayContaining([
        ["work_order_id", "WO-42"],
        ["description", "Brake noise"],
      ]),
    );
    const fileEntry = entries.find(([key]) => key === "file");
    expect(fileEntry).toBeTruthy();
  });
});
