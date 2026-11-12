import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  download: vi.fn(),
  currentUser: { role: "Student" as "Student" | "Teacher" | "Admin" } as
    { role: "Student" | "Teacher" | "Admin" } | null,
}));

vi.mock("@services/libraryService", () => ({
  libraryService: {
    list: (...args: unknown[]) => mocks.list(...args),
    download: (...args: unknown[]) => mocks.download(...args),
  },
}));

vi.mock("@stores/useAuthStore", () => ({
  useAuthStore: () => ({ user: mocks.currentUser }),
}));

import Library from "@pages/library/Library";

function renderLibrary(client = new QueryClient({
  defaultOptions: { queries: { retry: false, gcTime: 0 } },
})) {
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <Library />
      </QueryClientProvider>,
    ),
  };
}

const resource = {
  id: "resource-1",
  title: "Cryptography Notes",
  resource_type: "note",
  visibility: "college",
  download_count: 4,
};

describe("Library page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.currentUser = { role: "Student" };
  });

  it("shows loading placeholders while resources are being fetched", () => {
    mocks.list.mockReturnValue(new Promise(() => undefined));
    const { container } = renderLibrary();

    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("shows a useful empty state when the library has no resources", async () => {
    mocks.list.mockResolvedValue({ items: [] });
    renderLibrary();

    expect(await screen.findByText("No resources yet")).toBeInTheDocument();
  });

  it("disables download when the current role lacks library read permission", async () => {
    mocks.currentUser = { role: "Guest" as never };
    mocks.list.mockResolvedValue({ items: [resource] });
    renderLibrary();

    expect(await screen.findByText("Cryptography Notes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download" })).toBeDisabled();
  });

  it("enables download for a student with library read permission", async () => {
    mocks.currentUser = { role: "Student" };
    mocks.list.mockResolvedValue({ items: [resource] });
    mocks.download.mockResolvedValue({ file_id: "file-1" });
    renderLibrary();

    const button = await screen.findByRole("button", { name: "Download" });
    expect(button).toBeEnabled();
    fireEvent.click(button);

    await waitFor(() => expect(mocks.download).toHaveBeenCalled());
    expect(mocks.download.mock.calls[0][0]).toBe("resource-1");
  });

  it("shows a distinct error state and retries successfully", async () => {
    const user = userEvent.setup();
    mocks.list.mockRejectedValueOnce(new Error("Temporary network failure"));
    mocks.list.mockResolvedValueOnce({ items: [resource] });
    renderLibrary();

    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load resources");
    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Cryptography Notes")).toBeInTheDocument();
    expect(mocks.list).toHaveBeenCalledTimes(2);
  });

  it("keeps cached resources and download controls visible after a failed background refetch", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(["library", "resources"], { items: [resource] });
    mocks.list.mockRejectedValueOnce(new Error("Background refresh failed"));
    renderLibrary(client);

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("previously loaded resources"));
    expect(screen.getByText("Cryptography Notes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download" })).toBeEnabled();
  });

  it("keeps retry feedback visible while a retry is pending", async () => {
    const user = userEvent.setup();
    let rejectRequest!: (error: Error) => void;
    mocks.list.mockRejectedValueOnce(new Error("Temporary network failure"));
    mocks.list.mockImplementationOnce(() => new Promise((_, reject) => { rejectRequest = reject; }));
    renderLibrary();

    await user.click(await screen.findByRole("button", { name: "Try again" }));
    expect(screen.getByRole("button", { name: "Retrying…" })).toBeDisabled();
    rejectRequest(new Error("Still offline"));
    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("does not fetch the library before a user is available", () => {
    mocks.currentUser = null;
    renderLibrary();

    expect(mocks.list).not.toHaveBeenCalled();
  });
});
