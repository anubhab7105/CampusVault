/** Socket.IO service — connection lifecycle + typed emit helpers. */
import { io } from "socket.io-client";
import { useAuthStore } from "@stores/useAuthStore";
const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/socket.io";
let socket = null;
let pendingEmitQueue = [];
export const socketService = {
    /** Authenticate + connect. Idempotent. */
    connect: () => {
        if (socket?.connected)
            return socket;
        const token = useAuthStore.getState().access_token;
        if (!token)
            throw new Error("No access token available for socket connect.");
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
    emit: (event, payload) => {
        if (!socket?.connected) {
            pendingEmitQueue.push([event, payload]);
            return false;
        }
        socket.emit(event, payload);
        return true;
    },
    /** Listen to a namespaced event with a payload type guard. */
    on: (event, handler) => {
        if (!socket)
            throw new Error("Socket not initialized");
        socket.on(event, handler);
        return () => socket?.off(event, handler);
    },
    off: (event, handler) => {
        if (handler)
            socket?.off(event, handler);
        else
            socket?.off(event);
    },
    get connected() {
        return socket?.connected ?? false;
    },
};
