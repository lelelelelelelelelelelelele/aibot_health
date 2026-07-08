# Phase 8 Completion Audit Report

Generated: 2026-07-08

## Verdict

本地可完成的 Phase 8 改进已完成并有验证证据。剩余项不是代码继续打磨能证明的事项，而是需要外部状态或交付决策：

1. 启动/连通 KB backend 后跑 live integration，用真实样本校准 score gate 默认阈值。
2. 决定 `frontend` 子仓的既有 `summary.md` 和当前 RAG contract 改动如何提交/推送。
3. 决定 `miniprogram` ahead 12 的子仓提交是否保留/推送，再回父仓更新 gitlink。

## Requirement Audit

| Requirement | Status | Evidence |
| --- | --- | --- |
| 列出问题并排序 | Complete | `phase8_payload_contract_REPORT.md` 的 Ordered Issues 表覆盖 payload drift、pytest guard、架构文档、PNG、submodule、score gate |
| 统一 Web / 小程序 / pytest payload contract | Complete | Web `page.tsx`、小程序 `index.tsx`、pytest `kb_chat_contract.py` 都使用 `model + messages + stream + extra_body` |
| 防止 Python QA 工具绕过 contract | Complete | `test_vector_matching.py`、`test_vector_similarity.py` 改用 `build_kb_chat_payload`; pytest 检查禁止 `**request_config` |
| 更新测试 | Complete | `uv run pytest tests/test_kb_chat.py -q` 得到 `8 passed, 8 skipped` |
| 加入召回证据检查 | Complete | `test_kb_chat.py` 解析 docs/source/quality/similarity evidence；正式业务和医疗边界用例要求 docs |
| 加入健康/医疗边界检查 | Complete | `test_kb_chat_medical_boundary_refuses_surgery` 检查拒绝手术并禁止危险表述 |
| score 分布从记录升级为 gate | Complete locally | `KB_CHAT_REQUIRE_SIMILARITY_SCORES`、`KB_CHAT_MIN_SIMILARITY_SCORE`、`KB_CHAT_MIN_AVG_SIMILARITY_SCORE` 可控制失败条件 |
| 报告输出遵守 Markdown + HTML | Complete | Phase 8、submodule、KB chat、vector matching、vector similarity 报告均已有 Markdown/HTML 路径 |
| 架构文档同步 | Complete | `BLUEPRINT.md`、architecture schema、SVG/HTML 已同步；PNG 因 Cairo 缺失未刷新 |
| submodule 状态可审计 | Complete locally | `scripts/audit_submodules.py` 生成 `submodule_audit_REPORT.json/md/html` |
| live backend 全量验收 | Blocked | 当前 KB backend 不可达，集成用例按现有逻辑 skip |
| 子仓提交/推送与父仓 gitlink 更新 | Blocked | 需要决定并执行子仓提交/推送，之后才可更新父仓 gitlink |

## Current Evidence Snapshot

| Evidence | Result |
| --- | --- |
| `uv run pytest tests/test_kb_chat.py -q` | `8 passed, 8 skipped` |
| `npm run lint` in `frontend` | Passed |
| `python -m py_compile scripts\audit_submodules.py tests\kb_chat_contract.py tests\test_kb_chat.py tests\kb_chat_reporting.py tests\test_vector_matching.py tests\test_vector_similarity.py` | Passed |
| `python scripts\audit_submodules.py --repo E:\project\aibot --out-dir reports` | Passed; wrote JSON/Markdown/HTML |
| `frontend` submodule | ahead 1, dirty 3, no parent pointer drift |
| `miniprogram` submodule | ahead 12, dirty 0, parent pointer drift yes |

## Remaining Decision Path

1. Start or expose the KB backend at the configured test URL.
2. Run `uv run pytest tests/test_kb_chat.py -q` without skips and inspect score summaries.
3. Choose score gate defaults from real samples and document them.
4. In `frontend`, decide whether `summary.md` belongs with the RAG contract commit or a separate cleanup commit.
5. Commit/push `frontend`, then decide and push `miniprogram` ahead commits.
6. Return to parent repo and commit intended gitlink pointers plus reports/docs.
