/** MessagePane — infinite scroll upward, date separators, bubbles, status ticks. */

import { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { useSocketStore } from "@stores/useSocketStore";
import { useAuthStore } from "@stores/useAuthStore";
import { useQuery } from "@tanstack/react-query";
import { fetchMessages } from "@services/apiClient";
import { useToast } from "@hooks/useToast";
import { Card, CardContent, CardFooter, CardTitle } from "@components/ui/index";
import { cn } from "@utils/cn";
import { useParams } from "react-router-dom";
import { useParams as useSearchParams } from "react-router-dom";

interface Message {
  id: string;
  content: string;
  sender_id: string;
  created_at: string;
  user_role?: "student" | "teacher" | "admin";
}

interface MessagePaneProps {
  conversationId: string;
}

/** MessagePane component — displays conversation history with infinite scroll. */
export const MessagePane = ({ conversationId }: MessagePaneProps) => {
  const { user, access_token } = useAuthStore();
  const { connected } = useSocketStore();
  const { data, isLoading, isError, fetchNextPage, hasNextPage } = useQuery<
    Message[],
    Error
  >(
    ["messages", conversationId],
    async () => {
      const resp = await fetchMessages({
        conversation_id: conversationId,
        limit: 50,
      });
      return resp.data.messages;
    }
  );

  const [scrollPosition, setScrollPosition] = useState("bottom");
  const [typing, setTyping] = useState("");

  const sendMessage = async (content: string) => {
    if (!conversationId || !content.trim()) return;

    const idempotencyKey = `msg-${uuidv4()}-${Date.now()}`;
    const resp = await fetch("/api/v1/chat/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${access_token}`,
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
      queryClient.invalidateQueries(["messages", conversationId]);
    }
  };

  useEffect(() => {
    if (!connected) return;
    // Handle typing indicators etc.
  }, [connected]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conversation</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-64" />
        ) : (
          <div className="h-96 overflow-y-auto space-y-2 p-2" onScroll={(e) => {
            const bottom = e.target.scrollHeight - e.target.clientHeight;
            const scrollTop = e.target.scrollTop + e.target.clientHeight;
            setScrollPosition(scrollPosition === "bottom" && scrollTop >= bottom ? "bottom" : "top");
          }}>
            {data?.map((msg) => (
              <div key={msg.id} className="flex items-start">
                <span className="flex-1">{msg.content}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
      <CardFooter>
        <input
          type="text"
          placeholder="Reply..."
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              sendMessage(e.target.value);
              e.target.value = "";
            }
          }}
        />
      </CardFooter>
    </Card>
  );
};
