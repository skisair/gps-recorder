
### 依存関係のインストール
```bash
npm install -g azure-functions-core-tools@3 --unsafe-perm true
```

### プロジェクトの作成/関数を作成する
```bash
func init
func new

```

### コードを Azure にデプロイする
```bash
func azure functionapp publish iot-event-handler --python
```