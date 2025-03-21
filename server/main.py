from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import json
from datetime import datetime
import asyncio
from enum import Enum
import os
import httpx
import subprocess
import shlex
import sys
import tempfile
from pathlib import Path
import aiohttp
import base64
from io import BytesIO
import traceback

# FastAPIアプリケーションの初期化
app = FastAPI(title="Manus Clone API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンのみ許可するよう変更
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データモデル定義
class ModelInfo(BaseModel):
    id: str
    name: str
    description: str
    context_length: int

class FileAttachment(BaseModel):
    id: str
    name: str
    type: str
    url: str
    size: int

class Message(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime
    files: Optional[List[FileAttachment]] = None

class ChatSession(BaseModel):
    id: str
    model_id: str
    title: str
    created_at: datetime
    updated_at: datetime

class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"

class Task(BaseModel):
    id: str
    session_id: str
    title: str
    description: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

class TaskStepStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"

class TaskStep(BaseModel):
    id: str
    task_id: str
    title: str
    description: str
    status: TaskStepStatus
    created_at: datetime
    updated_at: datetime

class AgentActionType(str, Enum):
    command = "command"
    file_operation = "file_operation"
    network_request = "network_request"
    analysis = "analysis"
    other = "other"
    browser = "browser"
    file = "file"
    notify = "notify"
    ask = "ask"

class AgentAction(BaseModel):
    id: str
    session_id: str
    type: AgentActionType
    description: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

class AgentState(str, Enum):
    idle = "idle"
    thinking = "thinking"  # 思考中の状態を追加
    planning = "planning"
    executing = "executing"
    waiting_for_user = "waiting_for_user"
    error = "error"
    completed = "completed"

# インメモリデータストア（実際の実装ではデータベースを使用）
models_db = []  # 空リストに変更、Ollamaから動的に取得するため

# Ollamaの接続設定
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")

# Ollamaからモデル一覧を取得する関数
async def fetch_ollama_models() -> List[ModelInfo]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_API_URL}/api/tags")
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Ollamaサーバーからの応答エラー: {response.status_code}")
            
            data = response.json()
            models = []
            
            for model in data.get("models", []):
                model_name = model.get("name", "")
                models.append(
                    ModelInfo(
                        id=model_name,
                        name=model_name,
                        description=f"Ollamaモデル: {model_name}",
                        context_length=8192  # デフォルト値、実際のコンテキスト長はモデルごとに異なる
                    )
                )
            
            # モデルが見つからない場合はデフォルトモデルを追加
            if not models:
                models = [
                    ModelInfo(
                        id="llama3-8b",
                        name="Llama 3 8B",
                        description="Meta AI製の8Bパラメータモデル",
                        context_length=8192
                    ),
                    ModelInfo(
                        id="mistral-7b",
                        name="Mistral 7B",
                        description="Mistral AI製の高性能7Bパラメータモデル",
                        context_length=8192
                    ),
                    ModelInfo(
                        id="gemma-7b",
                        name="Gemma 7B",
                        description="Google製のオープンモデル",
                        context_length=8192
                    )
                ]
            
            return models
    except Exception as e:
        # エラー発生時もデフォルトモデルを返す
        print(f"Ollamaモデル取得エラー: {str(e)}")
        return [
            ModelInfo(
                id="llama3-8b",
                name="Llama 3 8B",
                description="Meta AI製の8Bパラメータモデル",
                context_length=8192
            ),
            ModelInfo(
                id="mistral-7b", 
                name="Mistral 7B",
                description="Mistral AI製の高性能7Bパラメータモデル",
                context_length=8192
            ),
            ModelInfo(
                id="gemma-7b",
                name="Gemma 7B",
                description="Google製のオープンモデル",
                context_length=8192
            )
        ]

sessions_db: Dict[str, ChatSession] = {}
messages_db: Dict[str, List[Message]] = {}
tasks_db: Dict[str, List[Task]] = {}
task_steps_db: Dict[str, List[TaskStep]] = {}
agent_actions_db: Dict[str, List[AgentAction]] = {}
agent_state_db: Dict[str, AgentState] = {}

# API用のプロンプトテンプレート - より単純なシステムプロンプトに変更
SYSTEM_PROMPT = """
あなたはManusというAIエージェントです。ユーザーのタスク指示を解析し、実行可能なステップに分解してください。
レスポンスはJSON形式で返してください。
"""

# テスト用の単純なリクエスト関数を追加
async def test_ollama_simple_request():
    """
    Ollamaへの最小限のリクエストテスト
    """
    model_id = "llama3" # または使用可能な別のモデル
    simple_prompt = "こんにちは"
    simple_system = "あなたは有能なアシスタントです。"
    
    print("--- シンプルなOllamaリクエストテスト開始 ---")
    
    base_url = OLLAMA_API_URL
    url = f"{base_url}/api/generate"
    
    # 最小限のデータ
    data = {
        "model": model_id,
        "prompt": simple_prompt,
        "system": simple_system,
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"成功! レスポンス: {result.get('response', '')[:100]}...")
                return True
            else:
                print(f"エラー: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"例外: {str(e)}")
        return False

# Ollamaからレスポンスを取得する関数 - 改善版
async def get_ollama_response(model_id, prompt, system_prompt=SYSTEM_PROMPT, max_tokens=4000):
    """
    Ollamaサーバーからレスポンスを取得する関数 - 改善版
    """
    try:
        # 設定からURLを取得
        base_url = OLLAMA_API_URL
        url = f"{base_url}/api/generate"
        
        # シンプル化したリクエストデータ
        data = {
            "model": model_id,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }
        
        print(f"Ollamaリクエスト内容: {json.dumps(data, ensure_ascii=False)[:500]}...")
        
        # タイムアウト設定を長め（120秒）に設定
        async with httpx.AsyncClient(timeout=120.0) as client:
            # まずシンプルなテストリクエストを試す
            test_success = await test_ollama_simple_request()
            if not test_success:
                print("警告: シンプルなテストリクエストが失敗しました。Ollamaサーバーに問題がある可能性があります。")
            
            # 実際のリクエストを送信
            response = await client.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                print(f"Ollamaレスポンス成功: 長さ{len(response_text)}文字")
                return response_text
            else:
                error_detail = f"HTTPエラー: {response.status_code} - {response.text}"
                print(f"Ollamaリクエストエラー: {error_detail}")
                return f"エラー: {error_detail}"
    
    except httpx.TimeoutException as e:
        error_msg = f"タイムアウトエラー: {str(e)}"
        print(error_msg)
        return f"エラー: {error_msg}"
    
    except httpx.RequestError as e:
        error_msg = f"リクエストエラー: {str(e)}"
        print(error_msg)
        return f"エラー: {error_msg}"
    
    except json.JSONDecodeError as e:
        error_msg = f"JSONデコードエラー: {str(e)}"
        print(error_msg)
        return f"エラー: {error_msg}"
    
    except Exception as e:
        error_msg = f"予期せぬエラー: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return f"エラー: {error_msg}"

# タスクを解析して実行ステップに分解する - 改善版
async def analyze_task(model_id, task_description):
    """
    ユーザーのタスク指示を解析し、実行ステップに分解する - 改善版
    """
    print(f"タスク解析開始 - モデル: {model_id}, タスク: {task_description[:50]}...")
    prompt = f"""
ユーザーの次のタスクを解析し、実行ステップに分解してください：

{task_description}

最大5つのステップに分けて、以下のJSON形式で返してください。他の説明は不要です：

{{
    "thought": "タスクの分析と考察...",
    "steps": [
        {{
            "title": "ステップ1のタイトル",
            "description": "ステップ1の詳細説明",
            "action": "実行するアクション（shell_command, read_file, write_file, web_fetch）",
            "params": {{アクションに必要なパラメータ}}
        }},
        ...
    ]
}}
"""
    
    response = await get_ollama_response(model_id, prompt)
    if not response.startswith("エラー: ") and not response.startswith("例外発生: "):
        # レスポンスからJSONを抽出
        try:
            content = response
            print(f"タスク解析レスポンス: {content[:100]}...")
            
            # JSONブロックを抽出する - 改善版
            import re
            
            # 1. JSONブロック（```json 〜 ```）を探す
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                print("JSONブロックを検出しました")
                json_str = json_match.group(1)
            else:
                # 2. 単純に最初の { から最後の } までを取得
                first_brace = content.find('{')
                last_brace = content.rfind('}')
                
                if first_brace >= 0 and last_brace > first_brace:
                    print("JSONブロックは見つかりませんが、{}で囲まれた部分を抽出します")
                    json_str = content[first_brace:last_brace+1]
                else:
                    print("JSON形式のデータが見つかりません、テキスト全体を解析します")
                    json_str = content
            
            print(f"JSONパース前: {json_str[:100]}...")
            
            # 文字列をJSON形式に整形してからパース
            try:
                plan = json.loads(json_str)
                print("JSONパース成功")
                
                # 必須フィールドの存在確認
                if "thought" not in plan or "steps" not in plan:
                    print("JSONの形式が不正: 'thought'または'steps'フィールドがありません")
                    return {
                        "success": False,
                        "error": "JSONの形式が不正: 必須フィールドがありません",
                        "raw_response": content
                    }
                
                return {
                    "success": True,
                    "plan": plan
                }
            except json.JSONDecodeError as e:
                # JSON解析エラー - 単純なエラーメッセージを返す
                error_msg = f"JSONの解析に失敗しました: {str(e)}"
                print(f"{error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "raw_response": content
                }
        except Exception as e:
            error_msg = f"タスク解析処理中にエラーが発生しました: {str(e)}"
            print(f"{error_msg} - レスポンス: {content[:200]}")
            return {
                "success": False,
                "error": error_msg,
                "raw_response": content
            }
    else:
        return {
            "success": False,
            "error": response
        }

# ステップを実行する
async def execute_step(step, session_id):
    """
    タスクステップを実行する
    """
    action_type = step.get("action", "").lower()
    params = step.get("params", {})
    
    # 作業用ディレクトリを作成・使用
    work_dir = f"workspaces/{session_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    result = {
        "success": False,
        "output": "",
        "error": ""
    }
    
    try:
        if action_type == "shell_command":
            command = params.get("command", "")
            result = await AgentTools.execute_shell_command(command, cwd=work_dir)
            
        elif action_type == "read_file":
            file_path = params.get("path", "")
            # 相対パスの場合は作業ディレクトリからの相対パスとして解釈
            if not os.path.isabs(file_path):
                file_path = os.path.join(work_dir, file_path)
            result = await AgentTools.read_file(file_path)
            
        elif action_type == "write_file":
            file_path = params.get("path", "")
            content = params.get("content", "")
            # 相対パスの場合は作業ディレクトリからの相対パスとして解釈
            if not os.path.isabs(file_path):
                file_path = os.path.join(work_dir, file_path)
            result = await AgentTools.write_file(file_path, content)
            
        elif action_type == "web_fetch":
            url = params.get("url", "")
            result = await AgentTools.fetch_web_content(url)
            
        else:
            result = {
                "success": False,
                "error": f"不明なアクションタイプ: {action_type}"
            }
    except Exception as e:
        result = {
            "success": False,
            "error": f"ステップ実行中にエラーが発生しました: {str(e)}"
        }
    
    return result

# エージェント実行ユーティリティ
class AgentTools:
    @staticmethod
    async def execute_shell_command(command, cwd=None):
        """
        シェルコマンドを安全に実行する
        """
        try:
            # Windowsの場合はPowerShellを使用
            if sys.platform == 'win32':
                # PowerShellでコマンドを実行するようにする
                full_command = ["powershell", "-Command", command]
                process = subprocess.Popen(
                    full_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    text=True
                )
            else:
                # Linuxの場合はbashを使用
                process = subprocess.Popen(
                    ["bash", "-c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    text=True
                )
            
            stdout, stderr = process.communicate()
            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    @staticmethod
    async def read_file(file_path):
        """
        ファイルを読み込む
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "success": True,
                "content": content
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def write_file(file_path, content):
        """
        ファイルに書き込む
        """
        try:
            # ディレクトリが存在しない場合は作成
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {
                "success": True,
                "file_path": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def fetch_web_content(url):
        """
        Webコンテンツを取得する
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        text = await response.text()
                        return {
                            "success": True,
                            "content": text,
                            "status": response.status
                        }
                    else:
                        return {
                            "success": False,
                            "status": response.status,
                            "error": f"HTTPエラー: {response.status}"
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# ステップ実行の結果を分析し次のアクションを決定する
async def analyze_step_result(model_id, step, result):
    """
    ステップ実行結果を分析し、次のアクションを決定する
    """
    print(f"ステップ実行結果の分析 - ステップ: {step.get('title', '不明なステップ')}")
    
    # 成功した場合は単に成功を報告
    if result.get("success", False):
        return {
            "success": True,
            "continue": True,
            "message": f"ステップ「{step.get('title', '不明なステップ')}」は正常に完了しました。"
        }
    
    # 失敗した場合は、エラーの詳細を含めて報告
    error_msg = result.get("error", "不明なエラー")
    return {
        "success": False,
        "continue": False,  # エラーが発生したため処理を停止
        "message": f"ステップ「{step.get('title', '不明なステップ')}」の実行中にエラーが発生しました: {error_msg}"
    }

# タスク完了後の要約を生成
async def generate_task_summary(model_id, task_description, steps_results):
    """
    タスク完了後の要約を生成する
    """
    print(f"タスク要約生成開始 - モデル: {model_id}")
    
    # 各ステップの実行結果を整形
    steps_summary = ""
    for i, (step, result) in enumerate(steps_results):
        status = "成功" if result.get("success", False) else "失敗"
        steps_summary += f"ステップ {i+1}: {step.get('title', '不明なステップ')} - {status}\n"
        if "stdout" in result:
            output = result.get("stdout", "").strip()
            if output:
                steps_summary += f"出力: {output[:500]}{'...' if len(output) > 500 else ''}\n"
        if "error" in result and result["error"]:
            steps_summary += f"エラー: {result.get('error', '')}\n"
        steps_summary += "\n"
    
    prompt = f"""
以下のタスクとその実行結果を要約してください：

タスク: {task_description}

実行結果:
{steps_summary}

要約とユーザーへのフィードバックを簡潔に記述してください。
"""
    
    response = await get_ollama_response(model_id, prompt)
    if not response.startswith("エラー: ") and not response.startswith("例外発生: "):
        return response
    else:
        return "タスク実行は完了しましたが、要約の生成中にエラーが発生しました。詳細はログを確認してください。"

# WebSocket接続を管理するクラス
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: Dict[str, Any]):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                await connection.send_json(message)

manager = ConnectionManager()

# APIエンドポイント
@app.get("/api/models", response_model=List[ModelInfo])
async def get_models():
    global models_db
    if not models_db:
        models_db = await fetch_ollama_models()
    return models_db

@app.post("/api/chat/sessions", response_model=ChatSession)
async def create_chat_session(model_id: str, title: str):
    session_id = str(uuid.uuid4())
    now = datetime.now()
    session = ChatSession(
        id=session_id,
        model_id=model_id,
        title=title,
        created_at=now,
        updated_at=now
    )
    
    sessions_db[session_id] = session
    messages_db[session_id] = [
        Message(
            id=str(uuid.uuid4()),
            role="assistant",
            content="こんにちは！AIエージェントのManusクローンです。どのようなタスクをお手伝いしましょうか？",
            timestamp=datetime.now(),
            files=None
        )
    ]
    tasks_db[session_id] = []
    agent_actions_db[session_id] = []
    agent_state_db[session_id] = AgentState.idle
    
    return session

@app.get("/api/chat/sessions", response_model=List[ChatSession])
async def get_chat_sessions():
    return list(sessions_db.values())

@app.get("/api/chat/sessions/{session_id}", response_model=ChatSession)
async def get_chat_session(session_id: str):
    if session_id not in sessions_db:
        return {"error": "Session not found"}
    return sessions_db[session_id]

@app.get("/api/chat/sessions/{session_id}/messages", response_model=List[Message])
async def get_messages(session_id: str):
    if session_id not in messages_db:
        return []
    return messages_db[session_id]

@app.post("/api/chat/sessions/{session_id}/messages", response_model=Message)
async def send_message(
    session_id: str,
    content: str = Form(...),
    files: List[UploadFile] = File(None)
):
    if session_id not in sessions_db:
        return {"error": "Session not found"}
    
    # ファイルの処理
    file_attachments = []
    if files:
        os.makedirs("uploads", exist_ok=True)
        for file in files:
            file_id = str(uuid.uuid4())
            file_path = f"uploads/{file_id}_{file.filename}"
            
            # ファイルを保存
            with open(file_path, "wb") as f:
                f.write(await file.read())
            
            file_attachments.append(
                FileAttachment(
                    id=file_id,
                    name=file.filename,
                    type=file.content_type,
                    url=f"/uploads/{file_id}_{file.filename}",
                    size=os.path.getsize(file_path)
                )
            )
    
    # メッセージを作成
    message = Message(
        id=str(uuid.uuid4()),
        role="user",
        content=content,
        timestamp=datetime.now(),
        files=file_attachments if file_attachments else None
    )
    
    messages_db[session_id].append(message)
    
    # WebSocket経由でメッセージを配信
    await manager.broadcast(
        session_id,
        {"type": "message", "data": json.loads(message.json())}
    )
    
    # エージェントの状態を「計画中」に変更
    agent_state_db[session_id] = AgentState.planning
    await manager.broadcast(
        session_id,
        {"type": "agent_state", "data": agent_state_db[session_id]}
    )
    
    # 非同期でエージェントのレスポンスをシミュレート
    asyncio.create_task(simulate_agent_response(session_id, content))
    
    return message

async def simulate_agent_response(session_id: str, user_content: str):
    """
    AIエージェントがタスクを実行するメイン処理
    """
    if session_id not in sessions_db:
        print(f"エラー: セッションID {session_id} が見つかりません")
        return

    session = sessions_db[session_id]
    
    # エージェントの状態を更新
    agent_state_db[session_id] = AgentState.thinking
    await manager.broadcast(
        session_id,
        {"type": "agent_state", "data": AgentState.thinking}
    )

    try:
        # 簡単なテストリクエストでOllamaの接続を確認
        test_success = await test_ollama_simple_request()
        if not test_success:
            print("警告: Ollamaテストリクエストが失敗しました。処理を継続しますが注意が必要です。")
            
            # テスト失敗の通知アクションを記録
            notification_action = AgentAction(
                id=str(uuid.uuid4()),
                session_id=session_id,
                type=AgentActionType.notify,
                description="Ollamaテスト接続の問題",
                details={
                    "message": "Ollamaサーバーとの接続テストに失敗しました。処理を続行しますが、エラーが発生する可能性があります。"
                },
                created_at=datetime.now()
            )
            agent_actions_db[session_id].append(notification_action)
            await manager.broadcast(
                session_id,
                {"type": "agent_action", "data": json.loads(notification_action.json())}
            )
        
        # タスク解析アクションを記録
        analysis_action = AgentAction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=AgentActionType.analysis,
            description="タスク解析開始",
            details={
                "task": user_content[:100] + ("..." if len(user_content) > 100 else ""),
                "model": session.model_id
            },
            created_at=datetime.now()
        )
        agent_actions_db[session_id].append(analysis_action)
        await manager.broadcast(
            session_id,
            {"type": "agent_action", "data": json.loads(analysis_action.json())}
        )
        
        # タスクを解析して実行ステップに分解
        print(f"タスク解析開始 - モデル: {session.model_id}, タスク: {user_content[:50]}...")
        result = await analyze_task(session.model_id, user_content)
        
        if not result["success"]:
            # タスク解析に失敗した場合
            print(f"タスク解析失敗: {result.get('error', '不明なエラー')}")
            
            # エラー通知アクションを記録
            error_action = AgentAction(
                id=str(uuid.uuid4()),
                session_id=session_id,
                type=AgentActionType.notify,
                description="タスク解析失敗",
                details={
                    "error": result.get('error', '不明なエラー')
                },
                created_at=datetime.now()
            )
            agent_actions_db[session_id].append(error_action)
            await manager.broadcast(
                session_id,
                {"type": "agent_action", "data": json.loads(error_action.json())}
            )
            
            error_message = Message(
                id=str(uuid.uuid4()),
                role="assistant",
                content=f"申し訳ありませんが、タスクの解析に失敗しました。\n\nエラー詳細: {result.get('error', '不明なエラー')}",
                timestamp=datetime.now(),
                files=None
            )
            messages_db[session_id].append(error_message)
            await manager.broadcast(
                session_id,
                {"type": "message", "data": json.loads(error_message.json())}
            )
            
            # エージェントの状態を更新
            agent_state_db[session_id] = AgentState.idle
            await manager.broadcast(
                session_id,
                {"type": "agent_state", "data": AgentState.idle}
            )
            return
        
        # タスク解析結果から情報を抽出
        plan = result["plan"]
        task_title = plan.get("thought", "新しいタスク")[:50]
        steps = plan.get("steps", [])
        
        # タスク解析成功のアクションを記録
        analysis_success_action = AgentAction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=AgentActionType.analysis,
            description="タスク解析完了",
            details={
                "thought": task_title,
                "steps_count": len(steps)
            },
            created_at=datetime.now()
        )
        agent_actions_db[session_id].append(analysis_success_action)
        await manager.broadcast(
            session_id,
            {"type": "agent_action", "data": json.loads(analysis_success_action.json())}
        )
        
        # タスクを作成
        now = datetime.now()
        task = Task(
            id=str(uuid.uuid4()),
            session_id=session_id,
            title=task_title,
            description=user_content,
            status=TaskStatus.in_progress,
            created_at=now,
            updated_at=now
        )
        
        tasks_db[session_id].append(task)
        await manager.broadcast(
            session_id,
            {"type": "task", "data": json.loads(task.json())}
        )
        
        # 確認メッセージを送信
        confirm_message = Message(
            id=str(uuid.uuid4()),
            role="assistant",
            content=f"タスク「{task_title}」を実行します。以下のステップで進めます：\n\n" + 
                   "\n".join([f"{i+1}. {step['description']}" for i, step in enumerate(steps)]),
            timestamp=datetime.now(),
            files=None
        )
        messages_db[session_id].append(confirm_message)
        await manager.broadcast(
            session_id,
            {"type": "message", "data": json.loads(confirm_message.json())}
        )
        
        # タスクステップを作成
        task_steps_db[task.id] = []
        for i, step_data in enumerate(steps):
            step = TaskStep(
                id=str(uuid.uuid4()),
                task_id=task.id,
                title=step_data.get("title", f"ステップ {i+1}"),
                description=step_data.get("description", f"タスクのステップ {i+1} を実行します"),
                status=TaskStepStatus.pending,
                created_at=now,
                updated_at=now
            )
            task_steps_db[task.id].append(step)
            await manager.broadcast(
                session_id,
                {"type": "task_step", "data": json.loads(step.json())}
            )
            await asyncio.sleep(0.5)
            
        # ここから実際のタスク実行ループを開始
        # エージェントの状態を「実行中」に変更
        agent_state_db[session_id] = AgentState.executing
        await manager.broadcast(
            session_id,
            {"type": "agent_state", "data": AgentState.executing}
        )
        
        # ステップごとの実行結果を保存するリスト
        steps_results = []
        
        # タスクのステップを順番に実行
        for i, (step_obj, step_data) in enumerate(zip(task_steps_db[task.id], steps)):
            # 中断確認
            if agent_state_db[session_id] == AgentState.waiting_for_user:
                # ユーザーによる停止
                pause_message = Message(
                    id=str(uuid.uuid4()),
                    role="assistant",
                    content=f"タスクの実行が一時停止されました。再開するには「再開」ボタンをクリックしてください。",
                    timestamp=datetime.now(),
                    files=None
                )
                messages_db[session_id].append(pause_message)
                await manager.broadcast(
                    session_id,
                    {"type": "message", "data": json.loads(pause_message.json())}
                )
                return
            elif agent_state_db[session_id] == AgentState.idle:
                # ユーザーによる停止
                stop_message = Message(
                    id=str(uuid.uuid4()),
                    role="assistant",
                    content=f"タスクの実行が停止されました。",
                    timestamp=datetime.now(),
                    files=None
                )
                messages_db[session_id].append(stop_message)
                await manager.broadcast(
                    session_id,
                    {"type": "message", "data": json.loads(stop_message.json())}
                )
                return
            
            # ステップの状態を「実行中」に更新
            step_obj.status = TaskStepStatus.in_progress
            step_obj.updated_at = datetime.now()
            await manager.broadcast(
                session_id,
                {"type": "task_step", "data": json.loads(step_obj.json())}
            )
            
            # ステップの実行開始をユーザーに通知
            running_message = Message(
                id=str(uuid.uuid4()),
                role="assistant",
                content=f"ステップ {i+1} を実行中: {step_obj.title}",
                timestamp=datetime.now(),
                files=None
            )
            messages_db[session_id].append(running_message)
            await manager.broadcast(
                session_id,
                {"type": "message", "data": json.loads(running_message.json())}
            )
            
            # アクションタイプをMapする関数
            def map_action_type(action_str):
                action_map = {
                    "shell_command": AgentActionType.command,
                    "read_file": AgentActionType.file,
                    "write_file": AgentActionType.file,
                    "web_fetch": AgentActionType.browser
                }
                return action_map.get(action_str, AgentActionType.other)
            
            # アクションを記録
            action_type = map_action_type(step_data.get("action", ""))
            action = AgentAction(
                id=str(uuid.uuid4()),
                session_id=session_id,
                type=action_type,
                description=f"ステップ {i+1} 実行開始: {step_obj.title}",
                details=step_data.get("params", {}),
                created_at=datetime.now()
            )
            agent_actions_db[session_id].append(action)
            await manager.broadcast(
                session_id,
                {"type": "agent_action", "data": json.loads(action.json())}
            )
            
            # ステップを実行
            print(f"ステップ {i+1} 実行: {step_obj.title}")
            step_result = await execute_step(step_data, session_id)
            
            # 実行結果を保存
            steps_results.append((step_data, step_result))
            
            # ステップの実行結果を分析
            analysis = await analyze_step_result(session.model_id, step_data, step_result)
            
            if step_result["success"]:
                # 成功の場合はステップの状態を「完了」に更新
                step_obj.status = TaskStepStatus.completed
                step_obj.updated_at = datetime.now()
                
                # 成功のアクションを記録
                success_action = AgentAction(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    type=action_type,
                    description=f"ステップ {i+1} 完了: {step_obj.title}",
                    details={
                        "success": True,
                        "step_id": step_obj.id,
                        "result": "success"
                    },
                    created_at=datetime.now()
                )
                agent_actions_db[session_id].append(success_action)
                await manager.broadcast(
                    session_id,
                    {"type": "agent_action", "data": json.loads(success_action.json())}
                )
                
                # 成功メッセージをユーザーに通知
                success_message = Message(
                    id=str(uuid.uuid4()),
                    role="assistant",
                    content=f"ステップ {i+1} が正常に完了しました: {step_obj.title}",
                    timestamp=datetime.now(),
                    files=None
                )
                messages_db[session_id].append(success_message)
                await manager.broadcast(
                    session_id,
                    {"type": "message", "data": json.loads(success_message.json())}
                )
                
                # 実行結果の詳細をユーザーに通知（シェルコマンドの場合は出力を表示）
                if "stdout" in step_result and step_result["stdout"].strip():
                    output_message = Message(
                        id=str(uuid.uuid4()),
                        role="assistant",
                        content=f"出力結果:\n```\n{step_result['stdout']}\n```",
                        timestamp=datetime.now(),
                        files=None
                    )
                    messages_db[session_id].append(output_message)
                    await manager.broadcast(
                        session_id,
                        {"type": "message", "data": json.loads(output_message.json())}
                    )
            else:
                # 失敗の場合はステップの状態を「失敗」に更新
                step_obj.status = TaskStepStatus.failed
                step_obj.updated_at = datetime.now()
                
                # 失敗のアクションを記録
                error_action = AgentAction(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    type=action_type,
                    description=f"ステップ {i+1} 失敗: {step_obj.title}",
                    details={
                        "success": False,
                        "step_id": step_obj.id,
                        "error": step_result.get("error", "不明なエラー")
                    },
                    created_at=datetime.now()
                )
                agent_actions_db[session_id].append(error_action)
                await manager.broadcast(
                    session_id,
                    {"type": "agent_action", "data": json.loads(error_action.json())}
                )
                
                # エラーメッセージをユーザーに通知
                error_message = Message(
                    id=str(uuid.uuid4()),
                    role="assistant",
                    content=f"ステップ {i+1} の実行中にエラーが発生しました: {step_result.get('error', '不明なエラー')}",
                    timestamp=datetime.now(),
                    files=None
                )
                messages_db[session_id].append(error_message)
                await manager.broadcast(
                    session_id,
                    {"type": "message", "data": json.loads(error_message.json())}
                )
                
                # ステップのエラーでタスク全体を中断する場合
                if not analysis.get("continue", False):
                    # タスクの状態を「失敗」に更新
                    task.status = TaskStatus.failed
                    task.updated_at = datetime.now()
                    await manager.broadcast(
                        session_id,
                        {"type": "task", "data": json.loads(task.json())}
                    )
                    
                    # 停止メッセージをユーザーに通知
                    abort_message = Message(
                        id=str(uuid.uuid4()),
                        role="assistant",
                        content=f"エラーが発生したため、タスクの実行を中止します。",
                        timestamp=datetime.now(),
                        files=None
                    )
                    messages_db[session_id].append(abort_message)
                    await manager.broadcast(
                        session_id,
                        {"type": "message", "data": json.loads(abort_message.json())}
                    )
                    
                    # エージェントの状態を「アイドル」に更新
                    agent_state_db[session_id] = AgentState.idle
                    await manager.broadcast(
                        session_id,
                        {"type": "agent_state", "data": AgentState.idle}
                    )
                    return
            
            # ステップの状態を更新
            await manager.broadcast(
                session_id,
                {"type": "task_step", "data": json.loads(step_obj.json())}
            )
            
            # 次のステップに進む前に少し待機
            await asyncio.sleep(1)
        
        # すべてのステップが完了した場合、タスクの完了処理
        task.status = TaskStatus.completed
        task.updated_at = datetime.now()
        await manager.broadcast(
            session_id,
            {"type": "task", "data": json.loads(task.json())}
        )
        
        # 完了アクションを記録
        complete_action = AgentAction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=AgentActionType.notify,
            description="タスク完了",
            details={
                "task_id": task.id,
                "task_title": task_title,
                "total_steps": len(steps),
                "success": True
            },
            created_at=datetime.now()
        )
        agent_actions_db[session_id].append(complete_action)
        await manager.broadcast(
            session_id,
            {"type": "agent_action", "data": json.loads(complete_action.json())}
        )
        
        # タスク完了の要約を生成
        summary = await generate_task_summary(session.model_id, user_content, steps_results)
        
        # 完了メッセージをユーザーに通知
        complete_message = Message(
            id=str(uuid.uuid4()),
            role="assistant",
            content=f"タスク「{task_title}」が完了しました。\n\n{summary}",
            timestamp=datetime.now(),
            files=None
        )
        messages_db[session_id].append(complete_message)
        await manager.broadcast(
            session_id,
            {"type": "message", "data": json.loads(complete_message.json())}
        )
        
        # エージェントの状態を更新
        agent_state_db[session_id] = AgentState.idle
        await manager.broadcast(
            session_id,
            {"type": "agent_state", "data": AgentState.idle}
        )
        
    except Exception as e:
        print(f"エージェント応答の生成中にエラーが発生しました: {str(e)}\n{traceback.format_exc()}")
        
        # エラーアクションを記録
        error_action = AgentAction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=AgentActionType.notify,
            description="エラー発生",
            details={
                "error": str(e),
                "traceback": traceback.format_exc()[:500]
            },
            created_at=datetime.now()
        )
        agent_actions_db[session_id].append(error_action)
        await manager.broadcast(
            session_id,
            {"type": "agent_action", "data": json.loads(error_action.json())}
        )
        
        # エラーメッセージを送信
        error_message = Message(
            id=str(uuid.uuid4()),
            role="assistant",
            content=f"申し訳ありませんが、処理中にエラーが発生しました: {str(e)}",
            timestamp=datetime.now(),
            files=None
        )
        messages_db[session_id].append(error_message)
        await manager.broadcast(
            session_id,
            {"type": "message", "data": json.loads(error_message.json())}
        )
        
        # 実行中のタスクがあれば、状態を「失敗」に更新
        current_tasks = tasks_db.get(session_id, [])
        for task in current_tasks:
            if task.status == TaskStatus.in_progress:
                task.status = TaskStatus.failed
                task.updated_at = datetime.now()
                await manager.broadcast(
                    session_id,
                    {"type": "task", "data": json.loads(task.json())}
                )
        
        # エージェントの状態を更新
        agent_state_db[session_id] = AgentState.idle
        await manager.broadcast(
            session_id,
            {"type": "agent_state", "data": AgentState.idle}
        )

