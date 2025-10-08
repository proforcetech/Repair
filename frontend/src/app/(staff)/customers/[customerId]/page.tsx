"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import {
  CustomerInlineProfileForm,
  VehicleForm,
  PdfDownloadButton,
} from "@/components/customers";
import {
  Customer,
  CustomerProfile,
  Vehicle,
  getCustomer,
  getCustomerProfile,
  getCustomerVehicles,
} from "@/services/customers";
import { showToast } from "@/stores/toast-store";

export default function CustomerDetailPage() {
  const params = useParams<{ customerId: string }>();
  const customerId = params?.customerId;
  const queryClient = useQueryClient();

  const customerQuery = useQuery<Customer>({
    queryKey: ["customer", customerId],
    queryFn: () => getCustomer(customerId!),
    enabled: Boolean(customerId),
  });

  const profileQuery = useQuery<CustomerProfile>({
    queryKey: ["customer", customerId, "profile"],
    queryFn: () => getCustomerProfile(customerId!),
    enabled: Boolean(customerId),
  });

  const vehiclesQuery = useQuery<Vehicle[]>({
    queryKey: ["customer", customerId, "vehicles"],
    queryFn: () => getCustomerVehicles(customerId!),
    enabled: Boolean(customerId),
  });

  const isLoading = customerQuery.isLoading || profileQuery.isLoading;

  const customer = customerQuery.data;
  const profile = profileQuery.data;
  const vehicles = vehiclesQuery.data ?? profile?.vehicles ?? [];

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading profile…</p>;
  }

  if (customerQuery.isError) {
    return <p className="text-sm text-destructive">Unable to load customer details.</p>;
  }

  if (!customer) {
    return <p className="text-sm text-destructive">Customer not found.</p>;
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">{customer.fullName}</h1>
        <p className="text-sm text-muted-foreground">
          Manage contact information, vehicles, and financial documents for this customer.
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <div className="space-y-6">
          <div className="rounded-lg border border-border/60 bg-card/80 p-5 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-foreground">Profile</h2>
            <CustomerInlineProfileForm
              customerId={customer.id}
              customer={customer}
              onCustomerUpdated={(updated) => {
                queryClient.setQueryData(["customer", customer.id], updated);
              }}
            />
          </div>

          <div className="rounded-lg border border-border/60 bg-card/80 p-5 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-foreground">Vehicles</h2>
            {vehicles.length === 0 ? (
              <p className="text-sm text-muted-foreground">No vehicles on file.</p>
            ) : (
              <ul className="space-y-3">
                {vehicles.map((vehicle) => (
                  <li
                    key={vehicle.id}
                    className="rounded-md border border-border/60 bg-background/70 p-4 text-sm shadow-sm"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-semibold text-foreground">
                          {vehicle.year} {vehicle.make} {vehicle.model}
                        </p>
                        <p className="text-xs text-muted-foreground">VIN {vehicle.vin}</p>
                      </div>
                      <PdfDownloadButton
                        href={`/vehicles/${vehicle.id}/history/pdf`}
                        filename={`vehicle-${vehicle.vin}.pdf`}
                      >
                        History PDF
                      </PdfDownloadButton>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <aside className="space-y-6">
          <div className="rounded-lg border border-border/60 bg-card/80 p-5 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-foreground">Add vehicle</h2>
            <VehicleForm
              mode="create"
              customerId={customer.id}
              onSuccess={() => {
                showToast({
                  title: "Vehicle added",
                  description: "Vehicle list refreshed",
                  variant: "success",
                });
                vehiclesQuery.refetch();
              }}
            />
          </div>

          <div className="rounded-lg border border-border/60 bg-card/80 p-5 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-foreground">Invoices</h2>
            {profileQuery.isError ? (
              <p className="text-sm text-destructive">Unable to load invoices.</p>
            ) : profile?.invoices?.length ? (
              <ul className="space-y-3">
                {profile.invoices.map((invoice) => (
                  <li key={invoice.id} className="rounded-md border border-border/60 bg-background/70 p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-medium text-foreground">Invoice #{invoice.id}</p>
                        <p className="text-xs text-muted-foreground">
                          {invoice.status ?? "PENDING"} · ${invoice.total?.toFixed(2) ?? "0.00"}
                        </p>
                      </div>
                      <PdfDownloadButton href={`/invoices/${invoice.id}/pdf`}>
                        Download PDF
                      </PdfDownloadButton>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No invoices available.</p>
            )}
          </div>

          <div className="rounded-lg border border-border/60 bg-card/80 p-5 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-foreground">Warranty claims</h2>
            {profileQuery.isError ? (
              <p className="text-sm text-destructive">Unable to load warranty claims.</p>
            ) : profile?.warrantyClaims?.length ? (
              <ul className="space-y-3">
                {profile.warrantyClaims.map((claim) => (
                  <li key={claim.id} className="rounded-md border border-border/60 bg-background/70 p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-medium text-foreground">Claim #{claim.id}</p>
                        <p className="text-xs text-muted-foreground">
                          {claim.status} · {claim.createdAt ? new Date(claim.createdAt).toLocaleDateString() : "—"}
                        </p>
                      </div>
                      {claim.workOrderId && (
                        <Link
                          href={`/work-orders/${claim.workOrderId}`}
                          className="inline-flex items-center rounded-md border border-border px-3 py-1 text-xs font-medium text-foreground transition hover:bg-accent hover:text-accent-foreground"
                        >
                          View work order
                        </Link>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No warranty claims on file.</p>
            )}
          </div>
        </aside>
      </section>
    </div>
  );
}
