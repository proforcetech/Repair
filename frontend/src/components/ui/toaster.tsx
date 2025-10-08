"use client";

import { useEffect } from "react";

import { useToastStore } from "@/stores/toast-store";

import {
    Toast,
    ToastClose,
    ToastDescription,
    ToastProvider,
    ToastTitle,
    ToastViewport,
} from "./toast";

export function Toaster() {
    const toasts = useToastStore((state) => state.toasts);
    const updateToast = useToastStore((state) => state.updateToast);
    const dismissToast = useToastStore((state) => state.dismissToast);
    const removeToast = useToastStore((state) => state.removeToast);

    useEffect(() => {
        const timers = toasts
            .filter((toast) => !toast.open)
            .map((toast) =>
                setTimeout(() => {
                    removeToast(toast.id);
                }, 250),
            );

        return () => {
            timers.forEach((timer) => clearTimeout(timer));
        };
    }, [toasts, removeToast]);

    return (
        <ToastProvider swipeDirection="right">
            {toasts.map((toast) => (
                <Toast
                    key={toast.id}
                    variant={toast.variant}
                    open={toast.open}
                    onOpenChange={(open) => {
                        if (!open) {
                            dismissToast(toast.id);
                        } else {
                            updateToast(toast.id, { open: true });
                        }
                    }}
                    duration={toast.duration}
                >
                    {toast.title ? <ToastTitle>{toast.title}</ToastTitle> : null}
                    {toast.description ? <ToastDescription>{toast.description}</ToastDescription> : null}
                    <ToastClose />
                </Toast>
            ))}
            <ToastViewport />
        </ToastProvider>
    );
}