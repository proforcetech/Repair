import type { Meta, StoryObj } from "@storybook/react";
import { userEvent, within } from "@storybook/test";

import { TwoFactorForm } from "@/components/auth/two-factor-form";

const meta: Meta<typeof TwoFactorForm> = {
  title: "Auth/TwoFactorForm",
  component: TwoFactorForm,
};

export default meta;

type Story = StoryObj<typeof TwoFactorForm>;

export const Default: Story = {};

export const WithInvalidCode: Story = {
  args: {
    onSubmit: async () => ({ status: "error", message: "Incorrect code" }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText(/one-time passcode/i), "123456");
    await userEvent.click(canvas.getByRole("button", { name: /verify/i }));
  },
};
