/** Composer — React Hook Form + Zod, length counter, Enter/Sender, file picker, typing. */

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useSocketStore } from "@stores/useSocketStore";
import { useAuthStore } from "@stores/useAuthStore";
import { useDispatch } from "react-redux";
import { sendTyping } from "@store/slices/chatSlice";
import { Card, Input, Button, Skeleton } from "@components/ui/index";
import { cn } from "@utils/cn";

const MAX_MESSAGE_LENGTH = 4000;

const messageSchema = z.object({
  content: z.string()
    .min(1, "Message cannot be empty")
    .max(MAX_MESSAGE_LENGTH, `Message must be less than ${MAX_MESSAGE_LENGTH} characters`),
});

type MessageForm = z.infer<typeof messageSchema>;

export default function Composer() {
  const { user } = useAuthStore();
  const { connected } = useSocketStore();
  const dispatch = useDispatch();

  const [form] = useForm<MessageForm>({
    resolver: zodResolver(messageSchema),
    defaultValues: { content: "" },
  });

  const [typing, setTyping] = useState(false);
  const [input, setInput] = useState("");

  // Debounced typing indicator
  useEffect(() => {
    if (!connected || !user) return;
    const timer = setTimeout(() => {
      setTyping(false);
      socketService.emit("typing", {
        conversation_id: user.currentConversationId || "",
        user_id: user.id,
        typing: false,
      });
    }, 1000); // 1s after last keystroke

    return () => clearTimeout(timer);
  }, [user, connected, setTyping]);

  // Emit typing when state changes
  useEffect(() => {
    if (!connected || !user) return;
    setTyping(true);
    socketService.emit("typing", {
      conversation_id: user.currentConversationId || "",
      user_id: user.id,
      typing: true,
    });
  }, [user, connected]);

  const onSubmit = async (data: MessageForm) => {
    const content = data.content;
    if (!content.trim() || !conversationId) return;

    // Shift+Enter for newline, Enter to send
    // (handled by keydown listener in the input)

    dispatch(sendTyping(false)); // stop typing indicator on send
    setInput(""); // clear input
  };

  return (
    <Card className="p-4 border-t border-border">
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="flex gap-2"
        noValidate
      >
        <Input
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            // Enter to send, Shift+Enter for newline
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              form.handleSubmit(onSubmit);
            } else if (e.key === "Shift" && e.shiftKey) {
              // Allow newline via Shift+Enter
              setInput((prev) => prev + "\n");
            }
          }}
          maxLength={MAX_MESSAGE_LENGTH}
          disabled={!connected}
          className={cn("flex-1 rounded-l-lg border border-border", !connected && "opacity-50 cursor-not-allowed")}
        />
        <Button
          type="submit"
          disabled={!connected || !form.getValues().content.trim()}
          className="flex-shrink-0 rounded-r-lg bg-brand px-4"
          type="button">
          Send
        </Button>
      </form>

      {typing && connected && (
        <Skeleton className="h-4 w-24 rounded-md my-2" />
      )}
    </Card>
  );
}