@app.get("/api/tasks", response_model=List[Task])
async def get_tasks(session_id: str):
    if session_id not in tasks_db:
        return []
    return tasks_db[session_id]

@app.get("/api/tasks/{task_id}/steps", response_model=List[TaskStep])
async def get_task_steps(task_id: str):
    if task_id not in task_steps_db:
        return []
    return task_steps_db[task_id]

@app.get("/api/sessions/{session_id}/actions", response_model=List[AgentAction])
async def get_agent_actions(session_id: str):
    if session_id not in agent_actions_db:
        return []
    return agent_actions_db[session_id]

@app.post("/api/sessions/{session_id}/pause")
async def pause_agent(session_id: str):
    if session_id not in agent_state_db:
        return {"error": "Session not found"}
    
    agent_state_db[session_id] = AgentState.waiting_for_user
    await manager.broadcast(
        session_id,
        {"type": "agent_state", "data": agent_state_db[session_id]}
    )
    
    return {"status": "success"}

@app.post("/api/sessions/{session_id}/resume")
async def resume_agent(session_id: str):
    if session_id not in agent_state_db:
        return {"error": "Session not found"}
    
    agent_state_db[session_id] = AgentState.executing
    await manager.broadcast(
        session_id,
        {"type": "agent_state", "data": agent_state_db[session_id]}
    )
    
    return {"status": "success"}

