import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email({ message: "Enter a valid email address" }),
  password: z
    .string()
    .min(8, { message: "Password must be at least 8 characters" })
    .max(128, { message: "Password must be 128 characters or fewer" }),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const twoFactorSchema = z.object({
  token: z
    .string()
    .min(6, { message: "Enter your 6-digit code" })
    .max(10, { message: "Code should be 10 digits or fewer" }),
});

export type TwoFactorFormValues = z.infer<typeof twoFactorSchema>;

export const passwordResetRequestSchema = z.object({
  email: z.string().email({ message: "Enter a valid email address" }),
});

export type PasswordResetRequestValues = z.infer<typeof passwordResetRequestSchema>;

export const passwordResetSchema = z
  .object({
    token: z.string().min(10, { message: "Reset token is required" }),
    password: z
      .string()
      .min(12, { message: "Password must be at least 12 characters" })
      .regex(/^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).+$/, {
        message: "Use upper, lower, and numeric characters",
      }),
    confirmPassword: z.string().min(1, { message: "Confirm your new password" }),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Passwords must match",
    path: ["confirmPassword"],
  });

export type PasswordResetValues = z.infer<typeof passwordResetSchema>;
