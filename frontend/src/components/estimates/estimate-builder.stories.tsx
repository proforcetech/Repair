import type { Meta, StoryObj } from "@storybook/react";

import { EstimateBuilder } from "@/components/estimates/estimate-builder";

const meta: Meta<typeof EstimateBuilder> = {
  title: "Estimates/EstimateBuilder",
  component: EstimateBuilder,
  parameters: {
    layout: "centered",
  },
};

export default meta;

type Story = StoryObj<typeof EstimateBuilder>;

export const Empty: Story = {
  args: {
    onSubmit: async () => {},
  },
};

export const WithDefaults: Story = {
  render: (args) => (
    <EstimateBuilder
      {...args}
      onSubmit={async () => {}}
    />
  ),
};
