import axios from "axios";
import { Model, ChatSession, Message, Task, TaskStep, AgentAction } from "@/types";

// APIの基本URL - 実際の環境に合わせて変更してください
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/**
 * APIクライアントクラス
 * バックエンドとの通信を担当
 */
class ApiClient {
  // モデル関連
  async getModels(): Promise<Model[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/models`);
      return response.data;
    } catch (error) {
      console.error("Failed to fetch models:", error);
      // デモ用ダミーモデル
      return [
        {
          id: "llama3-8b",
          name: "Llama 3 8B",
          description: "Meta AI製の8Bパラメータモデル",
          context_length: 8192
        },
        {
          id: "mistral-7b",
          name: "Mistral 7B",
          description: "Mistral AI製の高性能7Bパラメータモデル",
          context_length: 8192
        },
        {
          id: "gemma-7b",
          name: "Gemma 7B",
          description: "Google製のオープンモデル",
          context_length: 8192
        }
      ];
    }
  }

  // チャットセッション関連
  async createChatSession(modelId: string, title: string): Promise<ChatSession> {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat/sessions`, {
        model_id: modelId,
        title
      });
      return response.data;
    } catch (error) {
      console.error("Failed to create chat session:", error);
      throw error;
    }
  }

  async getChatSessions(): Promise<ChatSession[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/chat/sessions`);
      return response.data;
    } catch (error) {
      console.error("Failed to fetch chat sessions:", error);
      return [];
    }
  }

  async getChatSession(sessionId: string): Promise<ChatSession> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/chat/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch chat session ${sessionId}:`, error);
      throw error;
    }
  }

  async sendMessage(sessionId: string, content: string, files?: File[]): Promise<Message> {
    try {
      const formData = new FormData();
      formData.append("content", content);
      
      if (files && files.length > 0) {
        files.forEach(file => {
          formData.append("files", file);
        });
      }
      
      const response = await axios.post(
        `${API_BASE_URL}/api/chat/sessions/${sessionId}/messages`, 
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data"
          }
        }
      );
      return response.data;
    } catch (error) {
      console.error("Failed to send message:", error);
      throw error;
    }
  }

  // タスク関連
  async getTasks(sessionId: string): Promise<Task[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/tasks?session_id=${sessionId}`);
      return response.data;
    } catch (error) {
      console.error("Failed to fetch tasks:", error);
      return [];
    }
  }

  async getTaskSteps(taskId: string): Promise<TaskStep[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/tasks/${taskId}/steps`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch steps for task ${taskId}:`, error);
      return [];
    }
  }

  // エージェントアクション関連
  async getAgentActions(sessionId: string): Promise<AgentAction[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/sessions/${sessionId}/actions`);
      return response.data;
    } catch (error) {
      console.error("Failed to fetch agent actions:", error);
      return [];
    }
  }

  // エージェント制御
  async pauseAgent(sessionId: string): Promise<void> {
    try {
      await axios.post(`${API_BASE_URL}/api/sessions/${sessionId}/pause`);
    } catch (error) {
      console.error("Failed to pause agent:", error);
      throw error;
    }
  }

  async resumeAgent(sessionId: string): Promise<void> {
    try {
      await axios.post(`${API_BASE_URL}/api/sessions/${sessionId}/resume`);
    } catch (error) {
      console.error("Failed to resume agent:", error);
      throw error;
    }
  }

  async stopAgent(sessionId: string): Promise<void> {
    try {
      await axios.post(`${API_BASE_URL}/api/sessions/${sessionId}/stop`);
    } catch (error) {
      console.error("Failed to stop agent:", error);
      throw error;
    }
  }
}

// 単一のインスタンスをエクスポート
export const apiClient = new ApiClient();
