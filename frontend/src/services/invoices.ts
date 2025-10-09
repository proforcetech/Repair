import { apiClient, get, post } from "@/lib/api/client";

export type InvoiceStatus =
  | "DRAFT"
  | "SENT"
  | "FINALIZED"
  | "PARTIALLY_PAID"
  | "PAID"
  | "VOID";

export interface InvoicePayment {
  id: string;
  amount: number;
  method: string;
  receivedAt: string;
  runningBalance?: number;
}

export interface InvoiceLineItem {
  id: string;
  description: string;
  quantity: number;
  unitPrice: number;
  cost: number;
}

export interface InvoiceSummary {
  id: string;
  number: string;
  status: InvoiceStatus;
  issuedDate: string | null;
  dueDate: string | null;
  total: number;
  lateFee: number;
  balanceDue: number;
  customer: {
    id: string | null;
    name: string | null;
    email?: string | null;
  };
  payments: InvoicePayment[];
}

export interface InvoiceDetail extends InvoiceSummary {
  subtotal: number;
  tax: number;
  discountTotal: number;
  loyalty: {
    pointsEarned: number;
    customerBalance: number;
  };
  items: InvoiceLineItem[];
}

export interface ManualPaymentInput {
  amount: number;
  method: string;
}

export interface InvoiceMargin {
  invoiceId: string;
  total_cost: number;
  total_price: number;
  gross_margin_percent: number;
  threshold: number;
  is_below_threshold: boolean;
}

export interface InvoiceMarginAnalytics {
  averageMarginPercent: number;
  lowMarginInvoices: number;
  threshold: number;
  series: Array<{
    invoiceId: string;
    number: string;
    customer: string | null;
    finalizedAt: string | null;
    grossMarginPercent: number;
    isBelowThreshold: boolean;
  }>;
}

export async function listInvoices(): Promise<InvoiceSummary[]> {
  return get<InvoiceSummary[]>("/invoice");
}

export async function getInvoice(invoiceId: string): Promise<InvoiceDetail> {
  return get<InvoiceDetail>(`/invoice/${invoiceId}`);
}

export async function finalizeInvoice(invoiceId: string) {
  return post(`/invoice/${invoiceId}/finalize`);
}

export async function recordManualPayment(invoiceId: string, payload: ManualPaymentInput) {
  return post<InvoiceDetail>(`/invoice/${invoiceId}/pay`, payload);
}

export async function createStripeCheckout(invoiceId: string): Promise<{ checkout_url: string }> {
  return post<{ checkout_url: string }>(`/invoice/${invoiceId}/pay/online`);
}

export async function downloadInvoicePdf(invoiceId: string): Promise<Blob> {
  const response = await apiClient.get(`/invoice/${invoiceId}/pdf`, { responseType: "blob" });
  return response.data as Blob;
}

export async function getInvoiceMargin(invoiceId: string): Promise<InvoiceMargin> {
  return get<InvoiceMargin>(`/invoice/${invoiceId}/margin`);
}

export async function getInvoiceMarginAnalytics(): Promise<InvoiceMarginAnalytics> {
  return get<InvoiceMarginAnalytics>("/invoice/analytics/margin");
}
