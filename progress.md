# Manus Clone プロジェクト 進捗管理

## プロジェクト概要
Manus.im/appと同等のAIエージェントツールの開発プロジェクト

## 現在のステータス
- **日時**: 2025-03-22
- **状態**: 問題の原因を特定、修正計画更新
- **優先度**: 高

## 発生している問題

### 1. ~~Unhandled Runtime Error~~ (修正済み)
```
Error: Cannot read properties of undefined (reading 'slice')
Call Stack:
- getActionDescription .next\static\chunks\src_2d8dbe8c._.js (1426:50)
- .next\static\chunks\src_2d8dbe8c._.js (1372:43)
- Array.map (0:0)
- AgentLog .next\static\chunks\src_2d8dbe8c._.js (1331:27)
- ChatContainer .next\static\chunks\src_2d8dbe8c._.js (1698:245)
- Home .next\static\chunks\src_2d8dbe8c._.js (2434:221
```

### 2. タスク解析レスポンスの問題
- 言語が中国語と日本語で切り替わっている問題
- JSONブロックの処理に関する問題

### 3. Ollamaプロセスの異常終了（重要更新）
- **問題の詳細**: タスク実行中にOllamaプロセスが途中で終了する
- **新情報**: 
  - モデルサイズを小さくしても問題が解決しないことを確認（2025-03-22）
  - コマンドラインから直接Ollamaに簡単なプロンプトを送ると正常に応答する（2025-03-22）
- **エージェントログ表示不具合**: エージェントログパネルにアクション情報が正しく表示されない（時間のみ表示）

## エラー分析と修正状況

### 1. AgentLogコンポーネントの問題 ✅ 
`agent-log.tsx`ファイル内のundefined値へのアクセスに関する問題を修正：

**修正内容**:
- `action.payload.command`、`action.payload.url`などのプロパティが存在しない場合に安全に処理するため、デフォルト値とnullチェックを追加
- 各プロパティにアクセスする前にオプショナルチェーンや条件チェックを実装
- 文字列長の確認を追加し、undefinedに対するlengthプロパティのアクセスを防止

### 2. 言語切り替え問題の原因 🔍
サーバーサイドの`main.py`のanalyze_task関数内でのJSONパース処理に問題があることを特定：

```python
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
```

### 3. Ollamaプロセス異常終了の問題（原因特定： 🔍）
**問題の詳細**:
- Ollamaサーバーは起動し、モデルの読み込みも正常に完了している
- APIリクエスト処理中にプロセスが予期せず終了
- サーバーログには`POST "/api/generate"`までは表示されるが、その後の処理が中断
- モデルサイズの変更では解決しない（リソース問題ではない）
- コマンドラインからの直接リクエストでは正常に応答する（Ollamaサーバー自体に問題はない）

**特定された原因**:
アプリケーションサーバー（main.py）からOllamaへのリクエスト処理に問題がある可能性が非常に高い:

1. **リクエスト形式の問題**: 
   - アプリケーションが送信しているプロンプトが不適切または処理できない形式である
   - システムプロンプトやオプションの指定に問題がある

2. **非同期処理のエラー**:
   - FastAPIとhttpxの非同期処理におけるエラーハンドリングが不十分
   - タイムアウト設定が不適切

3. **レスポンス処理の問題**:
   - Ollamaからのレスポンスの解析部分にバグがある

## 対応計画（優先順位更新）

### 1. サーバー-Ollama通信の修正（優先度: 最高）

#### 1.1 `get_ollama_response`関数の改善
```python
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
            response = await client.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
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
```

#### 1.2 プロンプトの内容検証
- シンプルで短いプロンプトテストの追加
- プロンプト内容のサニタイズ処理
- システムプロンプトの最適化（短く明確なものに変更）

### 2. エージェントログ表示の改善（優先度: 中）
- `AgentAction`オブジェクトの生成とフォーマットの確認
- WebSocket通信を通じたアクション通知処理の検証
- ログパネルのUIレンダリング修正

### 3. サーバーサイドのJSONパース改善（優先度: 中）
- より堅牢なJSON抽出処理の実装
- マルチバイト文字のサポート強化
- エラーハンドリングの改善

## タスク進行状況
| No | タスク | 状態 | 完了日 |
|----|-------|------|-------|
| 1 | 進捗管理ファイルの作成 | 完了 | 2025-03-22 |
| 2 | リポジトリ状態の確認 | 完了 | 2025-03-22 |
| 3 | エラー原因の特定（フロントエンド） | 完了 | 2025-03-22 |
| 4 | AgentLogコンポーネントの修正 | 完了 | 2025-03-22 |
| 5 | 言語切り替え問題の原因特定 | 完了 | 2025-03-22 |
| 6 | Ollamaプロセス異常終了の原因特定 | 完了 | 2025-03-22 |
| 7 | `get_ollama_response`関数の改善 | 未着手 | - |
| 8 | プロンプト内容の検証と最適化 | 未着手 | - |
| 9 | エージェントログ表示問題の修正 | 未着手 | - |
| 10 | タスク解析レスポンスの言語問題修正 | 未着手 | - |
| 11 | 総合テストと検証 | 未着手 | - |

## 次のステップ - 具体的な修正計画

### 1. `get_ollama_response`関数の改善実装
前述のコード例を参考に、より堅牢なエラーハンドリングと詳細ログを実装します。

### 2. プロンプト内容の検証
```python
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
```

### 3. システムプロンプトの最適化
現在のシステムプロンプトを単純化し、Ollamaが処理しやすい形式に変更します。

```python
# より単純なシステムプロンプト
SYSTEM_PROMPT = """
あなたはAIエージェントです。ユーザーのタスクを分析し、実行可能なステップに分解してください。
"""
```

これらの修正を実装することで、Ollamaとの通信問題を解決し、アプリケーションの安定性が向上すると期待できます。
