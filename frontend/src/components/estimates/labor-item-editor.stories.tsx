import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";

import { LaborItemEditor } from "@/components/estimates/estimate-item-editors";
import { LaborItemDraft } from "@/services/estimates";

const meta: Meta<typeof LaborItemEditor> = {
  title: "Estimates/LaborItemEditor",
  component: LaborItemEditor,
};

export default meta;

type Story = StoryObj<typeof LaborItemEditor>;

type WrapperProps = {
  initial: LaborItemDraft[];
};

function Wrapper({ initial }: WrapperProps) {
  const [items, setItems] = useState(initial);
  return <LaborItemEditor items={items} onChange={setItems} />;
}

export const Empty: Story = {
  render: () => <Wrapper initial={[]} />,
};

export const Prefilled: Story = {
  render: () => (
    <Wrapper
      initial={[
        { kind: "labor", description: "Initial inspection", hours: 1.5, rate: 110 },
        { kind: "labor", description: "Brake adjustment", hours: 1, rate: 120 },
      ]}
    />
  ),
};
