import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import {
  inventoryKeys,
  useConsumePart,
  useGeneratePurchaseOrders,
  useGeneratedPurchaseOrders,
  useTransferStock,
  validateConsumptionQuantity,
  validateTransferQuantity,
} from "@/hooks/use-inventory";
import type { InventoryPart, PurchaseOrderRecord } from "@/services/inventory";
import * as inventoryService from "@/services/inventory";

vi.mock("@/stores/toast-store", () => ({
  showToast: vi.fn(),
}));

afterEach(() => {
  vi.restoreAllMocks();
});

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("quantity validation", () => {
  it("rejects zero or negative transfers", () => {
    expect(validateTransferQuantity(0, 10)).toBe("Quantity must be at least 1");
    expect(validateTransferQuantity(-3, 10)).toBe("Quantity must be at least 1");
  });

  it("rejects transfers above available inventory", () => {
    expect(validateTransferQuantity(12, 8)).toBe("Cannot transfer more than 8 units");
  });

  it("rejects consumption above available inventory", () => {
    expect(validateConsumptionQuantity(5, 2)).toBe("Only 2 units available");
  });

  it("accepts valid quantities", () => {
    expect(validateTransferQuantity(4, 10)).toBeNull();
    expect(validateConsumptionQuantity(2, 5)).toBeNull();
  });
});

describe("inventory cache updates", () => {
  it("reduces quantity after transfer", async () => {
    const queryClient = createTestQueryClient();
    const initialParts: InventoryPart[] = [
      { id: "part-1", sku: "ABC", quantity: 12, reorderMin: 4, reorderMax: null, location: "Main", vendor: "Vendor" },
    ];
    queryClient.setQueryData(inventoryKeys.parts(), initialParts);
    const transferSpy = vi
      .spyOn(inventoryService, "transferStock")
      .mockResolvedValue({ message: "Transfer complete" } as never);

    const { result } = renderHook(() => useTransferStock(), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync({
        partId: "part-1",
        fromLocation: "Main",
        toLocation: "Truck",
        quantity: 5,
      });
    });

    const updated = queryClient.getQueryData<InventoryPart[]>(inventoryKeys.parts());
    expect(updated?.[0].quantity).toBe(7);
    expect(transferSpy).toHaveBeenCalledWith({
      partId: "part-1",
      fromLocation: "Main",
      toLocation: "Truck",
      quantity: 5,
    });
  });

  it("reduces quantity after consumption", async () => {
    const queryClient = createTestQueryClient();
    const initialParts: InventoryPart[] = [
      { id: "part-2", sku: "XYZ", quantity: 6, reorderMin: 2, reorderMax: null, location: "Main", vendor: "Vendor" },
    ];
    queryClient.setQueryData(inventoryKeys.parts(), initialParts);

    const consumeSpy = vi
      .spyOn(inventoryService, "consumePart")
      .mockResolvedValue({ id: "usage-1", jobId: "job-1", partId: "part-2", quantity: 3 } as never);

    const { result } = renderHook(() => useConsumePart(), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync({ jobId: "job-1", partId: "part-2", quantity: 3 });
    });

    const updated = queryClient.getQueryData<InventoryPart[]>(inventoryKeys.parts());
    expect(updated?.[0].quantity).toBe(3);
    expect(consumeSpy).toHaveBeenCalledWith({ jobId: "job-1", partId: "part-2", quantity: 3 });
  });
});

describe("purchase order workflows", () => {
  it("fetches generated purchase orders from the API", async () => {
    const queryClient = createTestQueryClient();
    const wrapper = createWrapper(queryClient);
    const existing: PurchaseOrderRecord[] = [
      { id: "po-1", vendor: "Vendor A", status: "SENT", createdAt: new Date().toISOString(), updatedAt: null, emailSent: true },
    ];

    const fetchSpy = vi
      .spyOn(inventoryService, "fetchPurchaseOrders")
      .mockResolvedValue(existing as never);

    const { result } = renderHook(() => useGeneratedPurchaseOrders(), { wrapper });

    await waitFor(() => {
      expect(result.current.data).toEqual(existing);
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("stores newly generated purchase orders and merges with cache", async () => {
    const queryClient = createTestQueryClient();
    const wrapper = createWrapper(queryClient);
    const previous: PurchaseOrderRecord[] = [
      { id: "po-existing", vendor: "Vendor C", status: "DRAFT", createdAt: null, updatedAt: null, emailSent: false },
    ];
    queryClient.setQueryData(inventoryKeys.purchaseOrders(), previous);

    const created: PurchaseOrderRecord[] = [
      { id: "po-1", vendor: "Vendor A", status: "SENT", createdAt: new Date().toISOString(), updatedAt: null, emailSent: true },
      { id: "po-existing", vendor: "Vendor C", status: "SENT", createdAt: null, updatedAt: null, emailSent: true },
    ];

    vi.spyOn(inventoryService, "fetchPurchaseOrders").mockResolvedValue(created as never);

    const generateSpy = vi
      .spyOn(inventoryService, "generatePurchaseOrders")
      .mockResolvedValue({ created } as never);

    const { result } = renderHook(() => useGeneratePurchaseOrders(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync();
    });

    await waitFor(() => {
      expect(generateSpy).toHaveBeenCalledTimes(1);
      const cached = queryClient.getQueryData<PurchaseOrderRecord[]>(inventoryKeys.purchaseOrders());
      expect(cached).toEqual(created);
    });
  });
});
