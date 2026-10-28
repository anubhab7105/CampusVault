/** Conversation list — groups and DMs with unread badges and presence dots. */

import { useEffect } from "react";

import { Card, CardContent, CardHeader, Avatar, Badge, Skeleton, Button } from "@components/ui/index";
import { cn } from "@utils/cn";
import { useChatMessages } from "@hooks/useChat";
import { socketService } from "@services/socketService";
import { useAuthStore } from "@stores/useAuthStore";
import { useSocketStore } from "@stores/useSocketStore";

export default function ConversationList() {
  const { user } = useAuthStore();
  const { connected } = useSocketStore();
  const groups: any[] = [];
  const dmConversations: any[] = [];

  useEffect(() => {
    if (!user) return;

    const handleNotification = () => {
      // TODO: update unread counts when notification state is wired into Redux.
    };
    socketService.on("notification", handleNotification);

    return () => {
      socketService.off("notification", handleNotification);
    };
  }, [user]);

  const { isLoading } = useChatMessages({
    conversationId: "",
  });

  return (
    <Card className="h-[600px] w-full border-y border-border">
      <CardHeader className="flex items-center justify-between p-4 border-b border-border">
        <span className={cn("text-body-md font-semibold text-ink-default", user ? "" : "text-ink-secondary")}>
          {user?.full_name ?? "Chat"}
        </span>
        {connected ? (
          <span className="text-caption-xs text-green-600 font-medium">● Connected</span>
        ) : (
          <span className="text-caption-xs text-red-600 font-medium">○ Disconnected</span>
        )}
      </CardHeader>

      <CardContent className="h-96 overflow-y-auto p-4">
        {isLoading && <Skeleton className="h-6 w-20 rounded-b mb-2" />}

        {groups.length > 0 && (
          <div className="space-y-2 mb-6">
            <span className="text-caption-sm text-ink-tertiary uppercase tracking-wider">Groups</span>
            <div className="space-y-1">
              {groups.map((group) => (
                <Button
                  key={group.id}
                  variant="outline"
                  size="sm"
                  className={cn("w-full flex items-center justify-between", "px-3")}
                  onClick={() => {
                    // TODO: navigate to the selected group conversation.
                  }}
                >
                  <span className="font-medium text-ink-default">{group.name}</span>
                  <Badge variant="secondary" className="text-caption-xs">
                    {group.unread_count ?? 0}
                  </Badge>
                </Button>
              ))}
            </div>
          </div>
        )}

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
                    // TODO: set the active conversation and load its messages.
                  }}
                >
                  <Avatar className="w-6 h-6">{dm.last_sender_initial ?? "A"}</Avatar>
                  <span className="font-medium text-ink-default ml-2 line-clamp-1">
                    {dm.last_sender_name ?? "Unknown"}
                  </span>
                  <Badge variant="secondary" className="text-caption-xs ml-auto">
                    {dm.unread_count ?? 0}
                  </Badge>
                </Button>
              ))}
            </div>
          </div>
        )}

        {(!groups.length || !dmConversations.length) && (
          <p className="text-caption-xs text-ink-secondary italic mt-4">
            Select a group or direct message to start chatting
          </p>
        )}
      </CardContent>
    </Card>
  );
}
