import { describe, expect, it } from "vitest";
import { hasAnyPermission, hasPermission, PERMISSIONS } from "@constants/permissions";

describe("frontend permission affordances", () => {
  it("allows students to read the library but not upload resources", () => {
    expect(hasPermission("Student", [PERMISSIONS.LIBRARY_READ])).toBe(true);
    expect(hasPermission("Student", [PERMISSIONS.LIBRARY_UPLOAD])).toBe(false);
  });

  it("allows teachers to upload and create library resources", () => {
    expect(hasPermission("Teacher", [PERMISSIONS.LIBRARY_UPLOAD])).toBe(true);
    expect(hasPermission("Teacher", [PERMISSIONS.LIBRARY_CREATE])).toBe(true);
  });

  it("grants admin library capabilities and rejects an unknown role", () => {
    expect(hasPermission("Admin", [PERMISSIONS.LIBRARY_UPLOAD])).toBe(true);
    expect(hasPermission(undefined, [PERMISSIONS.LIBRARY_READ])).toBe(false);
  });

  it("checks any requested permission rather than requiring all of them", () => {
    expect(hasAnyPermission("Student", [
      PERMISSIONS.LIBRARY_UPLOAD,
      PERMISSIONS.CHAT_SEND_MESSAGE,
    ])).toBe(true);
  });
});
