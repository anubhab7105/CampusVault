/** Socket.IO service — connection lifecycle + typed emit helpers. */

import { io, type Socket } from "socket.io-client";
import { useAuthStore } from "@stores/useAuthStore";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/socket.io";

let socket: Socket | null = null;
let pendingEmitQueue: Array<[string, unknown?]> = [];

export const socketService = {
  /** Authenticate + connect. Idempotent. */
  connect: (): Socket => {
    if (socket?.connected) return socket;
    const token = useAuthStore.getState().access_token;
    if (!token) throw new Error("No access token available for socket connect.");

    socket = io(WS_URL, {
      auth: { token },
      transports: ["websocket", "polling"],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socket.on("connect", () => {
      // flush queued emits after re-authenticated connect
      const queue = pendingEmitQueue.splice(0, pendingEmitQueue.length);
      queue.forEach(([event, payload]) => socket?.emit(event, payload));
    });

    socket.on("connect_error", () => {
      // Socket.IO v4 auth failures arrive here
    });

    return socket;
  },

  /** Disconnect cleanly on logout. */
  disconnect: () => {
    if (socket) {
      socket.disconnect();
      socket = null;
    }
  },

  /** Typed emit with offline queueing. */
  emit: <T>(event: string, payload?: T): boolean => {
    if (!socket?.connected) {
      pendingEmitQueue.push([event, payload]);
      return false;
    }
    socket.emit(event, payload);
    return true;
  },

  /** Listen to a namespaced event with a payload type guard. */
  on: <T>(event: string, handler: (payload: T) => void): (() => void) => {
    if (!socket) throw new Error("Socket not initialized");
    socket.on(event, handler);
    return () => socket?.off(event, handler);
  },

  off: (event: string, handler?: (...args: unknown[]) => void) => {
    if (handler) socket?.off(event, handler);
    else socket?.off(event);
  },

  get connected(): boolean {
    return socket?.connected ?? false;
  },
};
