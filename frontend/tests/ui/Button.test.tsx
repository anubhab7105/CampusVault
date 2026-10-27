/** Vitest + React Testing Library example (unit layer of the pyramid). */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@components/ui/index";

describe("Button", () => {
  it("renders children and is disabled with isLoading", async () => {
    const user = userEvent.setup();
    render(<Button isLoading>Save</Button>);
    const button = screen.getByRole("button", { name: /loading/i });
    expect(button).toBeDisabled();
    await user.click(button);
    expect(button).toBeDisabled();
  });

  it("invokes onClick when enabled", async () => {
    const user = userEvent.setup();
    const clicked = vi.fn();
    render(<Button onClick={clicked}>Save</Button>);
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(clicked).toHaveBeenCalledTimes(1);
  });
});
