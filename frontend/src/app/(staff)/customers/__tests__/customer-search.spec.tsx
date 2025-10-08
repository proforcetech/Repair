import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CustomersPage from "../page";
import type { Customer } from "@/services/customers";

vi.mock("@/stores/toast-store", () => ({
  showToast: vi.fn(),
}));

const searchCustomers = vi.fn();
const createCustomer = vi.fn();
const updateCustomer = vi.fn();

vi.mock("@/services/customers", async () => {
  const actual = await vi.importActual<typeof import("@/services/customers")>("@/services/customers");
  return {
    ...actual,
    searchCustomers: (...args: unknown[]) => searchCustomers(...args),
    createCustomer: (...args: unknown[]) => createCustomer(...(args as Parameters<typeof createCustomer>)),
    updateCustomer: (...args: unknown[]) => updateCustomer(...(args as Parameters<typeof updateCustomer>)),
  };
});

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("CustomersPage search filters", () => {
  const customers: Customer[] = [
    {
      id: "1",
      fullName: "Alice Johnson",
      email: "alice@example.com",
      phone: "555-0100",
      street: "123 Main St",
      city: "Springfield",
      state: "IL",
      zip: "62704",
      visits: 3,
    },
    {
      id: "2",
      fullName: "Bob Smith",
      email: "bob@example.com",
      phone: "555-0200",
      street: "456 Elm St",
      city: "Shelbyville",
      state: "IL",
      zip: "62565",
      visits: 1,
    },
  ];

  beforeEach(() => {
    searchCustomers.mockImplementation(async (filters?: { name?: string }) => {
      if (filters?.name) {
        const term = filters.name.toLowerCase();
        return customers.filter((customer) => customer.fullName.toLowerCase().includes(term));
      }
      return customers;
    });
    createCustomer.mockResolvedValue(customers[0]);
  });

  it("filters the customer list by name", async () => {
    renderWithClient(<CustomersPage />);

    expect(await screen.findByText("Alice Johnson")).toBeInTheDocument();
    expect(screen.getByText("Bob Smith")).toBeInTheDocument();

    const nameInput = screen.getByLabelText("Name");
    fireEvent.change(nameInput, { target: { value: "Bob" } });
    fireEvent.submit(nameInput.closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(searchCustomers).toHaveBeenLastCalledWith({ name: "Bob", email: "", phone: "" });
    });

    expect(await screen.findByText("Bob Smith")).toBeInTheDocument();
    expect(screen.queryByText("Alice Johnson")).not.toBeInTheDocument();
  });
});
