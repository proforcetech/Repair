import { Fragment } from "react";

import type { JobTimerView, TechnicianDashboardView } from "@/services/dashboard-mappers";

function TimerRow({ timer }: { timer: JobTimerView }) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/70 p-4 shadow-sm">
      <div className="flex items-center justify-between text-sm font-medium text-foreground">
        <span>{timer.jobTitle}</span>
        <span className="text-xs text-muted-foreground">{timer.elapsedLabel}</span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${Math.max(timer.progressPercent, 4)}%` }}
        />
      </div>
      <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
        <span>{Math.round(timer.elapsedSeconds / 60)} minutes logged</span>
        <span>Progress {timer.progressPercent}%</span>
      </div>
    </div>
  );
}

type JobTimersCardProps = {
  dashboard: TechnicianDashboardView | undefined;
};

export function JobTimersCard({ dashboard }: JobTimersCardProps) {
  if (!dashboard) {
    return null;
  }

  const { activeTimers, assignedJobs } = dashboard;

  return (
    <div className="grid gap-5 lg:grid-cols-[2fr,1fr]">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">Active job timers</h3>
          <span className="text-xs text-muted-foreground">{activeTimers.length} running</span>
        </div>
        {activeTimers.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border/70 bg-background/60 p-6 text-center text-sm text-muted-foreground">
            No technicians are currently clocked in.
          </p>
        ) : (
          <div className="space-y-3">
            {activeTimers.map((timer) => (
              <TimerRow key={timer.id} timer={timer} />
            ))}
          </div>
        )}
      </div>
      <aside className="rounded-xl border border-border/60 bg-background/70 p-4">
        <h4 className="text-sm font-semibold text-foreground">Assigned jobs</h4>
        <p className="text-xs text-muted-foreground">
          Track work-in-progress and promised delivery windows.
        </p>
        <div className="mt-3 space-y-2">
          {assignedJobs.length === 0 ? (
            <p className="text-xs text-muted-foreground">No assigned jobs.</p>
          ) : (
            assignedJobs.map((job) => (
              <Fragment key={job.id}>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-foreground">{job.title}</span>
                  <span className="text-muted-foreground">{job.status}</span>
                </div>
                <p className="text-[11px] text-muted-foreground">{job.dueDateLabel}</p>
              </Fragment>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
