import { z } from "zod";

export const customerCreateSchema = z.object({
  fullName: z.string().min(1, "Full name is required"),
  email: z.string().email("Enter a valid email address"),
  phone: z.string().min(7, "Phone number is required"),
  street: z
    .string()
    .trim()
    .optional()
    .transform((value) => (value === "" ? undefined : value)),
  city: z
    .string()
    .trim()
    .optional()
    .transform((value) => (value === "" ? undefined : value)),
  state: z
    .string()
    .trim()
    .optional()
    .transform((value) => (value === "" ? undefined : value)),
  zip: z
    .string()
    .trim()
    .optional()
    .transform((value) => (value === "" ? undefined : value)),
});

export const customerUpdateSchema = customerCreateSchema.partial();

export type CustomerFormValues = z.infer<typeof customerCreateSchema>;
export type CustomerUpdateValues = z.infer<typeof customerUpdateSchema>;

export const vehicleSchema = z.object({
  vin: z
    .string()
    .min(5, "VIN must be at least 5 characters long")
    .max(32, "VIN must be shorter than 32 characters"),
  make: z.string().min(1, "Make is required"),
  model: z.string().min(1, "Model is required"),
  year: z
    .number({ invalid_type_error: "Year must be a number" })
    .int("Year must be a whole number")
    .gte(1950, "Year must be 1950 or later")
    .lte(new Date().getFullYear() + 1, "Year appears to be invalid"),
});

export const vehicleUpdateSchema = vehicleSchema.partial();

export type VehicleFormValues = z.infer<typeof vehicleSchema>;
export type VehicleUpdateValues = z.infer<typeof vehicleUpdateSchema>;
