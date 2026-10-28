/** Chat hook — TanStack Query infinite query + socket resync. */

import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { fetchMessages } from "@services/apiClient";
import { socketService } from "@services/socketService";
import { useAuthStore } from "@stores/useAuthStore";

interface Message {
  id: string;
  content: string;
  sender_id: string;
  created_at: string;
}

interface UseChatOptions {
  conversationId: string;
  initialCursor?: string;
  pageSize?: number;
}

interface SendMessageInput {
  conversationId: string;
  content: string;
  idempotencyKey: string;
}

interface SendMessageResponse {
  success: boolean;
  message?: Message;
}

/** Fetch messages with keyset pagination. */
export const useChatMessages = ({
  conversationId,
  initialCursor,
  pageSize = 20,
}: UseChatOptions) => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    status,
  } = useInfiniteQuery({
    queryKey: ["messages", conversationId],
    enabled: Boolean(conversationId),
    initialPageParam: initialCursor,
    queryFn: async ({ pageParam }): Promise<Message[]> => {
      const before = pageParam as string | undefined;
      const resp = await fetchMessages({
        conversation_id: conversationId,
        before_id: before,
        limit: pageSize,
      });
      return resp.data.messages as Message[];
    },
    getPreviousPageParam: (firstPage: Message[]) =>
      firstPage.length > 0 ? firstPage[0].id : undefined,
    getNextPageParam: (lastPage: Message[]) =>
      lastPage.length > 0 ? lastPage[lastPage.length - 1].id : undefined,
  });

  useEffect(() => {
    if (!user || !socketService.connected) return;

    const handleReconnect = () => {
      void queryClient.invalidateQueries({
        queryKey: ["messages", conversationId],
      });
    };

    socketService.off("connect", handleReconnect);
    socketService.on("connect", handleReconnect);

    return () => {
      socketService.off("connect", handleReconnect);
    };
  }, [conversationId, queryClient, user]);

  const allMessages = data?.pages.flat() ?? [];

  return {
    messages: allMessages,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
  };
};

/** Send message mutation with an idempotency key. */
export const useSendMessage = () => {
  const queryClient = useQueryClient();
  const { access_token } = useAuthStore();

  const sendMutation = useMutation({
    mutationFn: async ({
      conversationId,
      content,
      idempotencyKey,
    }: SendMessageInput): Promise<SendMessageResponse> => {
      const response = await fetch("/api/v1/chat/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${access_token}`,
        },
        body: JSON.stringify({ conversationId, content, idempotencyKey }),
      });

      if (!response.ok) {
        throw new Error("Message could not be sent.");
      }

      return (await response.json()) as SendMessageResponse;
    },
    onSuccess: async (result, variables) => {
      if (result.success) {
        await queryClient.invalidateQueries({
          queryKey: ["messages", variables.conversationId],
        });
      }
    },
  });

  return {
    sendMutation,
    isPending: sendMutation.isPending,
    isError: sendMutation.isError,
  };
};
