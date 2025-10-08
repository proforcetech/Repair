import type { Meta, StoryObj } from "@storybook/react";
import { userEvent, within } from "@storybook/test";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

const meta: Meta<typeof ForgotPasswordForm> = {
  title: "Auth/ForgotPasswordForm",
  component: ForgotPasswordForm,
};

export default meta;

type Story = StoryObj<typeof ForgotPasswordForm>;

export const Default: Story = {};

export const ShowsConfirmation: Story = {
  args: {
    onSubmit: async () => ({ status: "success", message: "Email sent" }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText(/email address/i), "driver@example.com");
    await userEvent.click(canvas.getByRole("button", { name: /send reset link/i }));
  },
};

export const DisplaysError: Story = {
  args: {
    onSubmit: async () => ({ status: "error", message: "Unable to send email" }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText(/email address/i), "driver@example.com");
    await userEvent.click(canvas.getByRole("button", { name: /send reset link/i }));
  },
};
