/** Group management dialogs — create, members, roles, leave. Gated by PermissionGate. */

import { useEffect, useState } from "react";
import { useDispatch } from "react-redux";

import { Card, Button, Select, Badge } from "@components/ui/index";
import { hideModal } from "@store/slices/modalSlice";
import { useAuthStore } from "@stores/useAuthStore";

interface GroupMember {
  id: string;
  name: string;
  role: "owner" | "moderator" | "member";
}

export function GroupManagementDialog({ groupId }: { groupId: string }) {
  const { user, permissions } = useAuthStore();
  const dispatch = useDispatch();
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [selectedMemberId, setSelectedMemberId] = useState("");
  const [role, setRole] = useState<"member" | "moderator" | "owner">("member");

  useEffect(() => {
    // TODO: replace the sample members with a request to the groups API.
    setMembers([
      { id: user.id, name: user.full_name, role: "owner" },
      { id: "user2", name: "Jane Student", role: "member" },
    ]);
  }, [groupId, user.id, user.full_name]);

  const canManage = permissions.includes("group:manage_members");

  const handleLeave = () => {
    dispatch(hideModal());
    // TODO: call the leave-group API.
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
            style={{ background: user.id === member.id ? "var(--brand-100)" : "transparent" }}
          >
            <span className="font-medium text-ink-default">{member.name}</span>
            <Badge
              variant={member.role === "owner" ? "destructive" : member.role === "moderator" ? "secondary" : "outline"}
              className="text-caption-xs"
            >
              {member.role}
            </Badge>
          </div>
        ))}
      </div>

      {canManage && (
        <div className="mt-4 space-y-3">
          <label className="block text-caption-xs text-ink-tertiary mb-1" htmlFor="group-member">
            Member
          </label>
          <Select value={selectedMemberId} onValueChange={setSelectedMemberId} placeholder="Select member">
            {members.map((member) => (
              <Select.Item key={member.id} value={member.id}>
                {member.name}
              </Select.Item>
            ))}
          </Select>

          <label className="block text-caption-xs text-ink-tertiary mb-1" htmlFor="group-role">
            New role
          </label>
          <Select value={role} onValueChange={(value: "member" | "moderator" | "owner") => setRole(value)} placeholder="Choose role">
            <Select.Item value="member">Member</Select.Item>
            <Select.Item value="moderator">Moderator</Select.Item>
            <Select.Item value="owner">Owner</Select.Item>
          </Select>
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
