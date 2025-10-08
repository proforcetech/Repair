import { create } from "zustand";

type AuthTokens = {
    accessToken?: string | null;
    refreshToken?: string | null;
};

type AuthState = AuthTokens & {
    setTokens: (tokens: AuthTokens) => void;
    clear: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
    accessToken: null,
    refreshToken: null,
    setTokens: (tokens) =>
        set(() => ({
            accessToken: tokens.accessToken ?? null,
            refreshToken: tokens.refreshToken ?? null,
        })),
    clear: () => set({ accessToken: null, refreshToken: null }),
}));

export const getAccessToken = () => useAuthStore.getState().accessToken;
export const getRefreshToken = () => useAuthStore.getState().refreshToken;
export const setAuthTokens = (tokens: AuthTokens) => useAuthStore.getState().setTokens(tokens);
export const clearAuthTokens = () => useAuthStore.getState().clear();