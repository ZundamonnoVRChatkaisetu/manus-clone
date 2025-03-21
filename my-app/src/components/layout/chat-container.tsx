"use client";

import React, { useState, useRef, useEffect } from "react";
import { Message, Task, TaskStep, AgentAction, AgentState } from "@/types";
import { ChatMessage } from "@/components/ui/chat-message";
import { ChatInput } from "@/components/ui/chat-input";
import { TaskCard } from "@/components/ui/task-card";
import { AgentLog } from "@/components/ui/agent-log";
import { Button } from "@/components/ui/button";
import { Pause, Play, StopCircle } from "lucide-react";

interface ChatContainerProps {
  messages: Message[];
  onSendMessage: (content: string, files?: File[]) => void;
  isLoading?: boolean;
  tasks?: Task[];
  taskSteps?: TaskStep[];
  agentActions?: AgentAction[];
  agentState?: AgentState;
  onPauseAgent?: () => void;
  onResumeAgent?: () => void;
  onStopAgent?: () => void;
}

export function ChatContainer({
  messages,
  onSendMessage,
  isLoading = false,
  tasks = [],
  taskSteps = [],
  agentActions = [],
  agentState = "idle",
  onPauseAgent,
  onResumeAgent,
  onStopAgent,
}: ChatContainerProps) {
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // メッセージが追加されたときに自動スクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const currentTask = tasks.find(task => task.status === "in_progress");
  const currentTaskSteps = currentTask
    ? taskSteps.filter(step => step.task_id === currentTask.id)
    : [];

  const isAgentActive = ["planning", "executing"].includes(agentState);
  const isWaitingForUser = agentState === "waiting_for_user";

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
      {/* チャット部分 - 左側2/3 */}
      <div className="md:col-span-2 flex flex-col border rounded-lg shadow-sm overflow-hidden">
        <div className="flex-1 p-4 overflow-y-auto">
          {messages.map((message, index) => (
            <ChatMessage
              key={message.id}
              message={message}
              isLast={index === messages.length - 1}
            />
          ))}
          <div ref={messagesEndRef} />
        </div>
        <ChatInput
          onSend={onSendMessage}
          disabled={isLoading || (isAgentActive && !isWaitingForUser)}
          placeholder={
            isWaitingForUser
              ? "エージェントに返信..."
              : isAgentActive
              ? "エージェントが実行中です..."
              : "タスクを入力..."
          }
        />
      </div>

      {/* エージェント状態表示部分 - 右側1/3 */}
      <div className="flex flex-col gap-4 h-full overflow-hidden">
        {/* エージェント制御ボタン */}
        {isAgentActive || isWaitingForUser ? (
          <div className="flex items-center gap-2 p-4 bg-muted/30 rounded-lg border">
            <div className="flex-1">
              <h3 className="font-medium text-sm">
                エージェント状態: {getAgentStateText(agentState)}
              </h3>
              <p className="text-xs text-muted-foreground">
                {getAgentStateDescription(agentState)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {isAgentActive ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onPauseAgent}
                  className="h-8"
                >
                  <Pause className="h-4 w-4 mr-1" />
                  一時停止
                </Button>
              ) : isWaitingForUser ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onResumeAgent}
                  className="h-8"
                >
                  <Play className="h-4 w-4 mr-1" />
                  再開
                </Button>
              ) : null}
              <Button
                variant="destructive"
                size="sm"
                onClick={onStopAgent}
                className="h-8"
              >
                <StopCircle className="h-4 w-4 mr-1" />
                停止
              </Button>
            </div>
          </div>
        ) : null}

        {/* タスク進行状況 */}
        <div className="flex flex-col gap-2 overflow-hidden">
          <h3 className="font-medium text-sm">タスク進行状況</h3>
          <div className="space-y-2 overflow-y-auto flex-shrink min-h-[100px] max-h-[200px]">
            {tasks.length > 0 ? (
              tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  steps={
                    expandedTaskId === task.id
                      ? taskSteps.filter((step) => step.task_id === task.id)
                      : undefined
                  }
                  expanded={expandedTaskId === task.id}
                  onToggleExpand={() =>
                    setExpandedTaskId(
                      expandedTaskId === task.id ? null : task.id
                    )
                  }
                />
              ))
            ) : (
              <div className="flex items-center justify-center h-24 bg-muted/20 rounded-md">
                <p className="text-sm text-muted-foreground">
                  タスクがここに表示されます
                </p>
              </div>
            )}
          </div>
        </div>

        {/* エージェントアクションログ */}
        <div className="flex flex-col gap-2 overflow-hidden flex-1">
          <h3 className="font-medium text-sm">エージェントログ</h3>
          <div className="overflow-y-auto flex-1">
            <AgentLog actions={agentActions} />
          </div>
        </div>
      </div>
    </div>
  );
}

function getAgentStateText(state: AgentState): string {
  switch (state) {
    case "idle":
      return "待機中";
    case "planning":
      return "計画中";
    case "executing":
      return "実行中";
    case "waiting_for_user":
      return "ユーザー入力待ち";
    case "error":
      return "エラー";
    case "completed":
      return "完了";
    default:
      return state;
  }
}

function getAgentStateDescription(state: AgentState): string {
  switch (state) {
    case "idle":
      return "エージェントは現在アイドル状態です";
    case "planning":
      return "タスクを分析し、実行計画を立てています";
    case "executing":
      return "タスクを実行しています";
    case "waiting_for_user":
      return "エージェントはあなたの返答を待っています";
    case "error":
      return "エラーが発生しました";
    case "completed":
      return "タスクが完了しました";
    default:
      return "";
  }
}
