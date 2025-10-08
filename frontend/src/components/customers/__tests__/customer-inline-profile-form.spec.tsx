import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { CustomerInlineProfileForm } from "../customer-inline-profile-form";
import type { Customer } from "@/services/customers";

const updateCustomer = vi.fn();

vi.mock("@/services/customers", async () => {
  const actual = await vi.importActual<typeof import("@/services/customers")>("@/services/customers");
  return {
    ...actual,
    updateCustomer: (...args: unknown[]) => updateCustomer(...args),
  };
});

vi.mock("@/stores/toast-store", () => ({
  showToast: vi.fn(),
}));

function renderForm(customer: Customer) {
  const queryClient = new QueryClient();
  const onCustomerUpdated = vi.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <CustomerInlineProfileForm
        customerId={customer.id}
        customer={customer}
        onCustomerUpdated={onCustomerUpdated}
      />
    </QueryClientProvider>,
  );
  return { onCustomerUpdated };
}

describe("CustomerInlineProfileForm", () => {
  const customer: Customer = {
    id: "cust-1",
    fullName: "Alex Rivers",
    email: "alex@example.com",
    phone: "555-0300",
    street: "789 Oak Ave",
    city: "Centerville",
    state: "CA",
    zip: "90210",
  };

  it("submits inline profile updates", async () => {
    const updated: Customer = { ...customer, fullName: "Alexandra Rivers" };
    updateCustomer.mockResolvedValue(updated);

    const { onCustomerUpdated } = renderForm(customer);

    const nameInput = screen.getByLabelText("Full name");
    fireEvent.change(nameInput, { target: { value: "Alexandra Rivers" } });
    fireEvent.click(screen.getByRole("button", { name: /save profile/i }));

    await waitFor(() => {
      expect(updateCustomer).toHaveBeenCalledWith("cust-1", {
        fullName: "Alexandra Rivers",
        email: "alex@example.com",
        phone: "555-0300",
        street: "789 Oak Ave",
        city: "Centerville",
        state: "CA",
        zip: "90210",
      });
    });

    expect(onCustomerUpdated).toHaveBeenCalledWith(updated);
    expect(screen.getByDisplayValue("Alexandra Rivers")).toBeInTheDocument();
  });
});
