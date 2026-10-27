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
  const [room, setRoom] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Array<{ id: string; content: string; sender_id: string; created_at: string }>>([]);

  useEffect(() => {
    if (!user) return;
    try {
      socketService.connect();
      setConnected(true);
      useSocketStore.getState().connect();
    } catch {
      setConnected(false);
    }
    return () => socketService.disconnect();
  }, [user]);

  useEffect(() => {
    const unsub = socketService.on<{ data: { message: any } }>("send_group_message", (payload) => {
      setMessages((prev) => [...prev, payload.data.message]);
    });
    return () => unsub();
  }, []);

  const joinRoom = (groupId: string) => {
    setRoom(groupId);
    socketService.emit("join_group", { group_id: groupId });
  };

  const sendMessage = () => {
    if (!input.trim() || !room) return;
    socketService.emit("send_group_message", {
      conversation_id: room,
      content: input,
    });
    setInput("");
  };

  if (!connected) {
    return (
      <Card className="h-[400px] flex items-center justify-center">
        <Skeleton className="h-10 w-32" />
      </Card>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <h1 className="text-heading-lg font-semibold text-ink-default mb-6">Chat</h1>
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 h-full">
        <div className="md:col-span-4 flex flex-col h-full border-r border-border">
          <div className="p-4 border-b border-border">
            <h2 className="text-body-md font-semibold text-ink-default">Rooms</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            <Button variant="outline" onClick={() => joinRoom("general")} className="w-full">
              #general
            </Button>
            <Button variant="outline" onClick={() => joinRoom("cs-101")} className="w-full">
              #cs-101
            </Button>
          </div>
        </div>
        <div className="md:col-span-8 flex flex-col h-full">
          <div className="flex h-10 items-center justify-between border-b border-border px-4">
            <span className={cn("text-body-md font-semibold text-ink-default", room ? "" : "text-ink-secondary")}>
              {room ?? "Select a room"}
            </span>
            <span className={`text-caption-xs ${connected ? "text-green-600" : "text-red-600"} font-medium`}>
              {connected ? "● Connected" : "○ Disconnected"}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((m) => (
              <div key={m.id} className={cn("max-w-[80%] rounded-lg p-3 text-sm", m.sender_id === user?.id ? "ml-auto bg-brand text-white" : "mr-auto bg-surface-200 text-ink-default")}>
                <p>{m.content}</p>
                <span className="text-[10px] text-ink-tertiary mt-1 block">{formatRelative(m.created_at)}</span>
              </div>
            ))}
            {messages.length === 0 && <p className="text-caption-xs text-ink-secondary italic">No messages yet.</p>}
          </div>
          <div className="border-t border-border p-4 flex gap-2">
            <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type a message…" disabled={!room} />
            <Button onClick={sendMessage} disabled={!input.trim() || !room} isLoading={!room}>
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
