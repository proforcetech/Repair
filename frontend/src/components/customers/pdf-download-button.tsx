"use client";

import { ReactNode, useCallback, useMemo, useState } from "react";

import { showToast } from "@/stores/toast-store";

type PdfDownloadButtonProps = {
  href: string;
  filename?: string;
  children?: ReactNode;
};

function parseFileName(contentDisposition: string | null, fallback?: string) {
  if (!contentDisposition) {
    return fallback ?? "document.pdf";
  }

  const match = /filename\*=UTF-8''(?<encoded>[^;]+)|filename="?(?<simple>[^";]+)"?/i.exec(contentDisposition);
  if (!match) {
    return fallback ?? "document.pdf";
  }

  if (match.groups?.encoded) {
    try {
      return decodeURIComponent(match.groups.encoded);
    } catch (error) {
      console.warn("Failed to decode filename", error);
    }
  }

  if (match.groups?.simple) {
    return match.groups.simple;
  }

  return fallback ?? "document.pdf";
}

export function PdfDownloadButton({ href, filename, children }: PdfDownloadButtonProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const label = useMemo(() => {
    if (isDownloading && progress !== null) {
      return `Downloading… ${progress}%`;
    }
    if (isDownloading) {
      return "Downloading…";
    }
    return children ?? "Download PDF";
  }, [children, isDownloading, progress]);

  const handleDownload = useCallback(async () => {
    setIsDownloading(true);
    setProgress(0);
    setError(null);

    try {
      const response = await fetch(href, { method: "GET" });
      if (!response.ok) {
        throw new Error(`Failed to download (${response.status})`);
      }

      const lengthHeader = response.headers.get("Content-Length");
      const total = lengthHeader ? Number.parseInt(lengthHeader, 10) : 0;
      const resolvedFilename = parseFileName(response.headers.get("Content-Disposition"), filename);

      if (!response.body) {
        const blob = await response.blob();
        triggerDownload(blob, resolvedFilename);
        setProgress(100);
        setIsDownloading(false);
        showToast({
          title: "Download ready",
          description: `${resolvedFilename} downloaded successfully`,
          variant: "success",
        });
        return;
      }

      const reader = response.body.getReader();
      const chunks: Uint8Array[] = [];
      let received = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value) {
          chunks.push(value);
          received += value.length;
          if (total > 0) {
            setProgress(Math.min(100, Math.round((received / total) * 100)));
          }
        }
      }

      const blob = new Blob(chunks, { type: "application/pdf" });
      triggerDownload(blob, resolvedFilename);
      setProgress(100);
      showToast({
        title: "Download ready",
        description: `${resolvedFilename} downloaded successfully`,
        variant: "success",
      });
    } catch (downloadError) {
      console.error(downloadError);
      const message =
        downloadError instanceof Error ? downloadError.message : "Unable to download document";
      setError(message);
      showToast({
        title: "Download failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsDownloading(false);
    }
  }, [filename, href]);

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={handleDownload}
        className="inline-flex items-center justify-center rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        disabled={isDownloading}
      >
        {label}
      </button>
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}

function triggerDownload(blob: Blob, filename: string) {
  const blobUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(blobUrl);
}
