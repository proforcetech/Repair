"use client";

import * as ToastPrimitives from "@radix-ui/react-toast";
import { clsx } from "clsx";
import { ComponentPropsWithoutRef, ElementRef, forwardRef } from "react";

const toastVariants = {
    default: "border border-border bg-card text-card-foreground shadow-brand",
    success: "border border-emerald-200/60 bg-emerald-50 text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/60 dark:text-emerald-100",
    warning: "border border-amber-200/60 bg-amber-50 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/60 dark:text-amber-100",
    destructive: "border border-destructive/50 bg-destructive text-destructive-foreground",
} as const;

export const ToastProvider = ToastPrimitives.Provider;

export const ToastViewport = forwardRef<
    ElementRef<typeof ToastPrimitives.Viewport>,
    ComponentPropsWithoutRef<typeof ToastPrimitives.Viewport>
>(({ className, ...props }, ref) => (
    <ToastPrimitives.Viewport
        ref={ref}
        className={clsx(
            "fixed right-0 top-0 z-[100] flex max-h-screen w-full flex-col gap-3 overflow-y-auto p-4 sm:top-2 sm:right-2 sm:w-96",
            className,
        )}
        {...props}
    />
));
ToastViewport.displayName = ToastPrimitives.Viewport.displayName;

export const Toast = forwardRef<
    ElementRef<typeof ToastPrimitives.Root>,
    ComponentPropsWithoutRef<typeof ToastPrimitives.Root> & {
        variant?: keyof typeof toastVariants;
    }
>(({ className, variant = "default", ...props }, ref) => (
    <ToastPrimitives.Root
        ref={ref}
        className={clsx(
            "group relative grid w-full gap-1 rounded-lg border px-4 py-3 shadow-lg transition-all duration-200 data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=end]:opacity-0 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-100 data-[state=open]:slide-in-from-top-full sm:data-[state=open]:slide-in-from-right-full",
            toastVariants[variant],
            className,
        )}
        {...props}
    />
));
Toast.displayName = ToastPrimitives.Root.displayName;

export const ToastTitle = forwardRef<
    ElementRef<typeof ToastPrimitives.Title>,
    ComponentPropsWithoutRef<typeof ToastPrimitives.Title>
>(({ className, ...props }, ref) => (
    <ToastPrimitives.Title
        ref={ref}
        className={clsx("text-sm font-semibold leading-none tracking-tight", className)}
        {...props}
    />
));
ToastTitle.displayName = ToastPrimitives.Title.displayName;

export const ToastDescription = forwardRef<
    ElementRef<typeof ToastPrimitives.Description>,
    ComponentPropsWithoutRef<typeof ToastPrimitives.Description>
>(({ className, ...props }, ref) => (
    <ToastPrimitives.Description
        ref={ref}
        className={clsx("text-sm text-muted-foreground", className)}
        {...props}
    />
));
ToastDescription.displayName = ToastPrimitives.Description.displayName;

export const ToastClose = forwardRef<
    ElementRef<typeof ToastPrimitives.Close>,
    ComponentPropsWithoutRef<typeof ToastPrimitives.Close>
>(({ className, ...props }, ref) => (
    <ToastPrimitives.Close
        ref={ref}
        className={clsx(
            "absolute right-2 top-2 rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
            className,
        )}
        {...props}
    />
));
ToastClose.displayName = ToastPrimitives.Close.displayName;