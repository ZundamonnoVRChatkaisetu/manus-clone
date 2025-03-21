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
    case "command": {
      // commandが存在するか確認してからslice
      const command = action.payload?.command || "";
      return `コマンド実行: ${command.slice(0, 30)}${
        command.length > 30 ? "..." : ""
      }`;
    }
    case "browser": {
      // urlが存在するか確認してからreplace/slice
      const url = action.payload?.url || "";
      const trimmedUrl = url.replace(/^https?:\/\//, "");
      return `ブラウザ操作: ${trimmedUrl.slice(0, 30)}${
        trimmedUrl.length > 30 ? "..." : ""
      }`;
    }
    case "file": {
      const operation = action.payload?.operation || "操作";
      const path = action.payload?.path || "";
      const fileName = path.split("/").pop() || path;
      return `ファイル操作: ${operation} ${fileName}`;
    }
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
    case "command": {
      const status = action.payload?.status;
      if (!status) return "実行中...";
      
      const output = action.payload?.output || "";
      return `${status}: ${output.slice(0, 100)}${output.length > 100 ? "..." : ""}`;
    }
    case "browser": {
      return action.payload?.operation || 
             action.payload?.description || 
             "ブラウザでの操作";
    }
    case "file": {
      return action.payload?.path || "ファイル操作";
    }
    case "notify": {
      return action.payload?.message || "通知メッセージ";
    }
    case "ask": {
      return action.payload?.question || "質問内容";
    }
    default: {
      const payloadStr = action.payload ? JSON.stringify(action.payload) : "{}";
      return payloadStr.slice(0, 100) + (payloadStr.length > 100 ? "..." : "");
    }
  }
}
