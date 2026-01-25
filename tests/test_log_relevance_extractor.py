from __future__ import annotations

import re

import pytest


# Keep the exact sample log so parsing stays stable.
TEST_LOG_CONTENT = r'''[https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings](https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings) "HTTP/1.1 200 OK"
H:\\project\\aibot\\.venv\\lib\\site-packages\\langchain_core\\[vectorstores.py:330](http://vectorstores.py:330/): UserWarning: Relevance scores must be between 0 and 1, got [(Document(page_content='"}, {"rule_name": "0元试用", "description": "新款产品（如护眼仪）付押金体验，提交测评后全额返押金并送积分。"}, {"rule_name": "AI健康初筛体验包", "description": "含AI全套检测+生物能量仪30min+报告解读+养生茶，售价29.9元。"}], "last_updated": "2026-01-24"}', metadata={'source': 'org_info.json', 'seq_num': 1, 'id': 'd9260cf9-354f-4748-ad6b-de934f77a9bd'}), 0.025802907828519572), (Document(page_content='"}, {"rule_name": "0元试用", "description": "新款产品（如护眼仪）付押金体验，提交测评后全额返押金并送积分。"}, {"rule_name": "AI健康初筛体验包", "description": "含AI全套检测+生物能量仪30min+报告解读+养生茶，售价29.9元。"}], "last_updated": "2026-01-24"}', metadata={'source': 'membership_rules.json', 'seq_num': 1, 'id': 'cdf05e85-3369-47ca-a06d-f192e434ed0e'}), 0.025802907828519572), (Document(page_content="', 'equipment': ['小愈-AI护眼仪C101'], 'duration': 'null', 'price_info': {'standard': 'null', 'member': 'null', 'staff': 'null'}, 'target_symptom': '眼疲 劳', 'quality_score': 4.5, 'last_updated': '2026-01-24'}, {'service_id': 'svc_007', 'category': '专项综合调理套餐', 'service_name': '筋骨至尊套餐', 'description': '含AI智能检测、小愈机器人脊柱调理(40min)、中医理筋正骨推拿(20min)、科学健身体系指导(10min)。', 'equipment': ['小愈天眼', 'AI小愈机器人'], 'duration': '70-80分 钟', 'price_info': {'standard': '598元', 'member': 'null', 'staff': 'null'}, 'target_symptom': '脊柱/颈肩腰深度调理', 'quality_score': 4.5, 'last_updated': '2026-01-24'}, {'service_id': 'svc_008', 'category': '专项综合调理套餐', 'service_name': '深睡修复套餐', 'description': '含AI智能检测、小愈机器人睡眠调理(30min)、中医点穴安神/头部刮痧(20min)、心理咨询(10min)。", metadata={'source': 'core_service.json', 'seq_num': 1, 'id': 'c39d1dfa-88c6-4e74-ae73-efadad52a829'}), -0.10002600263857242)]
warnings.warn(
H:\\project\\aibot\\.venv\\lib\\site-packages\\langchain_core\\[vectorstores.py:342](http://vectorstores.py:342/): UserWarning: No relevant docs were retrieved using the relevance score threshold 1.0
warnings.warn(
INFO:     127.0.0.1:62455 - "POST /knowledge_base/local_kb/health%20clinic/chat/completions HTTP/1.1" 200 OK
2026-01-25 04:00:31,043 httpx        38308 INFO     HTTP Request: POST [https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings](https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings) "HTTP/1.1 200 OK"
2026-01-25 04:00:31,750 httpx        38308 INFO     HTTP Request: POST [https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings](https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings) "HTTP/1.1 200 OK"
2026-01-25 04:00:32,038 httpx        38308 INFO     HTTP Request: POST [https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings](https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings) "HTTP/1.1 200 OK"
H:\\project\\aibot\\.venv\\lib\\site-packages\\langchain_core\\[vectorstores.py:330](http://vectorstores.py:330/): UserWarning: Relevance scores must be between 0 and 1, got [(Document(page_content='"}, {"rule_name": "0元试用", "description": "新款产品（如护眼仪）付押金体验，提交测评后全额返押金并送积分。"}, {"rule_name": "AI健康初筛体验包", "description": "含AI全套检测+生物能量仪30min+报告解读+养生茶，售价29.9元。"}], "last_updated": "2026-01-24"}', metadata={'source': 'org_info.json', 'seq_num': 1, 'id': 'd9260cf9-354f-4748-ad6b-de934f77a9bd'}), -0.18190451665329221), (Document(page_content='"}, {"rule_name": "0元试用", "description": "新款产品（如护眼仪）付押金体验，提交测评后全额返押金并送积分。"}, {"rule_name": "AI健康初筛体验包", "description": "含AI全套检测+生物能量仪30min+报告解读+养生茶，售价29.9元。"}], "last_updated": "2026-01-24"}', metadata={'source': 'membership_rules.json', 'seq_num': 1, 'id': 'cdf05e85-3369-47ca-a06d-f192e434ed0e'}), -0.18190451665329221), (Document(page_content='{"personal_membership": [{"level_name": "团体（职工）会员", "price": "工会集采体验包/套餐1次即可", "benefits": ["享受专属职工价（显着下调，如AI筛查34元）", "商城采购套餐卡/购物额外95折"]}, {"level_name": "钻石会员", "price": "9880元/年", "benefits": ["不限次AI检测", "每月1次舌诊与体态评估", "15次主题调理套餐", "4 次科学健身指导", "4次健康营养课", "商城购物85折"]}, {"level_name": "普通个人会员", "price": "无门槛（注册/单次消费）", "benefits": ["享受个人会员价（约标准价9-95折）"]}], "corporate_policy": [{"policy_name": "服务类集采折扣", "details": "50人以上88折，100人以上8折"}, {"policy_name": "商城产品集采折扣", "details": "单项100件以上75折"}, {"policy_name": "低价引流包", "details": "团体会员采购体验包100人以上，单价9.9元"}, {"policy_name": "上门服务", "details": "10000元/次（8小时，限35人）"}, {"policy_name": "健康积分兑换", "details": "支持与工会积分融合，工会支付协议价"}], "marketing_rules": [{"rule_name": "3人成团",', metadata={'source': 'org_info.json', 'seq_num': 1, 'id': 'a1316b6f-5f8a-4d24-b2ba-8691a315faaf'}), -0.2854660669403206)]
warnings.warn(
H:\\project\\aibot\\.venv\\lib\\site-packages\\langchain_core\\[vectorstores.py:342](http://vectorstores.py:342/): UserWarning: No relevant docs were retrieved using the relevance score threshold 1.0
warnings.warn(
INFO:     127.0.0.1:51211 - "POST /knowledge_base/local_kb/health%20clinic/chat/completions HTTP/1.1" 200 OK'''


