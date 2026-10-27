/** Group management dialogs — create, members, roles, leave. Gated by PermissionGate. */

import { useState } from "react";
import { useAuthStore } from "@stores/useAuthStore";
import { useDispatch } from "react-redux";
import { hideModal, showModal } from "@store/slices/modalSlice";
import { Card, Input, Button, Select, Badge } from "@components/ui/index";
import { cn } from "@utils/cn";
import { useNavigate } from "react-router-dom";

export function GroupManagementDialog({ groupId }: { groupId: string }) {
  const { user, permissions } = useAuthStore();
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const [members, setMembers] = useState<any[]>([]);
  const [role, setRole] = useState<string>("member");
  const [newMemberId, setNewMemberId] = useState<string>("");

  // Fetch group members when dialog opens
  useEffect(() => {
    // TODO: fetch members from API
    setMembers([
      { id: user.id, name: user.full_name, role: "owner" },
      { id: "user2", name: "Jane Student", role: "member" },
    ]);
  }, [groupId, user.id]);

  const canManage = permissions.includes("group:manage_members");

  const handleLeave = () => {
    dispatch(hideModal());
    // TODO: call leave group API
    // socketService.emit("leave_group", { group_id: groupId });
  };

  const handleRoleChange = (memberId: string, newRole: string) => {
    // TODO: call change member role API
    // dispatch(changeMemberRole({ groupId, memberId, newRole }));
    setRole(newRole);
  };

  const handleAddMember = () => {
    // TODO: call add member API
    // dispatch(addMember({ groupId, memberId: newMemberId }));
    setNewMemberId("");
    dispatch(hideModal());
  };

  return (
    <Card className="max-w-sm p-6">
      <CardHeader>
        <span className="text-body-sm font-semibold text-ink-default">
          Group Management
        </span>
      </CardHeader>
      <CardContent>
        {/* Member list */}
        {members.map((m) => (
          <div
            key={m.id}
            className="flex items-center justify-between p-2 rounded-md mb-2"
            style={{ background: user.id === m.id ? "bg-brand-100" : "transparent" }}
          >
            <span className="font-medium text-ink-default">{m.name}</span>
            <Badge
              variant={m.role === "owner" ? "destructive" : m.role === "moderator" ? "secondary" : "outline"}
              className="text-caption-xs"
            >
              {m.role}
            </Badge>
          </div>
        ))}

        {/* Role change section (owner/moderator only) */}
        {canManage && (
          <div className="mt-4">
            <label className="text-caption-xs text-ink-tertiary mb-1">
              Change role for:
            </label>
            <Select
              onValueChange={handleRoleChange}
              placeholder="Select member"
            >
              {members.map((m) => (
                <Select.Item key={m.id} value={m.id}>
                  {m.name} ({m.role})
                </Select.Item>
              ))}
            </Select>
            <Select.Item
              value="member"
              placeholder="Set role to member"
            />
            <Select.Item value="moderator" placeholder="Set role to moderator" />
            <Select.Item value="owner" placeholder="Set role to owner" />
          </div>
        )}

        {/* Leave group button */}
        <Button
          variant="destructive"
          onClick={handleLeave}
          className="mt-4 w-full"
        >
          Leave Group
        </Button>
      </CardContent>
    </Card>
  );
}