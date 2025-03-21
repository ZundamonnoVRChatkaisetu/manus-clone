import React from "react";
import { AgentAction } from "@/types";
import { formatDate } from "@/lib/utils";
import { Terminal, Globe, FileText, Bell, HelpCircle, Server, Network, BarChart } from "lucide-react";

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

  // アクションタイプに対応するアイコンの定義を拡張
  const actionIcon = {
    command: <Terminal className="h-4 w-4" />,
    browser: <Globe className="h-4 w-4" />,
    file: <FileText className="h-4 w-4" />,
    file_operation: <FileText className="h-4 w-4" />,
    notify: <Bell className="h-4 w-4" />,
    ask: <HelpCircle className="h-4 w-4" />,
    network_request: <Network className="h-4 w-4" />,
    analysis: <BarChart className="h-4 w-4" />,
    other: <Server className="h-4 w-4" />
  };

  return (
    <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
      {actions.map((action, index) => (
        <div
          key={index}
          className="flex gap-3 p-3 text-sm bg-card rounded-md border"
        >
          <div className="mt-0.5 text-primary">
            {actionIcon[action.type] || <Server className="h-4 w-4" />}
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
  // 直接descriptionフィールドがある場合はそれを使用
  if (action.description) {
    return action.description;
  }

  // タイプごとに適切なタイトルを生成
  switch (action.type) {
    case "command": {
      // commandが存在するか確認してからslice
      const command = action.payload?.command || action.details?.command || "";
      return `コマンド実行: ${command.slice(0, 30)}${
        command.length > 30 ? "..." : ""
      }`;
    }
    case "browser": {
      // urlが存在するか確認してからreplace/slice
      const url = action.payload?.url || action.details?.url || "";
      const trimmedUrl = url.replace(/^https?:\/\//, "");
      return `ブラウザ操作: ${trimmedUrl.slice(0, 30)}${
        trimmedUrl.length > 30 ? "..." : ""
      }`;
    }
    case "file":
    case "file_operation": {
      const operation = action.payload?.operation || action.details?.operation || "操作";
      const path = action.payload?.path || action.details?.path || "";
      const fileName = path.split("/").pop() || path;
      return `ファイル操作: ${operation} ${fileName}`;
    }
    case "network_request": {
      return "ネットワークリクエスト";
    }
    case "analysis": {
      return "データ分析";
    }
    case "notify": {
      return "通知";
    }
    case "ask": {
      return "質問";
    }
    default: {
      return action.type ? `${action.type}アクション` : "アクション";
    }
  }
}

function getActionDescription(action: AgentAction): string {
  // 従来のPayloadとdetailsの両方をサポート
  const details = action.details || {};
  const payload = action.payload || {};

  // detailsフィールドを優先的に使用し、次にpayloadを使用
  switch (action.type) {
    case "command": {
      const status = details.status || payload.status;
      if (!status) return "実行中...";
      
      const output = details.output || payload.output || "";
      return `${status}: ${output.slice(0, 100)}${output.length > 100 ? "..." : ""}`;
    }
    case "browser":
    case "network_request": {
      const desc = details.description || payload.description || 
                   details.operation || payload.operation;
      return desc || "ネットワーク操作";
    }
    case "file":
    case "file_operation": {
      const path = details.path || payload.path || "";
      return path || "ファイル操作";
    }
    case "notify": {
      const message = details.message || payload.message || "";
      return message || "通知メッセージ";
    }
    case "ask": {
      const question = details.question || payload.question || "";
      return question || "質問内容";
    }
    case "analysis": {
      return "データの分析を実行しています";
    }
    default: {
      // action.descriptionがある場合はそれを表示
      if (action.description) {
        return action.description;
      }
      
      // それ以外の場合は利用可能なオブジェクトをJSON文字列化
      const detailsStr = Object.keys(details).length > 0 
        ? JSON.stringify(details) 
        : "";
      
      const payloadStr = Object.keys(payload).length > 0 
        ? JSON.stringify(payload) 
        : "";
      
      const displayStr = detailsStr || payloadStr || "{}";
      return displayStr.slice(0, 100) + (displayStr.length > 100 ? "..." : "");
    }
  }
}
