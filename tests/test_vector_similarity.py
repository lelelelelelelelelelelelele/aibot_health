"""
向量匹配相似度专项测试
用于测试RAG系统中向量检索和匹配功能，特别关注相似度/质量评分
"""
from pathlib import Path
from urllib.parse import quote
import httpx
import yaml
import json
import time
import re
from datetime import datetime


def build_messages(user_text: str, history: list | None = None) -> list:
    history = history or []
    return history + [{"role": "user", "content": user_text}]


def load_request_config() -> dict:
    config_path = Path(__file__).parent / "kb_chat_request.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


class VectorSimilarityTest:
    """向量相似度专项测试类"""
    
    def __init__(self):
        self.test_results = []
    
    def run_similarity_test(self, question: str, test_name: str = "") -> dict:
        """
        运行向量相似度测试
        """
        print(f"\n执行相似度测试: {test_name}")
        print(f"问题: {question}")
        
        # 临时修改配置，将return_direct设为True以获取向量匹配详情
        config = load_request_config()
        base_url = config["base_url"]
        kb_name = config["kb_name"]
        request_config = config["request"].copy()
        request_config["return_direct"] = True
        request_config["stream"] = False

        endpoint = f"{base_url}/knowledge_base/local_kb/{quote(kb_name)}/chat/completions"

        payload = {
            **request_config,
            "messages": build_messages(question),
        }

        start_time = time.time()
        response = httpx.post(endpoint, json=payload, timeout=60)
        end_time = time.time()
        
        if response.status_code != 200:
            print(f"API调用失败: {response.status_code}")
            return None
        
        # 先尝试解析响应
        if response.status_code == 200:
            try:
                response_json = response.json()
            except:
                # 如果解析失败，使用原始文本
                response_json = response.text
        else:
            print(f"API调用失败: {response.status_code}")
            return None
        
        response_text = str(response_json)
        
        print(f"API响应: {response_text[:500]}...")
        
        # 分析源文档和质量评分
        source_docs = []
        
        # 处理响应，无论它是字典还是字符串
        if isinstance(response_json, dict) and "docs" in response_json:
            # 如果是包含docs字段的字典
            docs_list = response_json["docs"]
            for i, doc_item in enumerate(docs_list):
                doc_text = str(doc_item)
                
                # 尝试提取质量评分
                quality_score = None
                quality_matches = re.findall(r"'quality_score':\s*([0-9.]+)", doc_text)
                if quality_matches:
                    try:
                        quality_score = float(quality_matches[0])
                    except:
                        pass
                
                # 尝试提取最后更新时间
                last_updated = None
                date_matches = re.findall(r"'last_updated':\s*'([^']+)'", doc_text)
                if date_matches:
                    last_updated = date_matches[0]
                
                source_docs.append({
                    "doc_id": i + 1,
                    "content_preview": doc_text[:200] + ("..." if len(doc_text) > 200 else ""),
                    "quality_score": quality_score,
                    "last_updated": last_updated,
                    "full_content": doc_text
                })
        elif isinstance(response_json, str):
            # 如果是字符串，尝试查找docs部分
            import json as json_module
            try:
                parsed_data = json_module.loads(response_json)
                if isinstance(parsed_data, dict) and "docs" in parsed_data:
                    docs_list = parsed_data["docs"]
                    for i, doc_item in enumerate(docs_list):
                        doc_text = str(doc_item)
                        
                        # 尝试提取质量评分
                        quality_score = None
                        quality_matches = re.findall(r"'quality_score':\s*([0-9.]+)", doc_text)
                        if quality_matches:
                            try:
                                quality_score = float(quality_matches[0])
                            except:
                                pass
                        
                        # 尝试提取最后更新时间
                        last_updated = None
                        date_matches = re.findall(r"'last_updated':\s*'([^']+)'", doc_text)
                        if date_matches:
                            last_updated = date_matches[0]
                        
                        source_docs.append({
                            "doc_id": i + 1,
                            "content_preview": doc_text[:200] + ("..." if len(doc_text) > 200 else ""),
                            "quality_score": quality_score,
                            "last_updated": last_updated,
                            "full_content": doc_text
                        })
            except:
                # 如果无法解析JSON，查找文本中的质量评分
                # 先简单地将整个响应作为文档
                quality_matches = re.findall(r"'quality_score':\s*([0-9.]+)", response_text)
                if quality_matches:
                    quality_score = float(quality_matches[0]) if len(quality_matches) > 0 else None
                    source_docs.append({
                        "doc_id": 1,
                        "content_preview": response_text[:200] + ("..." if len(response_text) > 200 else ""),
                        "quality_score": quality_score,
                        "last_updated": None,
                        "full_content": response_text
                    })
        
        print(f"匹配到的源文档数量: {len(source_docs)}")
        for doc in source_docs:
            print(f"  文档 {doc['doc_id']}: 质量评分={doc['quality_score']}, 更新时间={doc['last_updated']}")
        
        test_result = {
            "question": question,
            "test_name": test_name,
            "response_time": end_time - start_time,
            "status_code": response.status_code,
            "source_documents_count": len(source_docs),
            "source_documents": source_docs,
            "api_response": response_json
        }
        
        # 保存测试结果
        self.test_results.append(test_result)
        
        return test_result
    
    def run_comprehensive_similarity_test(self):
        """
        运行综合相似度测试
        """
        print("开始运行综合相似度测试...")
        
        # 测试用例1: 价格查询
        self.run_similarity_test(
            question="AI天眼筛查多少钱？",
            test_name="价格信息相似度测试"
        )
        
        # 测试用例2: 健康方案
        self.run_similarity_test(
            question="我最近总是失眠，睡不着，有什么调理方案吗？",
            test_name="健康方案相似度测试"
        )
        
        # 测试用例3: 会员信息
        self.run_similarity_test(
            question="我想办个钻石会员，多少钱？包含什么？",
            test_name="会员信息相似度测试"
        )
        
        # 测试用例4: 产品试用
        self.run_similarity_test(
            question="那个护眼仪可以试用吗？",
            test_name="产品试用相似度测试"
        )
        
        # 生成相似度测试报告
        self.generate_similarity_report()
        
        # 输出汇总信息
        total = len(self.test_results)
        total_docs = sum(r["source_documents_count"] for r in self.test_results)
        avg_quality = self.calculate_average_quality()
        
        print(f"\n向量相似度测试完成！")
        print(f"总测试数: {total}")
        print(f"匹配文档总数: {total_docs}")
        print(f"平均质量评分: {avg_quality:.2f}")
        
        return self.test_results
    
    def calculate_average_quality(self):
        """
        计算平均质量评分
        """
        total_score = 0
        total_count = 0
        
        for result in self.test_results:
            for doc in result["source_documents"]:
                if doc["quality_score"] is not None:
                    total_score += doc["quality_score"]
                    total_count += 1
        
        return total_score / total_count if total_count > 0 else 0
    
    def generate_similarity_report(self):
        """
        生成向量相似度测试报告
        """
        import os
        # 创建报告目录
        report_dir = "test_reports"
        os.makedirs(report_dir, exist_ok=True)
        
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(report_dir, f"vector_similarity_test_report_{timestamp}.json")
        
        # 统计测试结果
        total_tests = len(self.test_results)
        total_docs = sum(r["source_documents_count"] for r in self.test_results)
        avg_quality = self.calculate_average_quality()
        avg_response_time = sum(r["response_time"] for r in self.test_results) / total_tests if total_tests > 0 else 0
        
        # 构建报告内容
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_tests": total_tests,
                "total_docs_matched": total_docs,
                "avg_quality_score": avg_quality,
                "avg_response_time": avg_response_time
            },
            "test_results": self.test_results
        }
        
        # 写入报告文件
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 生成摘要报告
        summary = f"""
向量相似度专项测试报告
========================
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
总测试数: {total_tests}
匹配文档总数: {total_docs}
平均质量评分: {avg_quality:.2f}
平均响应时间: {avg_response_time:.2f}秒

详细结果请查看: {report_filename}
"""
        
        print(summary)
        
        # 同时生成HTML格式报告
        html_report_filename = os.path.join(report_dir, f"vector_similarity_test_report_{timestamp}.html")
        self.generate_html_similarity_report(report, html_report_filename)
        
        return report_filename
    
    def generate_html_similarity_report(self, report: dict, html_filename: str):
        """
        生成HTML格式的向量相似度测试报告
        """
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>向量相似度专项测试报告</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; padding: 15px; background-color: #e8f4fd; }}
        .test-result {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .doc-item {{ margin: 5px 0; padding: 5px; background-color: #f9f9f9; }}
        .quality-high {{ color: #4CAF50; font-weight: bold; }}
        .quality-medium {{ color: #FF9800; font-weight: bold; }}
        .quality-low {{ color: #f44336; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>向量相似度专项测试报告</h1>
        <p>生成时间: {report['report_metadata']['generated_at']}</p>
    </div>
    
    <div class="summary">
        <h2>测试摘要</h2>
        <p><strong>总测试数:</strong> {report['report_metadata']['total_tests']}</p>
        <p><strong>匹配文档总数:</strong> {report['report_metadata']['total_docs_matched']}</p>
        <p><strong>平均质量评分:</strong> {report['report_metadata']['avg_quality_score']:.2f}</p>
        <p><strong>平均响应时间:</strong> {report['report_metadata']['avg_response_time']:.2f}秒</p>
    </div>
    
    <div>
        <h2>详细测试结果</h2>
"""
        
        for i, result in enumerate(report['test_results']):
            html_content += f"""
        <div class="test-result">
            <h3>测试 {i+1}: {result.get('test_name', '未知测试')}</h3>
            <p><strong>问题:</strong> {result.get('question', 'N/A')}</p>
            <p><strong>响应时间:</strong> {result.get('response_time', 0):.2f}秒</p>
            <p><strong>匹配文档数:</strong> {result.get('source_documents_count', 0)}</p>
            
            <h4>匹配的源文档:</h4>
"""
            
            for doc in result.get('source_documents', []):
                # 根据质量评分设置样式
                quality_class = ""
                if doc.get('quality_score'):
                    if doc['quality_score'] >= 4.0:
                        quality_class = "quality-high"
                    elif doc['quality_score'] >= 3.0:
                        quality_class = "quality-medium"
                    else:
                        quality_class = "quality-low"
                
                html_content += f"""
            <div class="doc-item">
                <p><strong>文档 {doc.get('doc_id')}:</strong> {doc.get('content_preview', 'N/A')}</p>
                <p><strong>质量评分:</strong> <span class="{quality_class}">{doc.get('quality_score', 'N/A')}</span></p>
                <p><strong>最后更新:</strong> {doc.get('last_updated', 'N/A')}</p>
            </div>
"""
            
            html_content += """
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)


if __name__ == "__main__":
    # 运行向量相似度测试
    tester = VectorSimilarityTest()
    tester.run_comprehensive_similarity_test()
