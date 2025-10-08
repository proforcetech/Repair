import { QuickActions } from "@/components/dashboard/quick-actions";

const metrics = [
    { label: "Open repair orders", value: "18", delta: "+3 today", trend: "positive" as const },
    { label: "Avg. cycle time", value: "4.2 hrs", delta: "-12% vs last week", trend: "positive" as const },
    { label: "Outstanding invoices", value: "$12.4K", delta: "5 due soon", trend: "warning" as const },
    { label: "Customer satisfaction", value: "4.8 / 5", delta: "Last 30 surveys", trend: "positive" as const },
];

const recentUpdates = [
    {
        title: "Bay 3  Brake pad replacement",
        description: "Technician Rivera requested quality inspection.",
        time: "12 minutes ago",
    },
    {
        title: "Mobile  Fleet tire rotation",
        description: "Job marked ready for invoicing.",
        time: "24 minutes ago",
    },
    {
        title: "Bay 1  Hybrid diagnostic",
        description: "Waiting on high voltage isolation test results.",
        time: "58 minutes ago",
    },
];

export default function HomePage() {
    return (
        <div className="space-y-8">
            <section className="flex flex-col gap-2">
                <h1 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
                    Morning overview
                </h1>
                <p className="text-sm text-muted-foreground md:text-base">
                    Track bay utilization, technician load, and customer follow-ups in a single workspace.
                </p>
            </section>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                {metrics.map((metric) => (
                    <article
                        key={metric.label}
                        className="rounded-xl border border-border/70 bg-gradient-to-br from-card to-card/80 p-5 shadow-sm"
                    >
                        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{metric.label}</p>
                        <p className="mt-3 text-2xl font-semibold text-foreground md:text-3xl">{metric.value}</p>
                        <p
                            className={
                                metric.trend === "positive"
                                    ? "mt-2 text-xs font-medium text-success"
                                    : "mt-2 text-xs font-medium text-warning"
                            }
                        >
                            {metric.delta}
                        </p>
                    </article>
                ))}
            </section>

            <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
                <article className="space-y-4 rounded-xl border border-border/70 bg-card/70 p-5 shadow-sm">
                    <header className="flex items-center justify-between">
                        <div>
                            <h2 className="text-base font-semibold text-foreground">Live workflow</h2>
                            <p className="text-xs text-muted-foreground">Realtime updates from bays, mobile vans, and customer approvals.</p>
                        </div>
                        <span className="rounded-full border border-success/30 bg-success/10 px-3 py-1 text-xs font-medium text-success">
                            6 in progress
                        </span>
                    </header>

                    <ul className="space-y-3">
                        {recentUpdates.map((update) => (
                            <li
                                key={update.title}
                                className="rounded-lg border border-border/60 bg-background/60 p-4 shadow-sm"
                            >
                                <div className="flex items-center justify-between gap-4">
                                    <span className="text-sm font-semibold text-foreground">{update.title}</span>
                                    <span className="text-xs text-muted-foreground">{update.time}</span>
                                </div>
                                <p className="mt-2 text-xs text-muted-foreground">{update.description}</p>
                            </li>
                        ))}
                    </ul>
                </article>

                <aside className="space-y-4 rounded-xl border border-border/70 bg-card/60 p-5 shadow-sm">
                    <div>
                        <h2 className="text-base font-semibold text-foreground">Quick actions</h2>
                        <p className="text-xs text-muted-foreground">
                            Surface the most common flows for your service writers and mobile team.
                        </p>
                    </div>
                    <QuickActions />
                </aside>
            </section>
        </div>
    );
}