import React from "react";
import { Message } from "@/types";
import { cn, formatDate } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { UserIcon, Bot } from "lucide-react";
import { FileAttachment } from "@/types";

interface ChatMessageProps {
  message: Message;
  isLast?: boolean;
}

export function ChatMessage({ message, isLast }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  return (
    <div
      className={cn(
        "flex w-full items-start gap-4 py-4",
        isUser ? "justify-end" : "",
        isSystem ? "bg-muted/50" : ""
      )}
    >
      {!isUser && (
        <Avatar className="h-8 w-8 border">
          <Bot className="h-5 w-5" />
        </Avatar>
      )}
      <div
        className={cn(
          "flex flex-col gap-1.5 max-w-3xl",
          isUser ? "items-end" : ""
        )}
      >
        <div
          className={cn(
            "flex flex-col gap-2 rounded-lg px-4 py-2.5 text-sm",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-foreground"
          )}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
          {message.files && message.files.length > 0 && (
            <MessageAttachments files={message.files} />
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>
            {isUser ? "ユーザー" : isSystem ? "システム" : "アシスタント"}
          </span>
          <span>•</span>
          <span>{formatDate(message.timestamp)}</span>
        </div>
      </div>
      {isUser && (
        <Avatar className="h-8 w-8 border">
          <UserIcon className="h-5 w-5" />
        </Avatar>
      )}
    </div>
  );
}

interface MessageAttachmentsProps {
  files: FileAttachment[];
}

function MessageAttachments({ files }: MessageAttachmentsProps) {
  return (
    <div className="flex flex-col gap-2 mt-2">
      <div className="text-xs font-medium">添付ファイル:</div>
      <div className="flex flex-wrap gap-2">
        {files.map((file) => (
          <a
            key={file.id}
            href={file.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-md bg-background px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-accent"
          >
            <span>{file.name}</span>
            <span className="text-muted-foreground">
              ({Math.round(file.size / 1024)} KB)
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}
