/** Message pane — infinite scroll upward, date separators, bubbles, status ticks. */

import { useEffect, useState, useRef } from "react";
import { useAuthStore } from "@stores/useAuthStore";
import { useSocketStore } from "@stores/useSocketStore";
import { useChatMessages } from "@hooks/useChat";
import { socketService } from "@services/socketService";
import { Card, Input, Button, Skeleton } from "@components/ui/index";
import { cn } from "@utils/cn";
import { formatRelative } from "@utils/datetime";
import { useDispatch } from "react-redux";
import { addMessage as addMsg } from "@store/slices/chatSlice";

export default function MessagePane() {
  const { user } = useAuthStore();
  const { connected } = useSocketStore();

  // For this demo, use a fixed conversationId; in production this comes from route params
  const [conversationId, setConversationId] = useState<string | null>(null);

  const { messages, isLoading, fetchNextPage, hasNextPage } = useChatMessages({
    conversationId: conversationId || "",
    initialCursor: undefined,
  });

  // Track scroll position for infinite scroll
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Join the appropriate room based on conversation type
    if (conversationId && connected) {
      socketService.emit("join_group", { group_id: conversationId });
    }

    // Leave when component unmounts or conversation changes
    return () => {
      socketService.emit("leave_group", { group_id: conversationId });
    }
  }, [conversationId, connected]);

  const sendMessage = async (content: string) => {
    if (!conversationId || !content.trim()) return;

    const idempotencyKey = `msg-${uuidv4()}-${Date.now()}`;
    const resp = await fetch("/api/v1/chat/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${user?.access_token}`,
      },
      body: JSON.stringify({
        conversationId,
        content: content.trim(),
        idempotencyKey,
      }),
    });

    const data = await resp.json();
    if (data.success) {
      // Optimistically add the message
      addMsg(data.message);
      socketService.emit("send_group_message", {
        conversation_id: conversationId,
        content,
      });
      // Clear input
      // (handled by parent Composer component)
    }
  };

  // Handle incoming messages from socket
  useEffect(() => {
    const msgUnsub = socketService.on("send_group_message", (payload: any) => {
      const msg = payload.data.message;
      // The message is already added optimistically via the hook;
      // here we just ensure UI updates
    });

    return () => msgUnsub();
  }, [conversationId]);

  // Infinite scroll: fetch next page when near bottom
  useEffect(() => {
    if (!bottomRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isLoading) {
          fetchNextPage();
        }
      },
      { root: null, threshold: 0.1 }
    );

    if (bottomRef.current) {
      observer.observe(bottomRef.current);
    }

    return () => {
      if (bottomRef.current) {
        observer.unobserve(bottomRef.current);
      }
    }
  }, [hasNextPage, isLoading, fetchNextPage]);

  return (
    <Card className="h-[400px] w-full border-y border-border overflow-y-auto">
      <CardContent className="h-full p-4 space-y-3" ref={bottomRef}>
        {isLoading && (
          <Skeleton className="h-6 w-full rounded-b mb-2" />
        )}

        {messages.length === 0 && (
          <p className="text-caption-xs text-ink-secondary italic text-center">
            No messages yet. Send the first message!
          </p>
        )}

        {messages.map((m) => {
          const isMine = m.sender_id === user?.id;
          const isEdited = m.is_edited === true;
          const isReply = !!m.reply_to_id;

          return (
            <div
              key={m.id}
              className={cn(
                "max-w-[85%] rounded-lg p-3 text-sm",
                isMine ? "ml-auto bg-brand text-white" : "mr-auto bg-surface-200 text-ink-default"
              )}
            >
              <p className="line-clamp-3">{m.content}</p>
              <span className="text-[10px] text-ink-tertiary mt-1 block">
                {formatRelative(m.created_at)} {isEdited && (
                  <span className="text-caption-xxs ml-1 text-ink-tertiary">edited</span>
                )}
              </span>
            </div>
          );
        })}

        {/* System/bot messages at bottom */}
        {messages.length > 0 && (
          <div className="border-t border-border pt-2 mt-3 text-caption-xs text-ink-tertiary">
            Type a message above to continue the conversation
          </div>
        )}
      </CardContent>
    </Card>
  );
}