@pytest.fixture(scope="module")
def extractor():
    mod = pytest.importorskip("log_relevance_extractor")
    return mod.LogRelevanceExtractor()


def _print_entries(entries) -> None:
    print(f"\nFound {len(entries)} relevance score entries:")
    print("=" * 60)
    for i, entry in enumerate(entries, 1):
        print(f"\nEntry {i}:")
        print(f"  Source File: {getattr(entry, 'source_file', None)}")
        print(f"  Similarity Score: {getattr(entry, 'similarity_score', None)}")
        print(f"  Quality Score: {getattr(entry, 'quality_score', None)}")
        doc = getattr(entry, 'document_content', '') or ''
        print(f"  Content Preview: {doc[:100]}...")
        print(f"  Timestamp: {getattr(entry, 'timestamp', None)}")
        print(f"  Metadata: {getattr(entry, 'metadata', None)}")


def test_parse_log_content_prints(extractor):
    entries = extractor.parse_log_content(TEST_LOG_CONTENT)
    _print_entries(entries)

    assert isinstance(entries, list)
    assert len(entries) >= 1

    # Basic sanity for first entry
    e0 = entries[0]
    assert isinstance(getattr(e0, "similarity_score", None), float)
    assert isinstance(getattr(e0, "document_content", ""), str)


def test_generate_summary_report_prints(extractor):
    entries = extractor.parse_log_content(TEST_LOG_CONTENT)

    print("\n" + "=" * 60)
    print("SUMMARY REPORT:")
    print("=" * 60)
    summary = extractor.generate_summary_report(entries)
    print(summary)

    assert isinstance(summary, str)
    assert "Total entries found" in summary or "No relevance score entries" in summary


def test_threshold_warnings_prints(extractor):
    warnings = extractor.extract_threshold_warnings(TEST_LOG_CONTENT)

    print(f"\nFound {len(warnings)} threshold warnings:")
    for w in warnings:
        print(f"  Line {w.get('line_number')}: Threshold {w.get('threshold')}")

    assert isinstance(warnings, list)
    # sample log contains at least one threshold warning
    assert any(float(w.get("threshold")) == 1.0 for w in warnings if "threshold" in w)


def test_malformed_entries_prints(extractor):
    malformed = extractor.handle_malformed_entries(TEST_LOG_CONTENT)

    print(f"\nFound {len(malformed)} malformed entries:")
    for m in malformed[:10]:
        print(f"  Line {m.get('line_number')}: {m.get('issue')}")

    assert isinstance(malformed, list)


def test_output_formats_prints(extractor):
    entries = extractor.parse_log_content(TEST_LOG_CONTENT)

    print("\n" + "=" * 60)
    print("JSON FORMAT (first 2 entries):")
    print("=" * 60)
    json_output = extractor.format_as_json(entries[:2])
    print(json_output)

    print("\n" + "=" * 60)
    print("CSV FORMAT (first 2 entries):")
    print("=" * 60)
    csv_output = extractor.format_as_csv(entries[:2])
    print(csv_output)

    assert isinstance(json_output, str) and json_output.strip()
    assert isinstance(csv_output, str)
    assert re.search(r"similarity_score", csv_output) is not None
