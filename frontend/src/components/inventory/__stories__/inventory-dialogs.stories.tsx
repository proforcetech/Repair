import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";

import { ConsumePartDialog } from "@/components/inventory/consume-part-dialog";
import { StockTransferDialog } from "@/components/inventory/stock-transfer-dialog";

const samplePart = {
  id: "part-1",
  sku: "ALT-001",
  name: "Alternator",
  description: "Remanufactured alternator",
  quantity: 12,
  reorderMin: 4,
  location: "Main Warehouse",
  vendor: "MotorWorks",
};

const meta: Meta<typeof StockTransferDialog> = {
  title: "Inventory/Dialogs",
  component: StockTransferDialog,
};

export default meta;

type Story = StoryObj<typeof StockTransferDialog>;

export const StockTransfer: Story = {
  render: function Render() {
    const [open, setOpen] = useState(true);
    return (
      <StockTransferDialog
        part={samplePart}
        open={open}
        onOpenChange={setOpen}
        isSubmitting={false}
        onSubmit={async () => {
          console.log("submit transfer");
        }}
      />
    );
  },
};

export const ConsumePart: Story = {
  render: function Render() {
    const [open, setOpen] = useState(true);
    return (
      <ConsumePartDialog
        part={samplePart}
        open={open}
        onOpenChange={setOpen}
        isSubmitting={false}
        onSubmit={async () => {
          console.log("record usage");
        }}
      />
    );
  },
};
