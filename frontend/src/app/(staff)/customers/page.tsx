"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { CustomerForm } from "@/components/customers/customer-form";
import { Customer, CustomerSearchFilters, searchCustomers } from "@/services/customers";
import { showToast } from "@/stores/toast-store";

export default function CustomersPage() {
  const [filters, setFilters] = useState<CustomerSearchFilters>({
    name: "",
    email: "",
    phone: "",
  });

  const query = useQuery<Customer[]>({
    queryKey: ["customers", filters],
    queryFn: () => searchCustomers(filters),
    keepPreviousData: true,
  });

  const updateFilters = useMutation({
    mutationFn: async (values: CustomerSearchFilters) => values,
    onSuccess: (values) => {
      setFilters(values);
    },
  });

  const results = useMemo(() => query.data ?? [], [query.data]);

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">Customer Directory</h1>
        <p className="text-sm text-muted-foreground">
          Search for existing customers, review their contact information, and add new customer records.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
        <section className="space-y-6">
          <SearchForm
            defaultValues={filters}
            isSubmitting={updateFilters.isPending}
            onSubmit={(values) => updateFilters.mutate(values)}
          />

          <div className="rounded-lg border border-border/60 bg-card/80 p-4 shadow-sm">
            {query.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading customers…</p>
            ) : query.isError ? (
              <p className="text-sm text-destructive">Unable to load customers.</p>
            ) : results.length === 0 ? (
              <p className="text-sm text-muted-foreground">No customers found. Adjust your search filters.</p>
            ) : (
              <ul className="space-y-3">
                {results.map((customer) => (
                  <CustomerListItem key={customer.id} customer={customer} />
                ))}
              </ul>
            )}
          </div>
        </section>

        <aside className="rounded-lg border border-border/60 bg-card/80 p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground">Add a customer</h2>
          <p className="mb-4 text-sm text-muted-foreground">
            Capture contact and mailing information for new customers in a single step.
          </p>
          <CustomerForm
            onSuccess={() => {
              showToast({
                title: "Customer added",
                description: "The directory has been refreshed with your new customer.",
                variant: "success",
              });
              query.refetch();
            }}
          />
        </aside>
      </div>
    </div>
  );
}

type SearchFormProps = {
  defaultValues: CustomerSearchFilters;
  isSubmitting: boolean;
  onSubmit: (values: CustomerSearchFilters) => void;
};

function SearchForm({ defaultValues, isSubmitting, onSubmit }: SearchFormProps) {
  const [localValues, setLocalValues] = useState(defaultValues);

  useEffect(() => {
    setLocalValues(defaultValues);
  }, [defaultValues]);

  return (
    <form
      className="grid gap-4 rounded-lg border border-border/60 bg-card/80 p-4 shadow-sm md:grid-cols-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(localValues);
      }}
    >
      <div className="flex flex-col gap-2 text-sm">
        <label className="font-medium text-foreground" htmlFor="name">
          Name
        </label>
        <input
          id="name"
          type="text"
          className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          value={localValues.name ?? ""}
          onChange={(event) =>
            setLocalValues((current) => ({ ...current, name: event.target.value }))
          }
          placeholder="Search by name"
        />
      </div>

      <div className="flex flex-col gap-2 text-sm">
        <label className="font-medium text-foreground" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          value={localValues.email ?? ""}
          onChange={(event) =>
            setLocalValues((current) => ({ ...current, email: event.target.value }))
          }
          placeholder="Search by email"
        />
      </div>

      <div className="flex flex-col gap-2 text-sm">
        <label className="font-medium text-foreground" htmlFor="phone">
          Phone
        </label>
        <input
          id="phone"
          type="tel"
          className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          value={localValues.phone ?? ""}
          onChange={(event) =>
            setLocalValues((current) => ({ ...current, phone: event.target.value }))
          }
          placeholder="Search by phone"
        />
      </div>

      <div className="md:col-span-3">
        <button
          type="submit"
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Applying…" : "Apply filters"}
        </button>
      </div>
    </form>
  );
}

type CustomerListItemProps = {
  customer: Customer;
};

function CustomerListItem({ customer }: CustomerListItemProps) {
  return (
    <li className="flex flex-col gap-1 rounded-md border border-border/50 bg-background/60 p-4 shadow-sm transition hover:border-primary/60 hover:shadow">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-foreground">{customer.fullName}</h3>
          <p className="text-sm text-muted-foreground">{customer.email}</p>
        </div>
        <Link
          href={`/customers/${customer.id}`}
          className="inline-flex items-center rounded-md border border-border px-3 py-1 text-sm font-medium text-foreground transition hover:bg-accent hover:text-accent-foreground"
        >
          View profile
        </Link>
      </div>
      <dl className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
        <div>
          <dt className="font-medium text-foreground">Phone</dt>
          <dd>{customer.phone}</dd>
        </div>
        <div>
          <dt className="font-medium text-foreground">Address</dt>
          <dd>
            {[customer.street, customer.city, customer.state, customer.zip]
              .filter(Boolean)
              .join(", ") || "—"}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-foreground">Visits</dt>
          <dd>{customer.visits ?? 0}</dd>
        </div>
      </dl>
    </li>
  );
}
