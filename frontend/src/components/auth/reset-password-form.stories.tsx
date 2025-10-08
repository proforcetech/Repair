import type { Meta, StoryObj } from "@storybook/react";
import { userEvent, within } from "@storybook/test";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";

const meta: Meta<typeof ResetPasswordForm> = {
  title: "Auth/ResetPasswordForm",
  component: ResetPasswordForm,
  args: {
    defaultValues: {
      token: "token-from-email",
    },
  },
};

export default meta;

type Story = StoryObj<typeof ResetPasswordForm>;

export const Default: Story = {};

export const ShowsSuccess: Story = {
  args: {
    onSubmit: async () => ({
      status: "success",
      message: "Password updated successfully.",
    }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText(/new password/i), "NewPassword123!");
    await userEvent.type(canvas.getByLabelText(/confirm password/i), "NewPassword123!");
    await userEvent.click(canvas.getByRole("button", { name: /update password/i }));
  },
};

export const ShowsError: Story = {
  args: {
    onSubmit: async () => ({ status: "error", message: "Token expired" }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText(/new password/i), "NewPassword123!");
    await userEvent.type(canvas.getByLabelText(/confirm password/i), "NewPassword123!");
    await userEvent.click(canvas.getByRole("button", { name: /update password/i }));
  },
};
