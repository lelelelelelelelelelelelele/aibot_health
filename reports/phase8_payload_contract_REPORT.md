# Phase 8 RAG Payload Contract Improvement Report

Generated: 2026-07-08

## Verdict

Phase 8 的最高优先问题已收敛：Web、小程序、pytest 现在都使用 `model + messages + stream + extra_body` 的 RAG payload 形态。

Submodule 交付整理也已收尾：`frontend` 和 `miniprogram` 已分别在子仓提交/推送，父仓 gitlink pointer 已更新到目标提交。

## Ordered Issues

| Priority | Issue | Evidence Before | Status |
| --- | --- | --- | --- |
| P0 | 三端 payload contract 漂移 | Web 和 pytest 把 `top_k`、`score_threshold`、`temperature`、`prompt_name`、`return_direct` 放在顶层；小程序已放在 `extra_body` | Fixed |
| P1 | pytest 没有 contract guard | `tests/test_kb_chat.py` 直接展开 YAML 请求配置，无法阻止 RAG 参数回到顶层 | Fixed |
| P1 | 架构文档仍写“待收敛” | `BLUEPRINT.md` 和 architecture schema 标记 payload 结构需统一 | Fixed |
| P2 | 架构 PNG 未刷新 | Cairo 动态库缺失，`--png` 渲染失败 | Open |
| P2 | submodule 交付边界收尾 | 子仓提交、推送、父仓 gitlink 更新、过时 frontend 汇总文件清理均已完成 | Fixed |
| P2 | score gate 等待真实样本校准 | QA 已有可配置 score gate，但默认不启用硬阈值；需要 live backend 样本选择稳定阈值 | Open |

## Changes Made

| Area | File | Change |
| --- | --- | --- |
| Web client | `frontend/src/app/page.tsx` | Moved RAG controls into `extra_body` while keeping `model`、`messages`、`stream` at the top level |
| pytest fixture | `tests/kb_chat_request.yaml` | Changed YAML request shape to nest RAG controls under `extra_body` |
| pytest code | `tests/kb_chat_contract.py`, `tests/test_kb_chat.py` | Added a shared payload builder, contract tests, retrieval-evidence extraction, and a medical-boundary guard |
| Vector QA scripts | `tests/test_vector_matching.py`, `tests/test_vector_similarity.py` | Switched vector diagnostics to the shared payload builder with `return_direct` under `extra_body` |
| pytest reporting | `tests/kb_chat_reporting.py`, `tests/conftest.py` | Added Markdown report output and included docs/source/score evidence in Markdown/HTML reports |
| Vector reporting | `tests/test_vector_matching.py`, `tests/test_vector_similarity.py` | Added Markdown source reports beside existing JSON/HTML vector diagnostics |
| Web typing | `frontend/src/types/chat.ts` | Updated `ChatRequestConfig` so RAG controls are typed under `extra_body` |
| Submodule audit | `scripts/audit_submodules.py`, `reports/submodule_audit_REPORT.md`, `reports/submodule_audit_REPORT.html` | Added repeatable read-only audit for child repo ahead/dirty state and parent gitlink drift |
| Completion audit | `reports/phase8_completion_audit_REPORT.md`, `reports/phase8_completion_audit_REPORT.html` | Added requirement-by-requirement completion evidence and blocked-item audit |
| Architecture docs | `BLUEPRINT.md`, `docs/architecture/schema.yaml`, `docs/architecture/frontend_adapters/schema.yaml` | Updated contract language from pending convergence to aligned call sites with remaining duplication risk |
| Rendered architecture | `docs/architecture/diagram.svg`, `docs/architecture/diagram.html`, `docs/architecture/frontend_adapters/diagram.svg`, `docs/architecture/frontend_adapters/diagram.html` | Re-rendered SVG/HTML views from updated schemas |

## Effect Difference

| Contract Aspect | Before | After |
| --- | --- | --- |
| Web payload | `model + stream + messages + top_k + score_threshold + ...` | `model + stream + messages + extra_body` |
| Mini Program payload | `model + messages + stream + extra_body` | unchanged; now matches Web and pytest |
| pytest payload | YAML RAG params spread into request top level | payload builder emits `model + stream + messages + extra_body` |
| Drift detection | Manual review only | `test_kb_chat_request_contract_uses_extra_body` fails if RAG keys return to top level; `test_client_payload_call_sites_use_extra_body` checks Web and mini program call sites |
| Local diagnostics | Vector scripts spread request config and could set top-level `return_direct` | Vector scripts call the shared payload builder; pytest checks they do not reintroduce `**request_config` |
| Retrieval evidence | Keyword assertions only | Business and medical-boundary cases require returned docs; reports show docs count, source files, quality scores, and similarity/relevance scores when present |
| Score distribution | Collected for manual review only | Reports include min/avg/max/out-of-range summaries, and env-configurable gates can fail low-score runs |
| Medical boundary | One keyword-style boundary case | Added a focused surgery-refusal guard with forbidden unsafe phrasing |
| KB chat reports | JSON + HTML only | JSON + Markdown editable source + HTML readable report |
| Vector reports | JSON + HTML only | JSON + Markdown editable source + HTML readable report |
| Submodule status | Manual commands and chat summary | Repeatable JSON + Markdown + HTML audit shows recorded commit, current HEAD, ahead/behind, dirty count, and pointer drift |
| Completion audit | Scattered notes across chat and reports | Single Markdown + HTML audit maps each requirement to status and evidence |
| Architecture wording | “待收敛” warning | aligned contract documented, with remaining schema-generation gap noted |

## Verification

| Check | Result | Notes |
| --- | --- | --- |
| `uv run pytest tests/test_kb_chat.py::test_kb_chat_request_contract_uses_extra_body -q` | Passed | 1 passed; `uv` rebuilt the local `.venv` because the previous interpreter path was missing |
| `uv run pytest tests/test_kb_chat.py -q` | Passed with skips | 8 passed, 8 skipped; backend KB service was not reachable, so integration cases skipped by existing logic |
| `python -m py_compile tests\kb_chat_contract.py tests\test_vector_matching.py tests\test_vector_similarity.py` | Passed | Shared helper and vector diagnostics compile |
| `npm run lint` in `frontend` | Passed | Next lint reported no warnings or errors |
| Architecture render without PNG | Passed | SVG/HTML regenerated |
| Architecture render with PNG | Failed | Cairo library is missing locally, so PNG was not regenerated |
| `python scripts\audit_submodules.py --repo E:\project\aibot --out-dir reports` | Passed | Wrote JSON, Markdown, and HTML submodule audit reports |

## Remaining Work

1. Calibrate score gate thresholds from live backend samples: the env-configurable gates exist, but stable default thresholds require real runs.
2. Re-run the KB integration cases when a reachable public or local KB API is available.
