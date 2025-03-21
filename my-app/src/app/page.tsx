"use client";

import { useState, useEffect } from "react";
import { AppLayout } from "@/components/layout/app-layout";
import { ChatContainer } from "@/components/layout/chat-container";
import { apiClient } from "@/lib/api/api-client";
import { useWebSocket } from "@/lib/api/websocket-client";
import { Model, Message } from "@/types";
import { v4 as uuidv4 } from "uuid";

export default function Home() {
  // モデル一覧とセッション関連の状態
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [sessionId, setSessionId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // WebSocket接続を使用してリアルタイムデータを取得
  const {
    messages,
    tasks,
    taskSteps,
    agentActions,
    agentState,
    connected: wsConnected,
    sendMessage,
    changeModel,
    error: wsError
  } = useWebSocket(sessionId, {
    messages: [],
    tasks: [],
    taskSteps: [],
    agentActions: [],
  });

  // 初期化 - モデル一覧の取得
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const modelList = await apiClient.getModels();
        setModels(modelList);
        
        // デフォルトで最初のモデルを選択
        if (modelList.length > 0) {
          setSelectedModel(modelList[0]);
        }
        
        setLoading(false);
      } catch (err) {
        console.error("Failed to fetch models:", err);
        setError("モデル一覧の取得に失敗しました。");
        setLoading(false);
      }
    };

    fetchModels();
  }, []);

  // モデルが選択されたらセッションを作成
  useEffect(() => {
    const createSession = async () => {
      if (!selectedModel) return;
      
      try {
        // セッションがまだ存在しない場合のみ作成
        if (!sessionId) {
          // 本来はAPIでセッションを作成しますが、デモではローカルでIDを生成
          const newSessionId = uuidv4();
          setSessionId(newSessionId);
        }
      } catch (err) {
        console.error("Failed to create session:", err);
        setError("セッションの作成に失敗しました。");
      }
    };

    createSession();
  }, [selectedModel, sessionId]);

  // メッセージ送信ハンドラー
  const handleSendMessage = async (content: string, files?: File[]) => {
    if (!sessionId || !content.trim()) return;

    // ユーザーメッセージをローカル状態に追加（楽観的更新）
    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content: content,
      timestamp: new Date(),
      files: files?.map(file => ({
        id: uuidv4(),
        name: file.name,
        type: file.type,
        url: URL.createObjectURL(file),
        size: file.size,
      })),
    };
    
    // WebSocketで直接メッセージを送信
    if (wsConnected) {
      console.log("WebSocketを使用してメッセージを送信します");
      const success = sendMessage(content);
      
      if (success) {
        // WebSocket送信成功の場合は、APIリクエストをスキップ
        // ユーザーメッセージを表示するために状態を更新
        setMessages(prev => [...prev, userMessage]);
        return;
      } else {
        console.error("WebSocketでのメッセージ送信に失敗しました");
        // 通常のAPIフォールバックに進む
      }
    } else {
      console.warn("WebSocketが接続されていません。通常のAPIを使用します");
    }

    try {
      // フォールバック: 通常のAPI送信
      await apiClient.sendMessage(sessionId, content, files);
    } catch (err) {
      console.error("Failed to send message:", err);
      setError("メッセージの送信に失敗しました。");
    }
  };

  // エージェント制御ハンドラー
  const handlePauseAgent = async () => {
    if (!sessionId) return;
    try {
      await apiClient.pauseAgent(sessionId);
    } catch (err) {
      console.error("Failed to pause agent:", err);
    }
  };

  const handleResumeAgent = async () => {
    if (!sessionId) return;
    try {
      await apiClient.resumeAgent(sessionId);
    } catch (err) {
      console.error("Failed to resume agent:", err);
    }
  };

  const handleStopAgent = async () => {
    if (!sessionId) return;
    try {
      await apiClient.stopAgent(sessionId);
    } catch (err) {
      console.error("Failed to stop agent:", err);
    }
  };

  // モデル選択ハンドラー
  const handleSelectModel = (model: Model) => {
    setSelectedModel(model);
    
    // WebSocketが接続されている場合、モデル変更を通知
    if (wsConnected && sessionId) {
      console.log(`モデルを変更します: ${model.id}`);
      changeModel(model.id);
    } else {
      console.warn("WebSocketが接続されていないため、モデル変更を送信できません");
    }
  };

  // ローカルでのメッセージ状態管理（デモ用）
  const [localMessages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "こんにちは！AIエージェントのManusクローンです。どのようなタスクをお手伝いしましょうか？",
      timestamp: new Date(),
    },
  ]);

  // モデルがまだロード中の場合
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">読み込み中...</p>
      </div>
    );
  }

  // エラーがある場合
  if (error || !selectedModel) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <p className="text-lg text-destructive">{error || "モデルの選択に失敗しました。"}</p>
        <button 
          className="px-4 py-2 bg-primary text-white rounded-md"
          onClick={() => window.location.reload()}
        >
          再読み込み
        </button>
      </div>
    );
  }

  return (
    <AppLayout
      models={models}
      selectedModel={selectedModel}
      onSelectModel={handleSelectModel}
      isAgentRunning={agentState === "planning" || agentState === "executing"}
    >
      <ChatContainer
        messages={localMessages}
        onSendMessage={handleSendMessage}
        isLoading={!wsConnected}
        tasks={tasks}
        taskSteps={taskSteps}
        agentActions={agentActions}
        agentState={agentState}
        onPauseAgent={handlePauseAgent}
        onResumeAgent={handleResumeAgent}
        onStopAgent={handleStopAgent}
      />
    </AppLayout>
  );
}
