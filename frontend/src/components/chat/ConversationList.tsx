/** Conversation list — groups and DMs with unread badges and presence dots. */

import { useEffect, useState } from "react";
import { useAuthStore } from "@stores/useAuthStore";
import { useSocketStore } from "@stores/useSocketStore";
import { socketService } from "@services/socketService";
import { useChatMessages } from "@hooks/useChat";
import { Card, Avatar, Badge, Skeleton, Button } from "@components/ui/index";
import { cn } from "@utils/cn";
import { formatRelative } from "@utils/datetime";
import { useDispatch } from "react-redux";
import { selectGroups, selectDMs } from "@store/slices/chatSlice";
import { loadGroups, loadDMs } from "@store/slices/chatSlice";

export default function ConversationList() {
  const { user } = useAuthStore();
  const { connected } = useSocketStore();

  // Load groups and DMs from Redux (populated by API calls on mount)
  useDispatch(loadGroups());
  useDispatch(loadDMs());

  const [groups, setGroups] = useState<any[]>([]);
  const [dmConversations, setDMConversations] = useState<any[]>([]);

  useEffect(() => {
    if (user) {
      // Groups and DMs are loaded via Redux; here we just subscribe to socket updates
      socketService.on("notification", (payload: any) => {
        // Handle notification badge updates
        // TODO: update unread counts
      });
    }
  }, [user]);

  const { messages, isLoading, fetchNextPage, hasNextPage } = useChatMessages({
    conversationId: "",
    initialCursor: undefined,
  });

  return (
    <Card className="h-[600px] w-full border-y border-border">
      <CardHeader className="flex items-center justify-between p-4 border-b border-border">
        <span className={cn("text-body-md font-semibold text-ink-default", user ? "" : "text-ink-secondary")}>
          {user?.full_name ?? "Chat"}
        </span>
        {connected ? (
          <span className="text-caption-xs text-green-600 font-medium">
            ● Connected
          </span>
        ) : (
          <span className="text-caption-xs text-red-600 font-medium">
            ○ Disconnected
          </span>
        )}
      </CardHeader>

      <CardContent className="h-96 overflow-y-auto p-4">
        {isLoading && (
          <Skeleton className="h-6 w-20 rounded-b mb-2" />
        )}

        {/* Groups section */}
        {groups.length > 0 && (
          <div className="space-y-2 mb-6">
            <span className="text-caption-sm text-ink-tertiary uppercase tracking-wider">Groups</span>
            <div className="space-y-1">
              {groups.map((g) => (
                <Button
                  key={g.id}
                  variant="outline"
                  size="sm"
                  className={cn("w-full flex items-center justify-between", "px-3")}
                  onClick={() => {/* Navigate to group chat */}
                  }
                >
                  <span className="font-medium text-ink-default">{g.name}</span>
                  <Badge
                    variant="secondary"
                    className="text-caption-xs"
                  >
                    {g.unread_count ?? 0}
                  </Badge>
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* DMs section */}
        {dmConversations.length > 0 && (
          <div className="space-y-2 mb-6">
            <span className="text-caption-sm text-ink-tertiary uppercase tracking-wider">Direct Messages</span>
            <div className="space-y-1">
              {dmConversations.map((dm) => (
                <Button
                  key={dm.id}
                  variant="outline"
                  size="sm"
                  className={cn("w-full flex items-center justify-between", "px-3")}
                  onClick={() => {
                    // Navigate to DM conversation
                    // TODO: set active conversation and load messages
                  }}
                >
                  <Avatar className="w-6 h-6">{dm.last_sender_initial ?? "A"}</Avatar>
                  <span className="font-medium text-ink-default ml-2 line-clamp-1">{dm.last_sender_name ?? "Unknown"}</span>
                  <Badge
                    variant="secondary"
                    className="text-caption-xs ml-auto"
                  >
                    {dm.unread_count ?? 0}
                  </Badge>
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Recent messages placeholder */}
        {(!groups.length || !dmConversations.length) && (
          <p className="text-caption-xs text-ink-secondary italic mt-4">
            Select a group or direct message to start chatting
          </p>
        )}
      </CardContent>
    </Card>
  );
}