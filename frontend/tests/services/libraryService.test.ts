import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@services/apiClient", () => ({
  apiClient: { get: mocks.get, post: mocks.post },
}));

import { libraryService } from "@services/libraryService";

describe("libraryService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("serializes active browse/search filters and omits empty values", async () => {
    mocks.get.mockResolvedValueOnce({
      data: { data: { items: [], paging: { total: 0 } } },
    });

    await libraryService.list({
      q: "cryptography",
      semester_id: "semester-1",
      page: 2,
      resource_type: "note",
      order: undefined,
    });

    const [url] = mocks.get.mock.calls[0];
    const query = new URL(url, "http://localhost").searchParams;
    expect(query.get("q")).toBe("cryptography");
    expect(query.get("semester_id")).toBe("semester-1");
    expect(query.get("page")).toBe("2");
    expect(query.get("resource_type")).toBe("note");
    expect(query.has("order")).toBe(false);
  });

  it("returns the resource page payload", async () => {
    const page = { items: [{ id: "resource-1" }], paging: { total: 1 } };
    mocks.get.mockResolvedValueOnce({ data: { data: page } });

    await expect(libraryService.list()).resolves.toEqual(page);
  });

  it("encodes resource IDs for detail and download requests", async () => {
    mocks.get.mockResolvedValueOnce({ data: { data: { id: "a/b" } } });
    mocks.post.mockResolvedValueOnce({ data: { data: { file_id: "file-1", external_url: null } } });

    await libraryService.get("a/b");
    await libraryService.download("a/b");

    expect(mocks.get).toHaveBeenCalledWith("/library/resources/a%2Fb");
    expect(mocks.post).toHaveBeenCalledWith("/library/resources/a%2Fb/download");
  });

  it("propagates API failures so callers can show and retry an error state", async () => {
    const failure = new Error("Network unavailable");
    mocks.get.mockRejectedValueOnce(failure);

    await expect(libraryService.list({ q: "retry" })).rejects.toBe(failure);
  });
});
