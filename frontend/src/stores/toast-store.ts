import { create } from "zustand";

export type ToastVariant = "default" | "success" | "warning" | "destructive";

export type AppToast = {
    id: string;
    title?: string;
    description?: string;
    duration?: number;
    variant?: ToastVariant;
    open: boolean;
};

type ToastStore = {
    toasts: AppToast[];
    addToast: (toast: Omit<AppToast, "id" | "open"> & { id?: string }) => string;
    updateToast: (id: string, toast: Partial<AppToast>) => void;
    dismissToast: (id?: string) => void;
    removeToast: (id: string) => void;
};

export const useToastStore = create<ToastStore>((set, get) => ({
    toasts: [],
    addToast: (toast) => {
        const id = toast.id ?? globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2);
        const nextToast: AppToast = {
            id,
            open: true,
            duration: toast.duration ?? 5000,
            variant: toast.variant ?? "default",
            title: toast.title,
            description: toast.description,
        };

        set((state) => ({
            toasts: [...state.toasts.filter((item) => item.id !== id), nextToast],
        }));

        return id;
    },
    updateToast: (id, toast) => {
        set((state) => ({
            toasts: state.toasts.map((item) =>
                item.id === id
                    ? {
                        ...item,
                        ...toast,
                    }
                    : item,
            ),
        }));
    },
    dismissToast: (id) => {
        if (!id) {
            const last = [...get().toasts].pop();
            if (!last) return;
            id = last.id;
        }

        set((state) => ({
            toasts: state.toasts.map((item) =>
                item.id === id
                    ? {
                        ...item,
                        open: false,
                    }
                    : item,
            ),
        }));
    },
    removeToast: (id) => {
        set((state) => ({
            toasts: state.toasts.filter((item) => item.id !== id),
        }));
    },
}));

export const showToast = (toast: Omit<AppToast, "id" | "open"> & { id?: string }) =>
    useToastStore.getState().addToast(toast);

export const dismissToast = (id?: string) => useToastStore.getState().dismissToast(id);