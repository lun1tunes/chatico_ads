import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { DEFAULT_CONNECTED_IDS } from '../data/mockAccounts';

export const PLATFORMS = {
  META: 'meta',
  GOOGLE: 'google',
  TIKTOK: 'tiktok',
};

export const useAppStore = create(
  persist(
    (set) => ({
      user: { id: 'demo', name: 'Демо-пользователь' },
      token: 'demo-token',
      selectedPlatform: PLATFORMS.META,
      connectedAccountIds: DEFAULT_CONNECTED_IDS,
      selectedAccountId: 'acc_001',
      connectModalOpen: false,
      sidebarCollapsed: false,
      // По умолчанию чат закреплён открытым на широких экранах, свёрнут на узких
      aiPanelOpen: typeof window !== 'undefined' ? window.innerWidth >= 1280 : true,

      setPlatform: (platform) => set({ selectedPlatform: platform }),
      setAccount: (id) => set({ selectedAccountId: id }),
      connectAccount: (id, { activate = false } = {}) =>
        set((state) => ({
          connectedAccountIds: state.connectedAccountIds.includes(id)
            ? state.connectedAccountIds
            : [...state.connectedAccountIds, id],
          selectedAccountId: activate ? id : state.selectedAccountId,
        })),
      disconnectAccount: (id) =>
        set((state) => {
          const remaining = state.connectedAccountIds.filter((x) => x !== id);
          return {
            connectedAccountIds: remaining,
            selectedAccountId:
              state.selectedAccountId === id
                ? remaining[0] ?? null
                : state.selectedAccountId,
          };
        }),
      openConnectModal: () => set({ connectModalOpen: true }),
      closeConnectModal: () => set({ connectModalOpen: false }),
      login: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      openAiPanel: () => set({ aiPanelOpen: true }),
      closeAiPanel: () => set({ aiPanelOpen: false }),
      toggleAiPanel: () => set((state) => ({ aiPanelOpen: !state.aiPanelOpen })),
    }),
    {
      name: 'chatico-ads-store',
      partialize: (state) => ({
        selectedPlatform: state.selectedPlatform,
        connectedAccountIds: state.connectedAccountIds,
        selectedAccountId: state.selectedAccountId,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    },
  ),
);
