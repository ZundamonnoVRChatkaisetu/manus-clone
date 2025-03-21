import React from "react";
import { AgentAction } from "@/types";
import { formatDate } from "@/lib/utils";
import { Terminal, Globe, FileText, Bell, HelpCircle } from "lucide-react";

interface AgentLogProps {
  actions: AgentAction[];
}

export function AgentLog({ actions }: AgentLogProps) {
  if (!actions.length) {
    return (
      <div className="flex items-center justify-center h-32 bg-muted/20 rounded-md">
        <p className="text-sm text-muted-foreground">
          エージェントのアクション履歴がここに表示されます
        </p>
      </div>
    );
  }

  const actionIcon = {
    command: <Terminal className="h-4 w-4" />,
    browser: <Globe className="h-4 w-4" />,
    file: <FileText className="h-4 w-4" />,
    notify: <Bell className="h-4 w-4" />,
    ask: <HelpCircle className="h-4 w-4" />,
  };

  return (
    <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
      {actions.map((action, index) => (
        <div
          key={index}
          className="flex gap-3 p-3 text-sm bg-card rounded-md border"
        >
          <div className="mt-0.5 text-primary">
            {actionIcon[action.type]}
          </div>
          <div className="flex flex-col gap-1 flex-1">
            <div className="flex items-center justify-between">
              <div className="font-medium">
                {getActionTitle(action)}
              </div>
              <div className="text-xs text-muted-foreground">
                {formatDate(action.timestamp)}
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              {getActionDescription(action)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function getActionTitle(action: AgentAction): string {
  switch (action.type) {
    case "command":
      return `コマンド実行: ${action.payload.command.slice(0, 30)}${
        action.payload.command.length > 30 ? "..." : ""
      }`;
    case "browser":
      return `ブラウザ操作: ${action.payload.url
        .replace(/^https?:\/\//, "")
        .slice(0, 30)}${action.payload.url.length > 30 ? "..." : ""}`;
    case "file":
      return `ファイル操作: ${action.payload.operation} ${action.payload.path.split("/").pop()}`;
    case "notify":
      return "通知";
    case "ask":
      return "質問";
    default:
      return "アクション";
  }
}

function getActionDescription(action: AgentAction): string {
  switch (action.type) {
    case "command":
      return action.payload.status
        ? `${action.payload.status}: ${action.payload.output?.slice(0, 100)}...`
        : "実行中...";
    case "browser":
      return action.payload.operation || action.payload.description || "ブラウザでの操作";
    case "file":
      return `${action.payload.path}`;
    case "notify":
      return action.payload.message;
    case "ask":
      return action.payload.question;
    default:
      return JSON.stringify(action.payload).slice(0, 100);
  }
}
