"use client";

import { useQuery } from "@tanstack/react-query";

import { PdfDownloadButton } from "@/components/customers";
import { getCustomerDashboard } from "@/services/customers";

export default function CustomerDashboardPage() {
  const dashboardQuery = useQuery({
    queryKey: ["portal", "dashboard"],
    queryFn: getCustomerDashboard,
  });

  if (dashboardQuery.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading your dashboard…</p>;
  }

  if (dashboardQuery.isError || !dashboardQuery.data) {
    return <p className="text-sm text-destructive">Unable to load dashboard data.</p>;
  }

  const { estimates, invoices, vehicles, appointments } = dashboardQuery.data;

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">Welcome back</h1>
        <p className="text-sm text-muted-foreground">
          Track upcoming appointments, download documents, and review your vehicles at a glance.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-border/60 bg-card/80 p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Recent invoices</h2>
          {invoices.length ? (
            <ul className="space-y-3">
              {invoices.slice(0, 5).map((invoice) => (
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
        </section>

        <section className="rounded-lg border border-border/60 bg-card/80 p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Pending estimates</h2>
          {estimates.length ? (
            <ul className="space-y-3">
              {estimates.slice(0, 5).map((estimate) => (
                <li key={estimate.id} className="rounded-md border border-border/60 bg-background/70 p-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium text-foreground">Estimate #{estimate.id}</p>
                      <p className="text-xs text-muted-foreground">
                        {estimate.status ?? "DRAFT"} · ${estimate.total?.toFixed(2) ?? "0.00"}
                      </p>
                    </div>
                    <PdfDownloadButton href={`/estimates/${estimate.id}/pdf`}>
                      Download PDF
                    </PdfDownloadButton>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No estimates to review.</p>
          )}
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-border/60 bg-card/80 p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Your vehicles</h2>
          {vehicles.length ? (
            <ul className="space-y-3">
              {vehicles.map((vehicle) => (
                <li key={vehicle.id} className="rounded-md border border-border/60 bg-background/70 p-3 text-sm">
                  <p className="font-medium text-foreground">
                    {vehicle.year} {vehicle.make} {vehicle.model}
                  </p>
                  <p className="text-xs text-muted-foreground">VIN {vehicle.vin}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">We don't have any vehicles on file yet.</p>
          )}
        </section>

        <section className="rounded-lg border border-border/60 bg-card/80 p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Upcoming appointments</h2>
          {appointments.length ? (
            <ul className="space-y-3">
              {appointments.map((appointment) => (
                <li key={appointment.id} className="rounded-md border border-border/60 bg-background/70 p-3 text-sm">
                  <p className="font-medium text-foreground">{appointment.serviceType ?? "Service"}</p>
                  <p className="text-xs text-muted-foreground">
                    {appointment.startTime
                      ? new Date(appointment.startTime).toLocaleString()
                      : "Date to be scheduled"}
                    {appointment.status ? ` · ${appointment.status}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No appointments scheduled.</p>
          )}
        </section>
      </div>
    </div>
  );
}