@app.post("/api/sessions/{session_id}/stop")
async def stop_agent(session_id: str):
    if session_id not in agent_state_db:
        return {"error": "Session not found"}
    
    agent_state_db[session_id] = AgentState.idle
    await manager.broadcast(
        session_id,
        {"type": "agent_state", "data": agent_state_db[session_id]}
    )
    
    # 実行中のタスクを失敗に変更
    for task in tasks_db.get(session_id, []):
        if task.status == TaskStatus.in_progress:
            task.status = TaskStatus.failed
            task.updated_at = datetime.now()
            await manager.broadcast(
                session_id,
                {"type": "task", "data": json.loads(task.json())}
            )
    
    return {"status": "success"}

@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    print(f"WebSocket接続リクエスト - セッションID: {session_id}")
    try:
        await manager.connect(websocket, session_id)
        
        # セッションが存在しない場合は作成
        if session_id not in sessions_db:
            print(f"新規セッション作成: {session_id}")
            # モデル一覧を取得して最初のモデルをデフォルトとして使用
            models = await fetch_ollama_models()
            default_model = "llama3" if not models else models[0].id
            print(f"デフォルトモデルを設定: {default_model}")
            
            session = ChatSession(
                id=session_id,
                model_id=default_model,
                title="新しいチャット",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            sessions_db[session_id] = session
            messages_db[session_id] = []
            tasks_db[session_id] = []
            agent_actions_db[session_id] = []
            agent_state_db[session_id] = AgentState.idle
            
            await websocket.send_json({
                "type": "session_created",
                "data": json.loads(session.json())
            })
        
        # 既存のメッセージを送信
        if session_id in messages_db:
            for message in messages_db[session_id]:
                await websocket.send_json({
                    "type": "message",
                    "data": json.loads(message.json())
                })
        
        # 既存のタスクを送信
        if session_id in tasks_db:
            for task in tasks_db[session_id]:
                await websocket.send_json({
                    "type": "task",
                    "data": json.loads(task.json())
                })
                
                # タスクステップを送信
                if task.id in task_steps_db:
                    for step in task_steps_db[task.id]:
                        await websocket.send_json({
                            "type": "task_step",
                            "data": json.loads(step.json())
                        })
        
        # エージェントアクションを送信
        if session_id in agent_actions_db:
            for action in agent_actions_db[session_id]:
                await websocket.send_json({
                    "type": "agent_action",
                    "data": json.loads(action.json())
                })
        
        # エージェントの状態を送信
        if session_id in agent_state_db:
            await websocket.send_json({
                "type": "agent_state",
                "data": agent_state_db[session_id]
            })
        
        try:
            while True:
                message = await websocket.receive_text()
                print(f"WebSocket受信: {message[:50]}...")
                data = json.loads(message)
                
                if data["type"] == "message":
                    user_content = data["content"]
                    print(f"ユーザーメッセージ受信: {user_content[:50]}...")
                    # メッセージをデータベースに保存
                    message = Message(
                        id=str(uuid.uuid4()),
                        role="user",
                        content=user_content,
                        timestamp=datetime.now(),
                        files=None
                    )
                    
                    messages_db[session_id].append(message)
                    await manager.broadcast(
                        session_id,
                        {"type": "message", "data": json.loads(message.json())}
                    )
                    
                    # エージェントの応答を生成
                    asyncio.create_task(simulate_agent_response(session_id, user_content))
                
                elif data["type"] == "model_change":
                    # モデル変更リクエスト
                    model_id = data.get("model_id")
                    if model_id:
                        print(f"モデル変更リクエスト: {model_id}")
                        # 現在のセッションを取得
                        session = sessions_db[session_id]
                        # モデルIDを更新
                        session.model_id = model_id
                        session.updated_at = datetime.now()
                        # 変更を保存
                        sessions_db[session_id] = session
                        
                        # 更新されたセッション情報をブロードキャスト
                        await manager.broadcast(
                            session_id,
                            {"type": "session_updated", "data": json.loads(session.json())}
                        )
                        
                        # システムメッセージを追加
                        system_message = Message(
                            id=str(uuid.uuid4()),
                            role="system",
                            content=f"モデルが {model_id} に変更されました。",
                            timestamp=datetime.now(),
                            files=None
                        )
                        messages_db[session_id].append(system_message)
                        await manager.broadcast(
                            session_id,
                            {"type": "message", "data": json.loads(system_message.json())}
                        )
        
        except WebSocketDisconnect:
            print(f"WebSocket切断: {session_id}")
            manager.disconnect(websocket, session_id)
        
    except Exception as e:
        print(f"WebSocketエラー: {str(e)}")
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
