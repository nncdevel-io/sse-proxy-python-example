# TASKS

マイルストーン: M1
ゴール: Python 上に3種類の SSE proxy endpoint を実装する

## ワークフロールール

- タスク着手時にステータスを 🚧 に更新する
- タスク完了時にステータスを ✅ に更新する
- DependsOn のタスクがすべて ✅ でないタスクには着手しない

## ステータス表記ルール

| Status | 意味 |
| ---- | ----- |
| ⏳ | 未着手、TODO |
| 🚧 | 作業中、IN_PROGRESS |
| 🧪 | 確認待ち、REVIEW |
| ✅ | 完了、DONE |
| 🚫 | 中止、CANCELLED |

## タスク一覧

| ID | Status | Summary | DependsOn |
| ---- | ---- | ---- | ---- |
| TASK-001 | ✅ | Python プロジェクト骨格を作成する | - |
| TASK-002 | ✅ | Web API と HTTP client 依存関係を追加する | TASK-001 |
| TASK-003 | ✅ | LLM 接続先の設定モデルを実装する | TASK-002 |
| TASK-004 | ✅ | SSE proxy 用のリクエストモデルを定義する | TASK-003 |
| TASK-005 | ✅ | OpenAI SDK endpoint を実装する | TASK-004 |
| TASK-006 | ✅ | httpx endpoint を実装する | TASK-004 |
| TASK-007 | ✅ | aiohttp endpoint を実装する | TASK-004 |
| TASK-008 | ✅ | SSE 中継の共通処理を実装する | TASK-005,TASK-006,TASK-007 |
| TASK-009 | ✅ | エラー応答と切断時処理を実装する | TASK-008 |
| TASK-010 | ✅ | Structured Outputs 用入力を追加する | TASK-009 |
| TASK-011 | ✅ | Docker 実行環境を追加する | TASK-010 |
| TASK-012 | ✅ | proxy 動作確認用の手順を追加する | TASK-011 |
| TASK-013 | ✅ | 単体テストと接続確認テストを追加する | TASK-012 |
| TASK-014 | ✅ | README に起動方法と利用例を記載する | TASK-013 |
| TASK-015 | ✅ | lint とテストで完了確認する | TASK-014 |

## タスク詳細（補足が必要な場合のみ）

### TASK-001

- 補足: 既存リポジトリは README と LICENSE 中心のため、`pyproject.toml`、アプリケーションパッケージ、テストディレクトリを作成する
- 補足: 1つの Python Web アプリに3つの endpoint を同居させる
- 注意: CI/CD 設定は含めない

### TASK-002

- 補足: FastAPI、ASGI server、OpenAI SDK、httpx、aiohttp、テスト関連の依存関係を追加する
- 注意: バージョン固定方法はプロジェクトの Python 管理方針に合わせる

### TASK-003

- 補足: `base_url`、`api_key`、`model` をサーバ側の環境変数または設定ファイルから読む
- 注意: API key をブラウザ、SSE、ログへ出さない
- 注意: ローカル Ollama の既定例は `http://localhost:11434/v1/` とする

### TASK-004

- 補足: 通常テキスト入力と Structured Outputs 用スキーマ入力を扱える形にする
- 注意: クライアントから API key を受け取らない

### TASK-005

- 補足: URL は `/openai-python/responses` とする
- 補足: 公式 Python SDK 経由で LLM に接続する
- 注意: OpenAI 互換 `base_url` で動くかを接続確認対象に含める

### TASK-006

- 補足: URL は `/httpx/responses` とする
- 補足: LLM 側の `/responses` に `stream: true` を送る
- 注意: stateful Responses の機能には依存しない

### TASK-007

- 補足: URL は `/aiohttp/responses` とする
- 補足: aiohttp の client streaming で LLM 側 SSE を受け取る
- 注意: httpx 実装との差分が分かるように責務を分ける

### TASK-008

- 補足: OpenAI 互換 server から受けた SSE event を原則そのまま中継する
- 注意: 3つの endpoint は `text/event-stream` を返す

### TASK-009

- 補足: LLM 側と client 側の切断、非 2xx 応答、JSON 不正を扱う
- 注意: API key、認証ヘッダー、上流の詳細すぎるエラー本文を不用意に返さない

### TASK-010

- 補足: JSON schema を proxy request から LLM request へ渡せるようにする
- 注意: schema の妥当性検証は最小限に留める

### TASK-011

- 補足: ローカル実行とコンテナ実行の両方を確認できる構成にする
- 注意: イメージ内に API key を埋め込まない

### TASK-012

- 補足: Ollama と OpenAI API の両方を curl で確認できる手順にする
- 補足: 3つの endpoint へ同じ payload を投げて比較する手順を含める
- 注意: `curl -N` で SSE が逐次表示されることを確認条件にする

### TASK-013

- 補足: OpenAI 実 API を叩かないテストを基本にする
- 注意: Ollama または実 API の接続確認は環境変数がある場合のみ実行できる形にする

### TASK-014

- 補足: ローカル起動、Docker 起動、各 endpoint の curl 例を README に記載する
- 注意: API key の設定例は環境変数を使う

### TASK-015

- 補足: Python の lint、型チェック、テスト、必要に応じて接続確認を実行する
- 注意: 環境変数がない接続確認はスキップ理由を記録する

## Backlog一覧

| ID | Status | Summary | DependsOn |
| ---- | ---- | ---- | ---- |

## Backlog詳細（補足が必要な場合のみ）
