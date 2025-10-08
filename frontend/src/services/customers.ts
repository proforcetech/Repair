import { get, post, put } from "@/lib/api/client";

export type Customer = {
  id: string;
  fullName: string;
  email: string;
  phone: string;
  street?: string | null;
  city?: string | null;
  state?: string | null;
  zip?: string | null;
  preferredTechnicianId?: string | null;
  loyaltyPoints?: number;
  visits?: number;
  createdAt?: string;
  updatedAt?: string;
};

export type Vehicle = {
  id: string;
  vin: string;
  make: string;
  model: string;
  year: number;
  archived?: boolean;
  createdAt?: string;
  lastServiceMileage?: number | null;
};

export type EstimateSummary = {
  id: string;
  status?: string | null;
  total?: number | null;
  createdAt?: string;
};

export type InvoiceSummary = {
  id: string;
  total?: number | null;
  status?: string | null;
  createdAt?: string;
};

export type WarrantyClaimSummary = {
  id: string;
  status: string;
  workOrderId?: string | null;
  createdAt?: string;
  resolutionNotes?: string | null;
  invoiceTotal?: number | null;
};

export type AppointmentSummary = {
  id: string;
  startTime?: string | null;
  status?: string | null;
  serviceType?: string | null;
};

export type CustomerProfile = {
  vehicles: Vehicle[];
  invoices: InvoiceSummary[];
  warrantyClaims: WarrantyClaimSummary[];
  appointments: AppointmentSummary[];
};

export type CustomerSearchFilters = {
  name?: string;
  email?: string;
  phone?: string;
};

export type CustomerCreateInput = {
  fullName: string;
  email: string;
  phone: string;
  street?: string | null;
  city?: string | null;
  state?: string | null;
  zip?: string | null;
};

export type CustomerUpdateInput = Partial<CustomerCreateInput>;

export type VehicleCreateInput = {
  vin: string;
  make: string;
  model: string;
  year: number;
};

export type VehicleUpdateInput = Partial<VehicleCreateInput>;

export async function searchCustomers(filters: CustomerSearchFilters = {}) {
  return get<Customer[]>("/customers", {
    params: filters,
  });
}

export async function getCustomer(customerId: string) {
  return get<Customer>(`/customers/${customerId}`);
}

export async function getCustomerProfile(customerId: string) {
  return get<CustomerProfile>(`/customers/${customerId}/profile`);
}

export async function createCustomer(input: CustomerCreateInput) {
  return post<Customer>("/customers", input);
}

export async function updateCustomer(customerId: string, input: CustomerUpdateInput) {
  return put<Customer>(`/customers/${customerId}`, input);
}

export async function createVehicle(customerId: string, input: VehicleCreateInput) {
  return post<Vehicle>(`/customers/${customerId}/vehicles`, input);
}

export async function updateVehicle(vehicleId: string, input: VehicleUpdateInput) {
  return put<Vehicle>(`/vehicles/${vehicleId}`, input);
}

export async function getCustomerVehicles(customerId: string) {
  return get<Vehicle[]>(`/customers/${customerId}/vehicles`);
}

export async function getCustomerDashboard() {
  return get<{
    estimates: EstimateSummary[];
    invoices: InvoiceSummary[];
    vehicles: Vehicle[];
    appointments: AppointmentSummary[];
  }>("/customers/dashboard");
}

export async function getCustomerSelf() {
  return get<Customer>("/customers/me");
}

export async function updateCustomerSelf(input: CustomerUpdateInput) {
  return put<{ message: string; customer: Customer }>("/customers/me", input);
}

export async function getWarrantyHistory() {
  return get<WarrantyClaimSummary[]>("/customers/me/warranty");
}
