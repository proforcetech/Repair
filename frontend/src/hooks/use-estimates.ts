"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  EstimateCreateInput,
  EstimateItemCreate,
  EstimateStatus,
  addEstimateItem,
  applyTemplateToEstimate,
  approveEstimate,
  createEstimate,
  duplicateEstimate,
  getEstimate,
  listEstimates,
  rejectEstimate,
  updateEstimateStatus,
} from "@/services/estimates";
import { showToast } from "@/stores/toast-store";

export function useEstimates() {
  return useQuery({
    queryKey: ["estimates"],
    queryFn: listEstimates,
  });
}

export function useEstimate(estimateId: string) {
  return useQuery({
    queryKey: ["estimates", estimateId],
    queryFn: () => getEstimate(estimateId),
    enabled: Boolean(estimateId),
  });
}

export function useCreateEstimate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: EstimateCreateInput) => createEstimate(input),
    onSuccess: (estimate) => {
      queryClient.invalidateQueries({ queryKey: ["estimates"] });
      showToast({
        title: "Estimate created",
        description: `Estimate #${estimate.id} drafted`,
        variant: "success",
      });
    },
    onError: (error: unknown) => {
      showToast({
        title: "Unable to create estimate",
        description:
          typeof error === "object" && error !== null && "message" in error
            ? String((error as { message?: unknown }).message)
            : "Unexpected error", 
        variant: "destructive",
      });
    },
  });
}

export function useEstimateMutations(estimateId: string) {
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["estimates"] });
    if (estimateId) {
      queryClient.invalidateQueries({ queryKey: ["estimates", estimateId] });
    }
  };

  const makeToast = (title: string, description: string, variant: "success" | "destructive" = "success") => {
    showToast({ title, description, variant });
  };

  const statusMutation = useMutation({
    mutationFn: (status: EstimateStatus) => updateEstimateStatus(estimateId, status),
    onSuccess: ({ estimate }) => {
      invalidate();
      const friendlyStatus = estimate.status
        .toLowerCase()
        .replace(/_/g, " ");
      makeToast("Status updated", `Estimate moved to ${friendlyStatus}`);
    },
    onError: (error: unknown) => {
      makeToast(
        "Unable to update status",
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unexpected error",
        "destructive",
      );
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => approveEstimate(estimateId),
    onSuccess: () => {
      invalidate();
      makeToast("Estimate approved", "Customer authorization recorded");
    },
    onError: (error: unknown) => {
      makeToast(
        "Unable to approve estimate",
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unexpected error",
        "destructive",
      );
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectEstimate(estimateId),
    onSuccess: () => {
      invalidate();
      makeToast("Estimate rejected", "Customer has declined the work");
    },
    onError: (error: unknown) => {
      makeToast(
        "Unable to reject estimate",
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unexpected error",
        "destructive",
      );
    },
  });

  const duplicateMutation = useMutation({
    mutationFn: () => duplicateEstimate(estimateId),
    onSuccess: ({ estimate }) => {
      invalidate();
      makeToast("Estimate duplicated", `Draft copy created (#${estimate.id})`);
    },
    onError: (error: unknown) => {
      makeToast(
        "Unable to duplicate estimate",
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unexpected error",
        "destructive",
      );
    },
  });

  const applyTemplateMutation = useMutation({
    mutationFn: (templateId: string) => applyTemplateToEstimate(estimateId, templateId),
    onSuccess: () => {
      invalidate();
      makeToast("Template applied", "Service template merged into estimate");
    },
    onError: (error: unknown) => {
      makeToast(
        "Unable to apply template",
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message)
          : "Unexpected error",
        "destructive",
      );
    },
  });

  return {
    statusMutation,
    approveMutation,
    rejectMutation,
    duplicateMutation,
    applyTemplateMutation,
    invalidate,
  };
}

export function useAddEstimateItem(estimateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (item: EstimateItemCreate) => addItem(estimateId, item),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["estimates", estimateId] });
      showToast({
        title: "Line item added",
        description: "The estimate total has been recalculated",
        variant: "success",
      });
    },
    onError: (error: unknown) => {
      showToast({
        title: "Unable to add line item",
        description:
          typeof error === "object" && error !== null && "message" in error
            ? String((error as { message?: unknown }).message)
            : "Unexpected error",
        variant: "destructive",
      });
    },
  });
}

function addItem(estimateId: string, item: EstimateItemCreate) {
  return addEstimateItem(estimateId, item);
}
