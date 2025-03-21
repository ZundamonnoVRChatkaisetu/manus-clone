# Manus Clone

Manus.im/appと同等の機能を持つAIエージェントツール。ユーザーからのタスク指示を解析し、自動的に実行するWebアプリケーションです。

## 機能概要

### 主な機能
- チャット形式でのタスク指示入力
- AIによるタスク解析と自動実行
- リアルタイムのタスク進行状況表示
- エージェントのアクション履歴表示
- 複数のLLMモデル対応（Ollama経由）

### 技術スタック
- **フロントエンド**: Next.js, React, TypeScript, Tailwind CSS
- **バックエンド**: Python, FastAPI, WebSocket
- **AI**: Ollama（LLMインターフェース）

## インストール方法

### 前提条件
- [Node.js](https://nodejs.org/) (v18以上)
- [Python](https://www.python.org/) (v3.8以上)
- [Ollama](https://ollama.ai/) (インストール済みで実行中)

### バックエンドのセットアップ
```bash
# リポジトリをクローン
git clone https://github.com/ZundamonnoVRChatkaisetu/manus-clone.git
cd manus-clone

# サーバーディレクトリに移動
cd server

# 依存関係のインストール
pip install -r requirements.txt

# サーバーの起動
python main.py
```

### フロントエンドのセットアップ
```bash
# 別のターミナルウィンドウで
cd manus-clone/my-app

# 依存関係のインストール
npm install

# 開発サーバーの起動
npm run dev
```

## 使い方

1. ブラウザで `http://localhost:3000` にアクセス
2. 使用するLLMモデルを選択（Ollamaから利用可能なモデル一覧が表示されます）
3. チャット入力欄にタスク指示を入力（例: 「簡単なメモアプリのプロトタイプを作成して」）
4. AIがタスクを解析し、自動的にステップに分解して実行
5. 右側のパネルでタスクの進行状況とエージェントのアクション履歴を確認

## 主要コンポーネント

### フロントエンド
- **ChatContainer**: メインのチャットインターフェース
- **AgentLog**: エージェントアクションの履歴表示
- **TaskCard**: タスクとその進行状況の表示

### バックエンド
- **FastAPI**: RESTとWebSocketエンドポイントの提供
- **Ollama連携**: AIモデルとの通信処理
- **タスク実行エンジン**: AIの指示に基づくシェルコマンド実行など

## トラブルシューティング

### よくある問題と解決法
- **Ollamaエラー**: Ollamaが起動していることを確認。`http://localhost:11434` にアクセスできるか確認
- **WebSocket接続エラー**: サーバーが起動していることを確認
- **モデルロードエラー**: 指定したモデルがOllamaでインストール済みか確認

### ログの確認
- バックエンドのログ: サーバー実行ターミナルを確認
- フロントエンドのログ: ブラウザのコンソールを確認

## 開発者向け情報

### プロジェクト構造
```
manus-clone/
├── my-app/              # フロントエンド（Next.js）
│   ├── src/
│   │   ├── app/         # Next.js アプリルーティング
│   │   ├── components/  # Reactコンポーネント
│   │   ├── lib/         # ユーティリティ関数
│   │   └── types/       # TypeScript型定義
├── server/              # バックエンド（FastAPI）
│   ├── main.py          # サーバーエントリーポイント
│   └── requirements.txt # Pythonの依存関係
└── progress.md          # 開発進捗状況
```

### 貢献方法
1. リポジトリをフォーク
2. 新しいブランチを作成（`git checkout -b feature/your-feature-name`）
3. 変更をコミット（`git commit -am 'Add some feature'`）
4. ブランチをプッシュ（`git push origin feature/your-feature-name`）
5. Pull Requestを作成

## ライセンス
MIT

## 謝辞
- このプロジェクトはManus.im/appの機能を参考にしていますが、公式の製品とは関係ありません。
- フロントエンドUIコンポーネントは[shadcn/ui](https://ui.shadcn.com/)を使用しています。
