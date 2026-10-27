/** Chat hook — TanStack Query v5 infinite query + socket resync. */

import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
  useQueryState,
} from "@tanstack/react-query";
import { socketService } from "@services/socketService";
import { useAuthStore } from "@stores/useAuthStore";
import { useSocketStore } from "@stores/useSocketStore";
import { useEffect, useRef, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";

import { fetchMessages } from "@services/apiClient";

const CACHE_KEY = "/chat:messages";

interface UseChatOptions {
  conversationId: string;
  initialCursor?: string; // message id to start before
  pageSize?: number;
}

interface Message {
  id: string;
  content: string;
  sender_id: string;
  created_at: string;
}

/** Fetch a page of messages (newest first, keyset pagination). */
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
    fetchPage,
    invalidateQueries,
  } = useInfiniteQuery<
    Array<Message>,
    Error
  >(
    [CACHE_KEY, conversationId],
    async ({ pageParam = initialCursor }) => {
      const resp = await fetchMessages({
        conversation_id: conversationId,
        before_id: pageParam as string,
        limit: pageSize,
      });
      return resp.data.messages;
    },
    {
      getNextPageParam: (lastPage, pages) => {
        // Return the last message id as cursor for the next page
        if (lastPage.length === 0) return undefined;
        return lastPage[lastPage.length - 1].id;
      },
      getPreviousPageParam: (firstPage, pages) => {
        // For previous page, return the first message id as cursor
        if (firstPage.length === 0) return undefined;
        return firstPage[0].id;
      },
      staleTime: 2 * 60 * 1000, // 2 minutes
    }
  );

  /** Optimistic add: insert a new message at the beginning of the list */
  const addMessageOptimistic = (
    newMessage: Message
  ) => {
    queryClient.setInfiniteQueryData([CACHE_KEY, conversationId], (old) => {
      if (!old) return [newMessage];
      return [newMessage, ...old];
    });
  };

  /** Refetch after reconnect — only fetch messages after the last known cursor */
  const resyncAfterReconnect = useCallback(() => {
    if (user && socketService.connected) {
      invalidatedQueries([CACHE_KEY, conversationId]);
    }
  }, [queryClient, conversationId, user, invalidatedQueries]);

  useEffect(() => {
    // Subscribe to new messages via socket
    const unsub = socketService.on(
      "send_group_message",
      (payload: { data: { message: Message } }) => {
        const msg = payload.data.message;
        addMessageOptimistic(msg);
      }
    );

    // Subscribe to delivery/read status updates
    const unsubDeliver = socketService.on(
      "delivery_status",
      (payload: { data: { message_id: string } }) => {
        // Update delivered status locally
        queryClient.invalidateQueries([CACHE_KEY, conversationId]);
      }
    );

    const unsubRead = socketService.on(
      "read_receipt",
      (payload: { conversation_id: string; user_id: string }) => {
        queryClient.invalidateQueries([CACHE_KEY, conversationId]);
      }
    );

    return () => {
      unsub();
      unsubDeliver();
      unsubRead();
    };
  }, [conversationId, queryClient, addMessageOptimistic]);

  useEffect(() => {
    // Auto-resync on socket reconnect
    const handleReconnect = () => {
      resyncAfterReconnect();
    };
    socketService.off("connect", handleReconnect);
    socketService.on("connect", handleReconnect);
    return () => {
      socketService.off("connect", handleReconnect);
    };
  }, [resyncAfterReconnect]);

  // Combine all pages into a single array
  const allMessages = data?.flat() || [];

  return {
    messages: allMessages,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
    refetch: invalidatedQueries,
    resyncAfterReconnect,
  };
};

/** Mutation for sending a message with idempotency key. */
export const useSendMessage = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const sendMutation = useMutation<
    { success: boolean; message: Message },
    { conversationId: string; content: string; idempotencyKey: string },
    string
  >(
    async ({ conversationId, content, idempotencyKey }) => {
      const resp = await fetch("/api/v1/chat/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.access_token}`,
        },
        body: JSON.stringify({ conversationId, content, idempotencyKey }),
      });
      const data = await resp.json();
      return data;
    },
    {
      onSuccess: (data) => {
        // Optimistically add the message
        if (data.success && user?.currentConversationId) {
          queryClient.setInfiniteQueryData(
            [CACHE_KEY, user.currentConversationId],
            (old) => [data.message, ...(old || [])]
          );
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
