# ai_chat_robot

主代码目录。

- **人类快速上手** → [../README.md](../README.md)
- **AI / 开发者协作** → [../CLAUDE.md](../CLAUDE.md)

## 一键启动

```bash
pip install -r requirements.txt
python scripts/generate_catalog.py
python sandbox/sync_workspace.py
streamlit run web_app.py
```

（需先在项目根 `../.env` 配置 `DEEPSEEK_API_KEY`）
