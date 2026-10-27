import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/** Chat placeholder — Socket.IO rooms + real-time message list. */
import { useEffect, useState } from "react";
import { socketService } from "@services/socketService";
import { useAuthStore } from "@stores/useAuthStore";
import { useSocketStore } from "@stores/useSocketStore";
import { Card, Input, Button, Skeleton } from "@components/ui/index";
import { cn } from "@utils/cn";
import { formatRelative } from "@utils/datetime";
export default function Chat() {
    const { user } = useAuthStore();
    const [connected, setConnected] = useState(socketService.connected);
    const [room, setRoom] = useState(null);
    const [input, setInput] = useState("");
    const [messages, setMessages] = useState([]);
    useEffect(() => {
        if (!user)
            return;
        try {
            socketService.connect();
            setConnected(true);
            useSocketStore.getState().connect();
        }
        catch {
            setConnected(false);
        }
        return () => socketService.disconnect();
    }, [user]);
    useEffect(() => {
        const unsub = socketService.on("send_group_message", (payload) => {
            setMessages((prev) => [...prev, payload.data.message]);
        });
        return () => unsub();
    }, []);
    const joinRoom = (groupId) => {
        setRoom(groupId);
        socketService.emit("join_group", { group_id: groupId });
    };
    const sendMessage = () => {
        if (!input.trim() || !room)
            return;
        socketService.emit("send_group_message", {
            conversation_id: room,
            content: input,
        });
        setInput("");
    };
    if (!connected) {
        return (_jsx(Card, { className: "h-[400px] flex items-center justify-center", children: _jsx(Skeleton, { className: "h-10 w-32" }) }));
    }
    return (_jsxs("div", { className: "flex flex-col h-full", children: [_jsx("h1", { className: "text-heading-lg font-semibold text-ink-default mb-6", children: "Chat" }), _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-12 gap-6 h-full", children: [_jsxs("div", { className: "md:col-span-4 flex flex-col h-full border-r border-border", children: [_jsx("div", { className: "p-4 border-b border-border", children: _jsx("h2", { className: "text-body-md font-semibold text-ink-default", children: "Rooms" }) }), _jsxs("div", { className: "flex-1 overflow-y-auto p-2 space-y-2", children: [_jsx(Button, { variant: "outline", onClick: () => joinRoom("general"), className: "w-full", children: "#general" }), _jsx(Button, { variant: "outline", onClick: () => joinRoom("cs-101"), className: "w-full", children: "#cs-101" })] })] }), _jsxs("div", { className: "md:col-span-8 flex flex-col h-full", children: [_jsxs("div", { className: "flex h-10 items-center justify-between border-b border-border px-4", children: [_jsx("span", { className: cn("text-body-md font-semibold text-ink-default", room ? "" : "text-ink-secondary"), children: room ?? "Select a room" }), _jsx("span", { className: `text-caption-xs ${connected ? "text-green-600" : "text-red-600"} font-medium`, children: connected ? "● Connected" : "○ Disconnected" })] }), _jsxs("div", { className: "flex-1 overflow-y-auto p-4 space-y-3", children: [messages.map((m) => (_jsxs("div", { className: cn("max-w-[80%] rounded-lg p-3 text-sm", m.sender_id === user?.id ? "ml-auto bg-brand text-white" : "mr-auto bg-surface-200 text-ink-default"), children: [_jsx("p", { children: m.content }), _jsx("span", { className: "text-[10px] text-ink-tertiary mt-1 block", children: formatRelative(m.created_at) })] }, m.id))), messages.length === 0 && _jsx("p", { className: "text-caption-xs text-ink-secondary italic", children: "No messages yet." })] }), _jsxs("div", { className: "border-t border-border p-4 flex gap-2", children: [_jsx(Input, { value: input, onChange: (e) => setInput(e.target.value), placeholder: "Type a message\u2026", disabled: !room }), _jsx(Button, { onClick: sendMessage, disabled: !input.trim() || !room, isLoading: !room, children: "Send" })] })] })] })] }));
}
