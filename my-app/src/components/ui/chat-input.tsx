"use client";

import React, { useState, useRef, KeyboardEvent } from "react";
import { Button } from "./button";
import { Textarea } from "./textarea";
import { SendIcon, Paperclip } from "lucide-react";

interface ChatInputProps {
  onSend: (content: string, files?: File[]) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = "メッセージを入力..."
}: ChatInputProps) {
  const [content, setContent] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (content.trim() || files.length > 0) {
      onSend(content, files.length > 0 ? files : undefined);
      setContent("");
      setFiles([]);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setFiles((prevFiles) => [...prevFiles, ...newFiles]);
    }
  };

  return (
    <div className="flex flex-col gap-2 p-4 border-t">
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {files.map((file, index) => (
            <div
              key={index}
              className="flex items-center gap-1.5 rounded-md bg-muted px-2.5 py-1.5 text-xs font-medium"
            >
              <span>{file.name}</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-muted-foreground"
                onClick={() => {
                  setFiles((prev) => prev.filter((_, i) => i !== index));
                }}
              >
                ×
              </Button>
            </div>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2">
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="min-h-10 max-h-40"
        />
        <div className="flex gap-2">
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            multiple
            onChange={handleFileChange}
            disabled={disabled}
          />
          <Button
            variant="outline"
            size="icon"
            type="button"
            disabled={disabled}
            onClick={() => fileInputRef.current?.click()}
            aria-label="ファイルを添付"
          >
            <Paperclip className="h-4 w-4" />
          </Button>
          <Button
            type="submit"
            size="icon"
            disabled={disabled || (!content.trim() && files.length === 0)}
            onClick={handleSend}
            aria-label="送信"
          >
            <SendIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
