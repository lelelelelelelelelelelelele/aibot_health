# RAG Project Startup Prompt

你正在 `E:\project\aibot` 这个 RAG Robot / 小愈助手项目中工作。先不要急着改代码，按下面顺序启动上下文：

1. 读取 `BLUEPRINT.md`、`docs/architecture/schema.yaml`、`docs/architecture/frontend_adapters/schema.yaml`，理解系统边界。
2. 检查父仓和两个 submodule 状态：

```powershell
git -C E:\project\aibot status --short --ignore-submodules=none
git -C E:\project\aibot\frontend status --short --branch
git -C E:\project\aibot\miniprogram status --short --branch
git -C E:\project\aibot submodule status --recursive
```

3. 记住：`frontend` 和 `miniprogram` 是 Git submodule，不是普通目录。前端改动要先在子仓提交/推送，再回父仓更新 gitlink pointer。
4. 当前优先 TODO 是 Phase 8：统一 Web / 小程序 / pytest 的 RAG payload contract，目标形态是 `messages + stream + extra_body`。
5. 做任何前端或 RAG API 改动前，先确认三处请求契约是否一致：
   - `frontend/src/app/page.tsx`
   - `miniprogram/src/pages/index/index.tsx`
   - `tests/kb_chat_request.yaml` / `tests/test_kb_chat.py`
6. 不要把父仓里的 `m frontend` 或 `M miniprogram` 当成真实 diff。真实 diff 要进对应子模块查看。
7. 修改后至少更新相关文档或测试；如果涉及架构边界，也同步 `BLUEPRINT.md` 和 `docs/architecture/schema.yaml`。

本轮建议目标：先做只读审计，列出 submodule 状态、payload contract 差异、最小修复路径；得到确认后再实施。
