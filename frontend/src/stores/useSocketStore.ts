/** Socket store — Socket.IO client lifecycle. */

import { create } from "zustand";
import { socketService } from "@services/socketService";

export interface SocketState {
  connected: boolean;
  connecting: boolean;
  connect: () => void;
  disconnect: () => void;
}

export const useSocketStore = create<SocketState>((set) => ({
  connected: false,
  connecting: false,

  connect: () => {
    if (socketService.connected) return;
    set({ connecting: true });
    try {
      socketService.connect();
      const unsub = socketService.on("connect", () => {
        set({ connected: true, connecting: false });
        unsub();
      });
      socketService.on("disconnect", () => set({ connected: false, connecting: false }));
    } catch {
      set({ connecting: false });
    }
  },

  disconnect: () => {
    socketService.disconnect();
    set({ connected: false, connecting: false });
  },
}));
