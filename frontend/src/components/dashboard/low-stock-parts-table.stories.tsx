import type { Meta, StoryObj } from "@storybook/react";

import { LowStockPartsTable } from "@/components/dashboard/low-stock-parts-table";

const meta: Meta<typeof LowStockPartsTable> = {
  title: "Dashboard/LowStockPartsTable",
  component: LowStockPartsTable,
  args: {
    parts: [
      {
        id: "part-1",
        sku: "BRK-101",
        description: "Brake pads",
        quantity: 3,
        reorderMin: 8,
        suggestedOrder: 13,
      },
      {
        id: "part-2",
        sku: "FLT-210",
        description: "Oil filter",
        quantity: 5,
        reorderMin: 12,
        suggestedOrder: 19,
      },
    ],
  },
};

export default meta;

type Story = StoryObj<typeof LowStockPartsTable>;

export const Default: Story = {};
