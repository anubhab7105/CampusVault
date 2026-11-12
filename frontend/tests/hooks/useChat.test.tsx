import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  connected: vi.fn(() => false),
  socketOn: vi.fn(),
  socketOff: vi.fn(),
  authState: { user: { id: "user-1" } },
}));

vi.mock("@services/apiClient", () => ({
  apiClient: { get: mocks.get, post: mocks.post },
  fetchMessages: async (params: { conversation_id: string; before_id?: string; limit?: number }) => {
    const response = await mocks.get(
      `/chat/conversations/${encodeURIComponent(params.conversation_id)}/messages`,
      { params: { before_id: params.before_id, limit: params.limit ?? 50 } },
    );
    return { data: { messages: response.data.data?.items ?? [] } };
  },
}));

vi.mock("@services/socketService", () => ({
  socketService: {
    get connected() { return mocks.connected(); },
    on: (...args: unknown[]) => mocks.socketOn(...args),
    off: (...args: unknown[]) => mocks.socketOff(...args),
  },
}));

vi.mock("@stores/useAuthStore", () => ({
  useAuthStore: Object.assign(() => mocks.authState, { getState: () => ({ access_token: "token" }) }),
}));

import { useChatMessages, useSendMessage } from "@hooks/useChat";

function createWrapper(client: QueryClient) {
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

describe("useChatMessages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.connected.mockReturnValue(false);
  });

  it("loads the first history page and reports success", async () => {
    mocks.get.mockResolvedValueOnce({
      data: { data: { items: [{ id: "message-1", content: "Welcome", sender_id: "user-2", created_at: "2026-01-01" }] } },
    });
    const { result } = renderHook(
      () => useChatMessages({ conversationId: "conversation-1", pageSize: 10 }),
      { wrapper: createWrapper(createQueryClient()) },
    );

    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.messages).toHaveLength(1);
    expect(mocks.get).toHaveBeenCalledWith("/chat/conversations/conversation-1/messages", {
      params: { before_id: undefined, limit: 10 },
    });
  });

  it("returns an empty history when the API has no messages", async () => {
    mocks.get.mockResolvedValueOnce({ data: { data: { items: [] } } });
    const { result } = renderHook(
      () => useChatMessages({ conversationId: "conversation-empty" }),
      { wrapper: createWrapper(createQueryClient()) },
    );

    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.messages).toEqual([]);
    expect(result.current.hasNextPage).toBe(false);
  });

  it("exposes the error state for a failed history request", async () => {
    mocks.get.mockRejectedValueOnce(new Error("Request failed"));
    const { result } = renderHook(
      () => useChatMessages({ conversationId: "conversation-error" }),
      { wrapper: createWrapper(createQueryClient()) },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.status).toBe("error");
  });

  it("sends a message and invalidates that conversation history after success", async () => {
    const client = createQueryClient();
    const invalidateQueries = vi.spyOn(client, "invalidateQueries");
    mocks.post.mockResolvedValueOnce({ data: { success: true } });
    const { result } = renderHook(() => useSendMessage(), { wrapper: createWrapper(client) });

    await act(async () => {
      await result.current.sendMutation.mutateAsync({
        conversationId: "conversation-1",
        content: "Hello",
        idempotencyKey: "test",
      });
    });

    expect(mocks.post).toHaveBeenCalledWith(
      "/chat/conversations/conversation-1/messages",
      { conversation_id: "conversation-1", content: "Hello", reply_to_id: null },
      { headers: { "Idempotency-Key": "test" } },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["messages", "conversation-1"] });
  });

  it("preserves failed sends as mutation errors", async () => {
    mocks.post.mockRejectedValueOnce(new Error("Offline"));
    const { result } = renderHook(() => useSendMessage(), { wrapper: createWrapper(createQueryClient()) });

    await act(async () => {
      await expect(result.current.sendMutation.mutateAsync({
        conversationId: "conversation-1",
        content: "Retry me",
        idempotencyKey: "test",
      })).rejects.toThrow("Offline");
    });

    expect(result.current.isError).toBe(true);
  });
});
