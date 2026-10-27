/** Composer — React Hook Form + Zod, length counter, Enter/Sender, Shift+Enter, file picker, typing. */

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

interface ComposerProps {
  conversationId: string;
}

/** Composer component — sends messages via socket, uses RHForm + Zod. */
export const Composer = ({ conversationId }: ComposerProps) => {
  const { user, access_token, setSending } = useAuthStore();
  const { connected, setTyping, typing } = useSocketStore();
  const dispatch = useDispatch();

  const form = useForm<{
    content: string;
  }>({
    resolver: zodResolver(z.object({ content: z.string().max(MAX_MESSAGE_LENGTH) })),
    defaultValues: { content: "" },
  });

  const onSubmit = async (values: { content: string }) => {
    const idempotencyKey = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    dispatch(sendMessage({ conversationId, content: values.content, idempotencyKey }));
    form.reset();
  };

  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;

    const handleTyping = () => {
      if (!connected || !user) return;
      setTyping(true);
      socketService.emit("typing", {
        conversation_id: conversationId,
        user_id: user.id,
        typing: true,
      });
      timer = setTimeout(() => {
        setTyping(false);
        socketService.emit("typing", {
          conversation_id: conversationId,
          user_id: user.id,
          typing: false,
        });
      }, 1000); // 1s after last keystroke
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        onSubmit({ content: e.target.value });
      }
      handleTyping();
    };

    if (connected && user) {
      handleTyping();
    }

    return () => {
      if (timer) clearTimeout(timer);
      socketService.off("typing");
    };
  }, [conversationId, connected, user]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Message</CardTitle>
      </CardHeader>
      <CardContent>
        <Input
          placeholder="Type a message..."
          maxlength={MAX_MESSAGE_LENGTH}
          value={form.getValues().content}
          onChange={form.handleChange}
          onKeyDown={handleKeyDown}
        />
      </CardContent>
      <CardFooter>
        <Button type="submit" form={form}>
          Send
        </Button>
      </CardFooter>
    </Card>
  );
};
