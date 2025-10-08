import type { Meta, StoryObj } from "@storybook/react";

import { OverdueInvoicesTable } from "@/components/dashboard/overdue-invoices-table";

const meta: Meta<typeof OverdueInvoicesTable> = {
  title: "Dashboard/OverdueInvoicesTable",
  component: OverdueInvoicesTable,
  args: {
    invoices: [
      { id: "INV-1001", status: "OVERDUE", total: 342.5 },
      { id: "INV-1002", status: "OVERDUE", total: 129.99 },
    ],
  },
};

export default meta;

type Story = StoryObj<typeof OverdueInvoicesTable>;

export const Default: Story = {};
