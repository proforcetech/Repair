import type { Meta, StoryObj } from "@storybook/react";

import { SummaryGrid } from "@/components/dashboard/summary-grid";

const meta: Meta<typeof SummaryGrid> = {
  title: "Dashboard/SummaryGrid",
  component: SummaryGrid,
  args: {
    metrics: [
      { id: "open_jobs", label: "Open Jobs", value: 12 },
      { id: "overdue_invoices", label: "Overdue Invoices", value: 3 },
      { id: "parts_to_reorder", label: "Parts to Reorder", value: 7 },
    ],
  },
};

export default meta;

type Story = StoryObj<typeof SummaryGrid>;

export const Default: Story = {};
