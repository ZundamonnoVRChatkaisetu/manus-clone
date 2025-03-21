import React from "react";
import { Task, TaskStep } from "@/types";
import { cn, formatDate } from "@/lib/utils";
import { CheckCircle, Clock, AlertCircle, Loader2 } from "lucide-react";

interface TaskCardProps {
  task: Task;
  steps?: TaskStep[];
  expanded?: boolean;
  onToggleExpand?: () => void;
}

export function TaskCard({ task, steps, expanded = false, onToggleExpand }: TaskCardProps) {
  const statusIcon = {
    pending: <Clock className="h-4 w-4 text-muted-foreground" />,
    in_progress: <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />,
    completed: <CheckCircle className="h-4 w-4 text-green-500" />,
    failed: <AlertCircle className="h-4 w-4 text-destructive" />,
  };

  const statusText = {
    pending: "未開始",
    in_progress: "実行中",
    completed: "完了",
    failed: "失敗",
  };

  return (
    <div className="rounded-lg border bg-card shadow-sm">
      <div
        className={cn(
          "flex items-center justify-between p-4 cursor-pointer",
          task.status === "in_progress" && "bg-blue-50",
          task.status === "completed" && "bg-green-50",
          task.status === "failed" && "bg-red-50"
        )}
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-3">
          {statusIcon[task.status]}
          <div className="flex flex-col">
            <h3 className="font-medium text-sm">{task.title}</h3>
            <p className="text-xs text-muted-foreground">
              {statusText[task.status]} • {formatDate(task.updated_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-xs font-medium">
            {task.progress}%
          </div>
          <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full",
                task.status === "completed" ? "bg-green-500" : 
                task.status === "failed" ? "bg-destructive" : "bg-blue-500"
              )}
              style={{ width: `${task.progress}%` }}
            />
          </div>
        </div>
      </div>
      {expanded && steps && steps.length > 0 && (
        <div className="p-4 pt-0 border-t">
          <ul className="space-y-2 mt-2">
            {steps.map((step) => (
              <li key={step.id} className="flex items-center gap-2 text-sm">
                {statusIcon[step.status]}
                <span
                  className={cn(
                    step.status === "completed" && "text-green-700",
                    step.status === "failed" && "text-destructive"
                  )}
                >
                  {step.description}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
