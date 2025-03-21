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

# API用のプロンプトテンプレート
SYSTEM_PROMPT = """
あなたはManusというAIエージェントです。ユーザーのタスク指示を解析し、実行する能力を持っています。
以下のツールを使用できます：
1. execute_shell_command - シェルコマンドを実行
2. read_file - ファイルを読み取る
3. write_file - ファイルに書き込む
4. fetch_web_content - Webのコンテンツを取得

まず、ユーザーの指示を分析し、必要なステップに分解してください。
各ステップは具体的なアクションとして表現し、実行可能な形式にしてください。
"""

# Ollamaからレスポンスを取得する関数
async def get_ollama_response(model_id, prompt, system_prompt=SYSTEM_PROMPT, max_tokens=4000):
    """
    Ollamaサーバーからレスポンスを取得する関数
    """
    print(f"Ollamaリクエスト開始 - モデル: {model_id}")
    
    # 設定からURLを取得、またはデフォルト値を使用
    base_url = OLLAMA_API_URL
    url = f"{base_url}/api/generate"
    print(f"Ollamaリクエスト - URL: {url}")
    
    # リクエストデータを準備
    data = {
        "model": model_id,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens
        }
    }
    print(f"Ollamaリクエスト - データ: {json.dumps(data)[:200]}...")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                error_detail = f"HTTPエラー: {response.status_code} - {response.text}"
                print(f"Ollamaリクエストエラー: {error_detail}")
                return f"エラー: {error_detail}"
    except Exception as e:
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Ollamaリクエスト例外: {error_detail}")
        return f"例外発生: {error_detail}"

# タスクを解析して実行ステップに分解する
async def analyze_task(model_id, task_description):
    """
    ユーザーのタスク指示を解析し、実行ステップに分解する
    """
    print(f"タスク解析開始 - モデル: {model_id}, タスク: {task_description[:50]}...")
    prompt = f"""
ユーザーの次のタスクを解析し、実行ステップに分解してください：

{task_description}

最大5つのステップに分けて、JSONフォーマットで返してください：
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
            
            # JSONブロックを抽出する
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                print("JSONブロックを検出しました")
                json_str = json_match.group(1)
            else:
                print("JSONブロックが見つかりません、テキスト全体を解析します")
                json_str = content
            
            # 余分な文字を削除してJSONを解析
            json_str = re.sub(r'^[^{]*', '', json_str)
            json_str = re.sub(r'[^}]*$', '', json_str)
            
            print(f"JSONパース前: {json_str[:100]}...")
            plan = json.loads(json_str)
            print("JSONパース成功")
            return {
                "success": True,
                "plan": plan
            }
        except Exception as e:
            error_msg = f"JSONの解析に失敗しました: {str(e)}"
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
        # タスクを解析して実行ステップに分解
        print(f"タスク解析開始 - モデル: {session.model_id}, タスク: {user_content[:50]}...")
        result = await analyze_task(session.model_id, user_content)
        
        if not result["success"]:
            # タスク解析に失敗した場合
            print(f"タスク解析失敗: {result.get('error', '不明なエラー')}")
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
        
        # エージェントの状態を更新
        agent_state_db[session_id] = AgentState.idle
        await manager.broadcast(
            session_id,
            {"type": "agent_state", "data": AgentState.idle}
        )
        
    except Exception as e:
        print(f"エージェント応答の生成中にエラーが発生しました: {str(e)}\n{traceback.format_exc()}")
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
