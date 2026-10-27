/** Chat hook — TanStack Query infinite query + socket resync. */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { socketService } from "@services/socketService";
import { useAuthStore } from "@stores/useAuthStore";
import { useSocketStore } from "@stores/useSocketStore";
import { useEffect, useRef, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";

import { fetchMessages } from "@services/apiClient";

const CACHE_KEY = "chat:messages";

interface UseChatOptions {
  conversationId: string;
  initialCursor?: string; // message id to start before
  pageSize?: number;
}

interface MessageStatus {
  sending: boolean;
  sent: boolean;
  delivered: boolean;
  read: boolean;
}

/** Fetch a page of messages (newest first, keyset pagination). */
export const useChatMessages = ({
  conversationId,
  initialCursor,
  pageSize = 20,
}: UseChatOptions) => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const { data, isLoading, isError, fetchNextPage, hasNextPage } = useQuery<
    Array<{ id: string; content: string; sender_id: string; created_at: string }>,
    Error
  >(
    [CACHE_KEY, conversationId, initialCursor],
    async () => {
      const resp = await fetchMessages({
        conversation_id: conversationId,
        before_id: initialCursor,
        limit: pageSize,
      });
      return resp.data.messages;
    },
    {
      getPreviousPage: (lastPage) => {
        // If we have the first page and there's no previous, return null
        return null;
      },
      keepPreviousData: true,
    }
  );

  /** Optimistic add: insert a new message at the top of the list */
  const addMessageOptimistic = (
    newMessage: {
      id: string;
      content: string;
      sender_id: string;
      created_at: string;
    }
  ) => {
    queryClient.setQueryData(
      [CACHE_KEY, conversationId, initialCursor],
      (old: any) => [newMessage, ...(old || [])]
    );
  };

  /** Refetch after reconnect — only fetch messages after the last known cursor */
  const resyncAfterReconnect = useCallback(() => {
    if (user && socketService.connected) {
      queryClient.invalidateQueries([CACHE_KEY, conversationId]);
    }
  }, [queryClient, conversationId, user]);

  useEffect(() => {
    // Subscribe to new messages via socket
    const unsub = socketService.on(
      "send_group_message",
      (payload: { data: { message: any } }) => {
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

  return {
    messages: data || [],
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    refetch: queryClient.invalidateQueries,
    resyncAfterReconnect,
  };
};

/** Mutation for sending a message with idempotency key. */
export const useSendMessage = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const sendMutation = useMutation<
    { success: boolean; message: { id: string } },
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
        // Optimistically add the message; the server will ack with the real id
        if (data.success && user?.currentConversationId) {
          queryClient.setQueryData(
            ["chat:messages", data.success, user.currentConversationId],
            (old: any) => [data.message, ...(old || [])]
          );
        }
      },
    }
  );

  return { sendMutation, isLoading: sendMutation.isLoading };
};