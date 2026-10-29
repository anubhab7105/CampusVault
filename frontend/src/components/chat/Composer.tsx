/** Message composer with validation, keyboard shortcuts, and delivery state. */

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";

import { useSendMessage } from "@hooks/useChat";

const MAX_MESSAGE_LENGTH = 4000;

const composerSchema = z.object({
  content: z.string().trim().min(1, "Enter a message.").max(MAX_MESSAGE_LENGTH),
});

interface ComposerProps {
  conversationId: string;
}

type ComposerValues = z.infer<typeof composerSchema>;

export const Composer = ({ conversationId }: ComposerProps) => {
  const { sendMutation, isPending } = useSendMessage();
  const form = useForm<ComposerValues>({
    resolver: zodResolver(composerSchema),
    defaultValues: { content: "" },
  });
  const content = form.watch("content");

  const onSubmit = (values: ComposerValues) => {
    sendMutation.mutate({
      conversationId,
      content: values.content.trim(),
      idempotencyKey: `msg-${crypto.randomUUID()}`,
    });
    form.reset();
  };

  const submitForm = form.handleSubmit(onSubmit);

  return (
    <form onSubmit={submitForm} className="space-y-2 rounded-lg border border-border p-3">
      <label htmlFor="message-content" className="sr-only">
        Message
      </label>
      <textarea
        id="message-content"
        {...form.register("content")}
        maxLength={MAX_MESSAGE_LENGTH}
        placeholder="Type a message…"
        rows={3}
        aria-invalid={Boolean(form.formState.errors.content)}
        className="w-full resize-y rounded-md border border-border bg-transparent p-3 text-body-md outline-none focus:ring-2 focus:ring-brand-500"
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void submitForm();
          }
        }}
      />
      <div className="flex items-center justify-between gap-3">
        <span className="text-caption-xs text-ink-tertiary" aria-live="polite">
          {content.length}/{MAX_MESSAGE_LENGTH}
        </span>
        <button
          type="submit"
          disabled={isPending || !content.trim()}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isPending ? "Sending…" : "Send"}
        </button>
      </div>
      {form.formState.errors.content?.message && (
        <p className="text-caption-xs text-red-600">{form.formState.errors.content.message}</p>
      )}
    </form>
  );
};
