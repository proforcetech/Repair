import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";

import { PartItemEditor } from "@/components/estimates/estimate-item-editors";
import { PartItemDraft } from "@/services/estimates";

const meta: Meta<typeof PartItemEditor> = {
  title: "Estimates/PartItemEditor",
  component: PartItemEditor,
};

export default meta;

type Story = StoryObj<typeof PartItemEditor>;

function Wrapper() {
  const [items, setItems] = useState<PartItemDraft[]>([
    {
      kind: "part",
      description: "OEM Brake Pad",
      unitPrice: 65,
      quantity: 2,
      partNumber: "BP-01",
    },
  ]);
  return <PartItemEditor items={items} onChange={setItems} />;
}

export const Default: Story = {
  render: () => <Wrapper />,
};

export const Empty: Story = {
  render: () => {
    const Component = () => {
      const [items, setItems] = useState<PartItemDraft[]>([]);
      return <PartItemEditor items={items} onChange={setItems} />;
    };
    return <Component />;
  },
};
