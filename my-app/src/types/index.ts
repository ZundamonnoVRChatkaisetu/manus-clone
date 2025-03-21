/**
 * メッセージの型定義
 */
export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  files?: FileAttachment[];
}

/**
 * ファイル添付の型定義
 */
export interface FileAttachment {
  id: string;
  name: string;
  type: string;
  url: string;
  size: number;
}

/**
 * モデル情報の型定義
 */
export interface Model {
  id: string;
  name: string;
  description: string;
  context_length: number;
  parameters?: string;
}

/**
 * タスクの型定義
 */
export interface Task {
  id: string;
  title: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  progress: number;
  created_at: Date;
  updated_at: Date;
}

/**
 * タスクステップの型定義
 */
export interface TaskStep {
  id: string;
  task_id: string;
  description: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  output?: string;
  created_at: Date;
  updated_at: Date;
}

/**
 * AIエージェントのアクションの型定義
 */
export interface AgentAction {
  id?: string;
  type: "command" | "browser" | "file" | "notify" | "ask" | "file_operation" | "network_request" | "analysis" | "other";
  description?: string;
  details?: any;
  payload: any;
  timestamp: Date;
}

/**
 * エージェントの状態の型定義
 */
export type AgentState = 
  | "idle" 
  | "thinking"
  | "planning" 
  | "executing" 
  | "waiting_for_user" 
  | "error" 
  | "completed";

/**
 * チャットセッションの型定義
 */
export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  model: Model;
  created_at: Date;
  updated_at: Date;
  tasks?: Task[];
}
