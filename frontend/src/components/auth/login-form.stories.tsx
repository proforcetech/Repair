import type { Meta, StoryObj } from "@storybook/react";
import { userEvent, within } from "@storybook/test";

import { LoginForm } from "@/components/auth/login-form";

const meta: Meta<typeof LoginForm> = {
  title: "Auth/LoginForm",
  component: LoginForm,
};

export default meta;

type Story = StoryObj<typeof LoginForm>;

export const Default: Story = {};

export const ShowsServerError: Story = {
  args: {
    onSubmit: async () => ({
      status: "error",
      message: "Invalid credentials",
    }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText(/email address/i), "wrong@example.com");
    await userEvent.type(canvas.getByLabelText(/password/i), "badpass123");
    await userEvent.click(canvas.getByRole("button", { name: /sign in/i }));
  },
};

export const TwoFactorPrompt: Story = {
  args: {
    onSubmit: async () => ({
      status: "twoFactor",
      message: "Two-factor authentication required",
    }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText(/email address/i), "user@example.com");
    await userEvent.type(canvas.getByLabelText(/password/i), "SuperSecure123!");
    await userEvent.click(canvas.getByRole("button", { name: /sign in/i }));
  },
};
