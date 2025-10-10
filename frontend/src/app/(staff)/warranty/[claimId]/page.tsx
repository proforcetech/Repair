"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  assignWarrantyClaim,
  fetchWarrantyClaim,
  fetchWarrantyCommentsAfter,
  postWarrantyComment,
  updateWarrantyClaimStatus,
  WarrantyClaimDetail,
  WarrantyComment,
  WarrantyStatus,
} from "@/services/warranty";
import { useTechnicianOptions } from "@/hooks/use-dashboard-data";
import { showToast } from "@/stores/toast-store";
import { computeSlaBadge, getNextWarrantyStatus, mergeWarrantyComments } from "@/lib/warranty-utils";

function formatDate(value?: string | null) {
  if (!value) {
    return "—";
  }
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return value;
  }
}

function SlaBadge({ detail }: { detail?: WarrantyClaimDetail | null }) {
  const badge = useMemo(
    () => (detail ? computeSlaBadge({ createdAt: detail.claim.createdAt, firstResponseAt: detail.claim.firstResponseAt }) : null),
    [detail?.claim.createdAt, detail?.claim.firstResponseAt],
  );
  if (!badge) {
    return null;
  }

  const toneClass: Record<string, string> = {
    success: "bg-emerald-100 text-emerald-800",
    destructive: "bg-red-100 text-red-700",
    warning: "bg-amber-100 text-amber-800",
    muted: "bg-slate-200 text-slate-700",
  };

  return <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${toneClass[badge.tone]}`}>{badge.label}</span>;
}

export default function WarrantyClaimDetailPage() {
  const params = useParams<{ claimId: string }>();
  const claimId = typeof params.claimId === "string" ? params.claimId : Array.isArray(params.claimId) ? params.claimId[0] : "";
  const queryClient = useQueryClient();

  const detailQuery = useQuery({
    queryKey: ["warranty", "claim", claimId],
    queryFn: () => fetchWarrantyClaim(claimId),
    enabled: Boolean(claimId),
  });

  const [thread, setThread] = useState<WarrantyComment[]>([]);
  const [commentDraft, setCommentDraft] = useState("");
  const technicians = useTechnicianOptions();

  useEffect(() => {
    if (detailQuery.data?.comments) {
      setThread(detailQuery.data.comments);
    }
  }, [detailQuery.data?.comments]);

  const latestTimestamp = thread.at(-1)?.createdAt ?? detailQuery.data?.claim.createdAt ?? null;

  useEffect(() => {
    if (!claimId || !latestTimestamp) {
      return undefined;
    }
    const interval = setInterval(async () => {
      try {
        const updates = await fetchWarrantyCommentsAfter(claimId, latestTimestamp);
        if (updates.length > 0) {
          setThread((current) => mergeWarrantyComments(current, updates));
          showToast({
            title: "New warranty comment",
            description: "A customer has replied on this claim.",
          });
        }
      } catch (error) {
        console.error("Failed to poll comments", error);
      }
    }, 15_000);

    return () => clearInterval(interval);
  }, [claimId, latestTimestamp]);

  const assignMutation = useMutation({
    mutationFn: ({ userId }: { userId: string }) => assignWarrantyClaim(claimId, { userId }),
    onSuccess: () => {
      showToast({ title: "Claim assigned", description: "Assignment saved", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["warranty", "claim", claimId] });
      queryClient.invalidateQueries({ queryKey: ["warranty", "claims"] });
    },
    onError: (error) => {
      const message =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message?: unknown }).message ?? "Unable to assign claim")
          : "Unable to assign claim";
      showToast({ title: "Assignment failed", description: message, variant: "destructive" });
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: WarrantyStatus) => updateWarrantyClaimStatus(claimId, { status }),
    onSuccess: () => {
      showToast({ title: "Status updated", description: "Claim status saved", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["warranty", "claim", claimId] });
      queryClient.invalidateQueries({ queryKey: ["warranty", "claims"] });
    },
    onError: () => {
      showToast({ title: "Update failed", description: "Could not update status", variant: "destructive" });
    },
  });

  const commentMutation = useMutation({
    mutationFn: (message: string) => postWarrantyComment(claimId, message),
    onSuccess: (_, message) => {
      showToast({ title: "Comment sent", description: "Customer will be notified", variant: "success" });
      setCommentDraft("");
      setThread((current) => [
        ...current,
        {
          id: `local-${Date.now()}`,
          claimId,
          message,
          sender: "STAFF",
          createdAt: new Date().toISOString(),
        },
      ]);
    },
    onError: () => {
      showToast({ title: "Comment failed", description: "Unable to send reply", variant: "destructive" });
    },
  });

  if (!claimId) {
    return <p className="text-sm text-destructive">Invalid claim reference.</p>;
  }

  if (detailQuery.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading claim details…</p>;
  }

  if (detailQuery.isError || !detailQuery.data) {
    return <p className="text-sm text-destructive">Unable to load claim detail.</p>;
  }

  const { claim } = detailQuery.data;
  const assignedOption = claim.assignedTo?.id ?? "";

  return (
    <div className="space-y-6">
      <Link href="/warranty" className="inline-flex items-center text-sm font-medium text-primary hover:underline">
        ← Back to triage
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Claim #{claim.id}</h1>
          <p className="text-sm text-muted-foreground">Opened {formatDate(claim.createdAt)}</p>
        </div>
        <SlaBadge detail={detailQuery.data} />
      </header>

      <section className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <div className="space-y-6">
          <article className="rounded-lg border border-border/60 bg-card/80 p-4 text-sm shadow-sm">
            <h2 className="text-lg font-semibold text-foreground">Issue summary</h2>
            <p className="mt-2 whitespace-pre-line text-muted-foreground">{claim.description ?? "No description provided."}</p>
            {claim.attachmentUrl && (
              <a
                href={claim.attachmentUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex items-center text-sm font-medium text-primary hover:underline"
              >
                View attachment
              </a>
            )}
          </article>

          <article className="space-y-4 rounded-lg border border-border/60 bg-card/80 p-4 shadow-sm">
            <header>
              <h2 className="text-lg font-semibold text-foreground">Conversation</h2>
              <p className="text-xs text-muted-foreground">
                Messages appear newest at the bottom. The thread refreshes every 15 seconds.
              </p>
            </header>
            <ul className="space-y-3 text-sm">
              {thread.map((comment) => (
                <li
                  key={comment.id}
                  className={`rounded-md border border-border/40 p-3 ${
                    comment.sender === "STAFF" ? "bg-primary/5 text-foreground" : "bg-amber-50 text-foreground"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{comment.sender === "STAFF" ? "Staff" : "Customer"}</span>
                    <span>{formatDate(comment.createdAt)}</span>
                  </div>
                  <p className="mt-2 whitespace-pre-line text-sm">{comment.message}</p>
                </li>
              ))}
              {thread.length === 0 && (
                <li className="rounded-md border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground">
                  No conversation yet. Send a reply to start the thread.
                </li>
              )}
            </ul>
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!commentDraft.trim()) {
                  return;
                }
                commentMutation.mutate(commentDraft.trim());
              }}
            >
              <label htmlFor="reply" className="text-sm font-medium text-foreground">
                Reply to customer
              </label>
              <textarea
                id="reply"
                value={commentDraft}
                onChange={(event) => setCommentDraft(event.target.value)}
                className="min-h-[120px] w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="Share troubleshooting steps or request more information."
              />
              <button
                type="submit"
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
                disabled={commentMutation.isLoading}
              >
                {commentMutation.isLoading ? "Sending…" : "Send reply"}
              </button>
            </form>
          </article>
        </div>

        <aside className="space-y-4 text-sm">
          <section className="rounded-lg border border-border/60 bg-card/80 p-4 shadow-sm">
            <h2 className="text-base font-semibold text-foreground">Assignment</h2>
            <p className="text-xs text-muted-foreground">Assign the claim to a team member for follow-up.</p>
            <select
              value={assignedOption}
              onChange={(event) => {
                const userId = event.target.value;
                if (!userId) {
                  return;
                }
                assignMutation.mutate({ userId });
              }}
              className="mt-3 w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">Select team member</option>
              {technicians.data?.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </section>

          <section className="space-y-3 rounded-lg border border-border/60 bg-card/80 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-foreground">Status</h2>
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                {claim.status.replace(/_/g, " ")}
              </span>
            </div>
            <div className="space-y-2 text-xs text-muted-foreground">
              <p>Resolution notes: {claim.resolutionNotes ?? "—"}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {["APPROVED", "DENIED", "NEEDS_MORE_INFO", "OPEN"].map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => {
                    const next = getNextWarrantyStatus(claim.status, status);
                    if (next === claim.status && status !== claim.status) {
                      showToast({
                        title: "Status unchanged",
                        description: "Cannot transition directly between approved and denied.",
                        variant: "warning",
                      });
                      return;
                    }
                    statusMutation.mutate(next);
                  }}
                  className="inline-flex flex-1 items-center justify-center rounded-md border border-border/60 px-3 py-1.5 text-xs font-medium text-foreground transition hover:border-primary hover:text-primary"
                  disabled={statusMutation.isLoading}
                >
                  {status.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </section>

          <section className="space-y-2 rounded-lg border border-border/60 bg-card/80 p-4 shadow-sm">
            <h2 className="text-base font-semibold text-foreground">Timeline</h2>
            <dl className="space-y-2 text-xs text-muted-foreground">
              <div className="flex items-center justify-between">
                <dt>Created</dt>
                <dd>{formatDate(claim.createdAt)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt>Updated</dt>
                <dd>{formatDate(claim.updatedAt)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt>First response</dt>
                <dd>{formatDate(claim.firstResponseAt)}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </section>
    </div>
  );
}
