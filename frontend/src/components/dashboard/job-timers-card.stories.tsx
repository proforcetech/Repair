import type { Meta, StoryObj } from "@storybook/react";

import { JobTimersCard } from "@/components/dashboard/job-timers-card";
import type { TechnicianDashboardView } from "@/services/dashboard-mappers";

const dashboard: TechnicianDashboardView = {
  activeTimerCount: 2,
  activeTimers: [
    {
      id: "job-1",
      jobId: "job-1",
      jobTitle: "Brake replacement",
      startedAt: new Date("2024-01-10T10:00:00Z"),
      elapsedSeconds: 3600,
      elapsedLabel: "about 1 hour ago",
      progressPercent: 45,
    },
    {
      id: "job-2",
      jobId: "job-2",
      jobTitle: "AC diagnostics",
      startedAt: new Date("2024-01-10T11:00:00Z"),
      elapsedSeconds: 1200,
      elapsedLabel: "20 minutes ago",
      progressPercent: 20,
    },
  ],
  assignedJobs: [
    {
      id: "job-1",
      title: "Brake replacement",
      status: "IN_PROGRESS",
      dueDateLabel: "Due in 3 hours",
    },
    {
      id: "job-2",
      title: "AC diagnostics",
      status: "QUEUED",
      dueDateLabel: "Promise in 5 hours",
    },
  ],
};

const meta: Meta<typeof JobTimersCard> = {
  title: "Dashboard/JobTimersCard",
  component: JobTimersCard,
  args: {
    dashboard,
  },
};

export default meta;

type Story = StoryObj<typeof JobTimersCard>;

export const Default: Story = {};
