import { create } from "zustand";

type LayoutState = {
    isSidebarOpen: boolean;
    toggleSidebar: () => void;
    closeSidebar: () => void;
};

export const useLayoutStore = create<LayoutState>((set) => ({
    isSidebarOpen: false,
    toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
    closeSidebar: () => set({ isSidebarOpen: false }),
}));