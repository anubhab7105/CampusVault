import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  mutate: vi.fn(),
  pending: false,
}));

vi.mock("@hooks/useChat", () => ({
  useSendMessage: () => ({
    sendMutation: { mutate: mocks.mutate },
    isPending: mocks.pending,
  }),
}));

import { Composer } from "@components/chat/Composer";

describe("Composer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.pending = false;
  });

  it("exposes an accessible message field and disables send for an empty message", () => {
    render(<Composer conversationId="conversation-1" />);

    expect(screen.getByRole("textbox", { name: "Message" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("sends a trimmed message on submit and resets the field", async () => {
    const user = userEvent.setup();
    render(<Composer conversationId="conversation-1" />);

    const field = screen.getByRole("textbox", { name: "Message" });
    await user.type(field, "  Hello campus  ");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(mocks.mutate).toHaveBeenCalledTimes(1));
    expect(mocks.mutate).toHaveBeenCalledWith(expect.objectContaining({
      conversationId: "conversation-1",
      content: "Hello campus",
      idempotencyKey: expect.stringMatching(/^msg-/),
    }));
    expect(field).toHaveValue("");
  });

  it("submits with Enter and preserves newlines with Shift+Enter", async () => {
    const user = userEvent.setup();
    render(<Composer conversationId="conversation-1" />);
    const field = screen.getByRole("textbox", { name: "Message" });

    await user.type(field, "Keyboard message");
    fireEvent.keyDown(field, { key: "Enter", shiftKey: true });
    expect(mocks.mutate).not.toHaveBeenCalled();
    expect(field).toHaveValue("Keyboard message");

    fireEvent.keyDown(field, { key: "Enter", shiftKey: false });
    await waitFor(() => expect(mocks.mutate).toHaveBeenCalledTimes(1));
  });

  it("does not submit whitespace-only content", async () => {
    const user = userEvent.setup();
    render(<Composer conversationId="conversation-1" />);
    await user.type(screen.getByRole("textbox", { name: "Message" }), "   ");

    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    expect(mocks.mutate).not.toHaveBeenCalled();
  });

  it("disables the composer while a message is being sent", () => {
    mocks.pending = true;
    render(<Composer conversationId="conversation-1" />);

    expect(screen.getByRole("button", { name: "Sending…" })).toBeDisabled();
  });

  it("announces the character count to assistive technology", () => {
    render(<Composer conversationId="conversation-1" />);

    expect(screen.getByText("0/4000")).toHaveAttribute("aria-live", "polite");
  });
});
