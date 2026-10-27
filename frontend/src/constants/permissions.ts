/** Permission catalog — wired to backend RBAC codes. Admin implies all. */

export const PERMISSIONS = {
  /** Library */
  LIBRARY_READ: "library:resource:read",
  LIBRARY_CREATE: "library:resource:create",
  LIBRARY_UPLOAD: "library:file:upload",

  /** Chat */
  CHAT_JOIN_GROUP: "chat:group:join",
  CHAT_SEND_MESSAGE: "chat:message:send",

  /** Academic */
  ACADEMIC_MANAGE: "admin:academic:manage",

  /** Admin */
  ADMIN_DASHBOARD_VIEW: "admin:dashboard:view",
  ADMIN_ROLES_MANAGE: "admin:roles:manage",
  ADMIN_USERS_MANAGE: "admin:users:manage",
  ADMIN_AUDIT_READ: "admin:audit:read",

  /** Groups */
  GROUPS_MANAGE: "admin:groups:manage",

  /** Files */
  FILES_UPLOAD: "files:upload",
} as const;

export type PermissionCode = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

/** Role → static permission grants (backend seeds these too). */
export const ROLE_PERMISSIONS: Record<RoleName, PermissionCode[]> = {
  Student: [
    PERMISSIONS.LIBRARY_READ,
    PERMISSIONS.CHAT_JOIN_GROUP,
    PERMISSIONS.CHAT_SEND_MESSAGE,
  ],
  Teacher: [
    PERMISSIONS.LIBRARY_READ,
    PERMISSIONS.LIBRARY_CREATE,
    PERMISSIONS.LIBRARY_UPLOAD,
    PERMISSIONS.CHAT_JOIN_GROUP,
    PERMISSIONS.CHAT_SEND_MESSAGE,
  ],
  Admin: [
    PERMISSIONS.ACADEMIC_MANAGE,
    PERMISSIONS.ADMIN_DASHBOARD_VIEW,
    PERMISSIONS.ADMIN_ROLES_MANAGE,
    PERMISSIONS.ADMIN_USERS_MANAGE,
    PERMISSIONS.ADMIN_AUDIT_READ,
    PERMISSIONS.GROUPS_MANAGE,
    PERMISSIONS.FILES_UPLOAD,
    PERMISSIONS.LIBRARY_READ,
    PERMISSIONS.LIBRARY_CREATE,
    PERMISSIONS.LIBRARY_UPLOAD,
    PERMISSIONS.CHAT_JOIN_GROUP,
    PERMISSIONS.CHAT_SEND_MESSAGE,
  ],
};

export function hasPermission(
  role: RoleName | null | undefined,
  codes: PermissionCode[],
): boolean {
  if (!role) return false;
  const held = new Set(ROLE_PERMISSIONS[role]);
  return codes.some((code) => held.has(code));
}

export function hasAnyPermission(
  role: RoleName | null | undefined,
  codes: PermissionCode[],
): boolean {
  if (!role) return false;
  const held = new Set(ROLE_PERMISSIONS[role]);
  return codes.some((code) => held.has(code));
}
