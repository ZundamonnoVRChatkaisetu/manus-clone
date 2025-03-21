"use client";

import { useEffect, useState, useCallback } from 'react';
import { Message, Task, TaskStep, AgentAction, AgentState } from '@/types';

// WebSocketの基本URL
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL || 'ws://localhost:8000';

interface WebSocketHookResult {
  messages: Message[];
  tasks: Task[];
  taskSteps: TaskStep[];
  agentActions: AgentAction[];
  agentState: AgentState;
  connected: boolean;
  error: string | null;
  sendMessage: (content: string) => boolean;
  changeModel: (modelId: string) => boolean;
}

/**
 * WebSocketクライアントフック
 * エージェントの状態やメッセージをリアルタイムで取得
 */
export function useWebSocket(sessionId: string, initialData?: {
  messages?: Message[];
  tasks?: Task[];
  taskSteps?: TaskStep[];
  agentActions?: AgentAction[];
}): WebSocketHookResult {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [messages, setMessages] = useState<Message[]>(initialData?.messages || []);
  const [tasks, setTasks] = useState<Task[]>(initialData?.tasks || []);
  const [taskSteps, setTaskSteps] = useState<TaskStep[]>(initialData?.taskSteps || []);
  const [agentActions, setAgentActions] = useState<AgentAction[]>(initialData?.agentActions || []);
  const [agentState, setAgentState] = useState<AgentState>('idle');

  const connect = useCallback(() => {
    try {
      if (!sessionId) {
        setError('セッションIDが指定されていません');
        return;
      }

      console.log(`WebSocket接続開始: ${WS_BASE_URL}/ws/chat/${sessionId}`);
      const newSocket = new WebSocket(`${WS_BASE_URL}/ws/chat/${sessionId}`);
      
      newSocket.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        setError(null);
      };
      
      newSocket.onclose = (event) => {
        console.log('WebSocket disconnected:', event);
        setConnected(false);
      };
      
      newSocket.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket接続エラーが発生しました');
      };
      
      newSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch (data.type) {
            case 'message':
              setMessages((prev) => [...prev, parseMessage(data.data)]);
              break;
            case 'messages':
              setMessages(data.data.map((msg: any) => parseMessage(msg)));
              break;
            case 'task':
              setTasks((prev) => {
                const parsedTask = parseTask(data.data);
                const index = prev.findIndex(t => t.id === parsedTask.id);
                if (index >= 0) {
                  return [...prev.slice(0, index), parsedTask, ...prev.slice(index + 1)];
                } else {
                  return [...prev, parsedTask];
                }
              });
              break;
            case 'tasks':
              setTasks(data.data.map((task: any) => parseTask(task)));
              break;
            case 'task_step':
              setTaskSteps((prev) => {
                const parsedStep = parseTaskStep(data.data);
                const index = prev.findIndex(s => s.id === parsedStep.id);
                if (index >= 0) {
                  return [...prev.slice(0, index), parsedStep, ...prev.slice(index + 1)];
                } else {
                  return [...prev, parsedStep];
                }
              });
              break;
            case 'task_steps':
              setTaskSteps(data.data.map((step: any) => parseTaskStep(step)));
              break;
            case 'agent_action':
              setAgentActions((prev) => [...prev, parseAgentAction(data.data)]);
              break;
            case 'agent_actions':
              setAgentActions(data.data.map((action: any) => parseAgentAction(action)));
              break;
            case 'agent_state':
              setAgentState(data.data);
              break;
            default:
              console.warn('Unknown message type:', data.type);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };
      
      setSocket(newSocket);
      
      // クリーンアップ関数
      return () => {
        newSocket.close();
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
      setError('WebSocket接続に失敗しました');
    }
  }, [sessionId]);

  // メッセージをパースする関数
  const parseMessage = (data: any): Message => {
    return {
      ...data,
      timestamp: data.timestamp ? new Date(data.timestamp) : new Date(),
    };
  };

  // タスクをパースする関数
  const parseTask = (data: any): Task => {
    return {
      ...data,
      created_at: data.created_at ? new Date(data.created_at) : new Date(),
      updated_at: data.updated_at ? new Date(data.updated_at) : new Date(),
    };
  };

  // タスクステップをパースする関数
  const parseTaskStep = (data: any): TaskStep => {
    return {
      ...data,
      created_at: data.created_at ? new Date(data.created_at) : new Date(),
      updated_at: data.updated_at ? new Date(data.updated_at) : new Date(),
    };
  };

  // エージェントアクションをパースする関数
  const parseAgentAction = (data: any): AgentAction => {
    return {
      ...data,
      timestamp: data.timestamp ? new Date(data.timestamp) : new Date(),
    };
  };

  useEffect(() => {
    const cleanup = connect();
    
    return () => {
      if (cleanup) cleanup();
      if (socket) socket.close();
    };
  }, [connect, sessionId]);

  // WebSocketを通じてメッセージを送信
  const sendMessage = useCallback((content: string) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocketが接続されていません');
      setError('WebSocketが接続されていません。再接続してください。');
      return false;
    }

    try {
      console.log('WebSocketでメッセージを送信:', content);
      const message = {
        type: 'message',
        content
      };
      socket.send(JSON.stringify(message));
      return true;
    } catch (err) {
      console.error('メッセージ送信エラー:', err);
      setError('メッセージの送信に失敗しました');
      return false;
    }
  }, [socket]);

  // WebSocketを通じてモデル変更リクエストを送信
  const changeModel = useCallback((modelId: string) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocketが接続されていません');
      setError('WebSocketが接続されていません。再接続してください。');
      return false;
    }

    try {
      console.log('WebSocketでモデル変更リクエストを送信:', modelId);
      const message = {
        type: 'model_change',
        model_id: modelId
      };
      socket.send(JSON.stringify(message));
      return true;
    } catch (err) {
      console.error('モデル変更リクエスト送信エラー:', err);
      setError('モデル変更リクエストの送信に失敗しました');
      return false;
    }
  }, [socket]);

  return {
    messages,
    tasks,
    taskSteps,
    agentActions,
    agentState,
    connected,
    error,
    sendMessage,
    changeModel
  };
}
