import type { Meta, StoryObj } from "@storybook/react";

import { PartCatalogTable } from "@/components/inventory/part-catalog-table";

const meta: Meta<typeof PartCatalogTable> = {
  title: "Inventory/PartCatalogTable",
  component: PartCatalogTable,
  args: {
    parts: [
      {
        id: "part-1",
        sku: "ALT-001",
        name: "Alternator",
        description: "Remanufactured alternator",
        quantity: 8,
        reorderMin: 5,
        location: "Main Warehouse",
        vendor: "MotorWorks",
      },
      {
        id: "part-2",
        sku: "BAT-220",
        name: "Battery",
        description: "AGM battery",
        quantity: 2,
        reorderMin: 4,
        location: "Truck #3",
        vendor: "VoltCo",
      },
    ],
  },
};

export default meta;

type Story = StoryObj<typeof PartCatalogTable>;

export const Default: Story = {};

export const Loading: Story = {
  args: {
    isLoading: true,
    parts: [],
  },
};

export const WithActions: Story = {
  args: {
    onTransfer: () => console.log("transfer"),
    onConsume: () => console.log("consume"),
  },
};
