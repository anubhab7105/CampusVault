/** Group management dialogs — create, members, roles, leave. Gated by PermissionGate. */

import { useEffect, useState } from "react";
import { Card, Button } from "@components/ui/index";
import { useAuthStore } from "@stores/useAuthStore";

interface GroupMember {
  id: string;
  name: string;
  role: "owner" | "moderator" | "member";
}

export function GroupManagementDialog({ groupId }: { groupId: string }) {
  const { user } = useAuthStore();
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [selectedMemberId, setSelectedMemberId] = useState("");
  const [role, setRole] = useState<"member" | "moderator" | "owner">("member");

  useEffect(() => {
    if (!user) {
      setMembers([]);
      return;
    }

    // TODO: replace the sample members with a request to the groups API.
    setMembers([
      { id: user.id, name: user.full_name, role: "owner" },
      { id: "user2", name: "Jane Student", role: "member" },
    ]);
  }, [groupId, user]);

  const canManage = Boolean(
    user && members.some(
      (member) => member.id === user.id && (member.role === "owner" || member.role === "moderator"),
    ),
  );

  const handleLeave = () => {
    // TODO: call the leave-group API and notify the parent to close this dialog.
  };

  const handleApplyRole = () => {
    if (!selectedMemberId || !canManage) return;
    // TODO: call the change-member-role API with selectedMemberId and role.
  };

  return (
    <Card className="max-w-sm p-6">
      <div className="text-body-sm font-semibold text-ink-default">Group Management</div>
      <div className="mt-4">
        {members.map((member) => (
          <div
            key={member.id}
            className="flex items-center justify-between p-2 rounded-md mb-2"
            style={{ background: user?.id === member.id ? "var(--brand-100)" : "transparent" }}
          >
            <span className="font-medium text-ink-default">{member.name}</span>
            <span className="rounded-full bg-surface-100 px-2 py-0.5 text-caption-xs">
              {member.role}
            </span>
          </div>
        ))}
      </div>

      {canManage && (
        <div className="mt-4 space-y-3">
          <label className="block text-caption-xs text-ink-tertiary mb-1" htmlFor="group-member">
            Member
          </label>
          <select
            id="group-member"
            value={selectedMemberId}
            onChange={(event) => setSelectedMemberId(event.currentTarget.value)}
            className="w-full rounded-md border border-border bg-transparent px-3 py-2"
          >
            <option value="">Select member</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.name}
              </option>
            ))}
          </select>

          <label className="block text-caption-xs text-ink-tertiary mb-1" htmlFor="group-role">
            New role
          </label>
          <select
            id="group-role"
            value={role}
            onChange={(event) => setRole(event.currentTarget.value as "member" | "moderator" | "owner")}
            className="w-full rounded-md border border-border bg-transparent px-3 py-2"
          >
            <option value="member">Member</option>
            <option value="moderator">Moderator</option>
            <option value="owner">Owner</option>
          </select>
          <Button onClick={handleApplyRole} disabled={!selectedMemberId} className="w-full">
            Apply role
          </Button>
        </div>
      )}

      <Button variant="destructive" onClick={handleLeave} className="mt-4 w-full">
        Leave Group
      </Button>
    </Card>
  );
}
