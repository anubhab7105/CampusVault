/** Message pane — message history, status, and reply composition. */

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient, fetchMessages } from "@services/apiClient";
import { useSocketStore } from "@stores/useSocketStore";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, Skeleton } from "@components/ui/index";

interface Message {
  id: string;
  content: string;
  sender_id: string | null;
  created_at: string | null;
  user_role?: "student" | "teacher" | "admin";
}

interface MessagePaneProps {
  conversationId: string;
}

/** Displays conversation history and sends replies. */
export const MessagePane = ({ conversationId }: MessagePaneProps) => {
  const { connected } = useSocketStore();
  const queryClient = useQueryClient();
  const [scrollPosition, setScrollPosition] = useState<"bottom" | "top">("bottom");

  const { data, isLoading } = useQuery({
    queryKey: ["messages", conversationId],
    enabled: Boolean(conversationId),
    queryFn: async (): Promise<Message[]> => {
      const response = await fetchMessages({
        conversation_id: conversationId,
        limit: 50,
      });
      return response.data.messages as Message[];
    },
  });

  const sendMessage = async (content: string) => {
    if (!conversationId || !content.trim()) return;

    const response = await apiClient.post<{ success?: boolean }>(
      `/chat/conversations/${encodeURIComponent(conversationId)}/messages`,
      {
        conversation_id: conversationId,
        content: content.trim(),
        reply_to_id: null,
      },
    );

    const result = response.data;
    if (result.success) {
      await queryClient.invalidateQueries({
        queryKey: ["messages", conversationId],
      });
    }
  };

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Conversation</CardTitle>
        <span className="text-caption-xs text-ink-tertiary">
          {connected ? "Connected" : "Disconnected"}
        </span>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-64" />
        ) : (
          <div
            className="h-96 overflow-y-auto space-y-2 p-2"
            onScroll={(event) => {
              const element = event.currentTarget;
              const atBottom = element.scrollHeight - element.clientHeight <= element.scrollTop + 1;
              setScrollPosition(atBottom ? "bottom" : "top");
            }}
            data-scroll-position={scrollPosition}
          >
            {data?.map((message) => (
              <div key={message.id} className="flex items-start">
                <span className="flex-1">{message.content}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
      <CardFooter>
        <input
          type="text"
          placeholder="Reply..."
          aria-label="Reply"
          className="w-full rounded-md border border-border bg-transparent px-3 py-2"
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              const input = event.currentTarget;
              const content = input.value;
              void sendMessage(content)
                .then(() => {
                  input.value = "";
                })
                .catch(() => {
                  // Keep the draft in the input when sending fails.
                });
            }
          }}
        />
      </CardFooter>
    </Card>
  );
};
