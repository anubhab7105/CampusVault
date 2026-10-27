/** Chat hook — TanStack Query infinite query + socket resync. */

import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { socketService } from "@services/socketService";
import { useAuthStore } from "@stores/useAuthStore";
import { useEffect, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";

import { fetchMessages } from "@services/apiClient";

const CACHE_KEY = "/chat:messages";

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
    isPlaceholder,
  } = useInfiniteQuery<Message[], Error>(
    ["messages", conversationId],
    async ({ pageParam }) => {
      const before = pageParam as string | undefined;
      const resp = await fetchMessages({
        conversation_id: conversationId,
        before_id: before,
        limit: pageSize,
      });
      return resp.data.messages;
    },
    {
      getPreviousPageParam: (firstPage) => {
        if (firstPage.length === 0) return undefined;
        return firstPage[0].id;
      },
      getNextPageParam: (lastPage) => {
        if (lastPage.length === 0) return undefined;
        return lastPage[lastPage.length - 1].id;
      },
      keepPreviousData: true,
    }
  );

  /** Optimistic add a new message at the top */
  const addMessageOptimistic = (newMessage: Message) => {
    queryClient.setInfiniteQueryData(["messages", conversationId], (old) => {
      if (!old) return [newMessage];
      return [newMessage, ...old];
    });
  };

  /** Refetch after socket reconnect */
  useEffect(() => {
    if (!user || !socketService.connected) return;

    const handleReconnect = () => {
      queryClient.invalidateQueries(["messages", conversationId]);
    };

    socketService.off("connect", handleReconnect);
    socketService.on("connect", handleReconnect);

    return () => {
      socketService.off("connect", handleReconnect);
    };
  }, [conversationId, user]);

  // Merge all pages into flat list
  const allMessages = data?.reduce((acc, page) => acc.concat(page), []) || [];

  return {
    messages: allMessages,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
    placeholder: isPlaceholder,
  };
};

/** Send message mutation with idempotency key. */
export const useSendMessage = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const sendMutation = useMutation(
    async ({
      conversationId,
      content,
      idempotencyKey,
    }: {
      conversationId: string;
      content: string;
      idempotencyKey: string;
    }) => {
      const resp = await fetch("/api/v1/chat/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.access_token}`,
        },
        body: JSON.stringify({ conversationId, content, idempotencyKey }),
      });
      return resp.json();
    },
    {
      onSuccess: (data) => {
        if (data.success && user?.currentConversationId) {
          addMessageOptimistic(data.message);
        }
      },
    }
  );

  return {
    sendMutation,
    isPending: sendMutation.isPending,
    isError: sendMutation.isError,
  };
};
