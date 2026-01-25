"""
向量匹配专项测试
用于测试RAG系统中向量检索和匹配功能
"""
from pathlib import Path
from urllib.parse import quote
import httpx
import yaml
import json
import time
from datetime import datetime


def build_messages(user_text: str, history: list | None = None) -> list:
    history = history or []
    return history + [{"role": "user", "content": user_text}]


def load_request_config() -> dict:
    config_path = Path(__file__).parent / "kb_chat_request.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def call_kb_chat_with_vector_info(question: str, return_direct: bool = True) -> dict:
    """
    调用知识库聊天API并获取向量匹配信息
    """
    config = load_request_config()
    base_url = config["base_url"]
    kb_name = config["kb_name"]
    request_config = config["request"].copy()
    
    # 设置return_direct为True以获取纯净的向量匹配结果
    request_config["return_direct"] = return_direct
    request_config["stream"] = False

    endpoint = f"{base_url}/knowledge_base/local_kb/{quote(kb_name)}/chat/completions"

    payload = {
        **request_config,
        "messages": build_messages(question),
    }

    response = httpx.post(endpoint, json=payload, timeout=60)
    
    # 解析响应
    if response.status_code == 200:
        try:
            import json as json_module
            json_response = json_module.loads(response.text)
            
            # 尝试提取内容
            extracted_content = ""
            if isinstance(json_response, dict) and "choices" in json_response and len(json_response["choices"]) > 0:
                extracted_content = json_response["choices"][0].get("message", {}).get("content", "")
            else:
                extracted_content = str(json_response)
                
            return {
                "status_code": response.status_code,
                "response": json_response,  # 返回解析后的字典
                "raw_response": response,
                "extracted_content": extracted_content
            }
        except Exception as e:
            # 如果解析失败，返回原始响应
            return {
                "status_code": response.status_code,
                "response": response.text,  # 保持原始响应文本
                "raw_response": response,
                "extracted_content": f"Error: {response.text}",
                "parse_error": str(e)
            }
    else:
        return {
            "status_code": response.status_code,
            "response": {"error": response.text},
            "raw_response": response,
            "extracted_content": f"Error: {response.text}"
        }


class VectorMatchingTest:
    """向量匹配专项测试类"""
    
    def __init__(self):
        self.test_results = []
    
    def run_vector_matching_test(self, question: str, expected_docs: list = None, test_name: str = "") -> dict:
        """
        运行向量匹配测试
        """
        print(f"\n执行向量匹配测试: {test_name}")
        print(f"问题: {question}")
        
        start_time = time.time()
        result = call_kb_chat_with_vector_info(question, return_direct=True)
        end_time = time.time()
        
        response_text = result.get("extracted_content", "")
        
        print(f"实际响应: {response_text}")
        
        # 分析源文档信息
        source_docs = []
        response_data = result["response"]
        
        # 检查response_data是否为字典
        if isinstance(response_data, dict):
            # 从docs字段中提取源文档信息
            if "docs" in response_data:
                docs_list = response_data["docs"]
                for doc_item in docs_list:
                    # 解析每个文档项，提取内容和可能的相似度信息
                    doc_text = str(doc_item)
                    doc_info = {
                        "page_content": doc_text,
                        "metadata": {"source": "kb"}
                    }
                    
                    # 尝试从文档文本中提取可能的相似度信息
                    # 检查是否包含评分或质量分数
                    if "quality_score" in doc_text:
                        import re
                        quality_matches = re.findall(r"'quality_score':\s*([0-9.]+)", doc_text)
                        if quality_matches:
                            doc_info["metadata"]["quality_score"] = float(quality_matches[0])
                    
                    # 检查是否包含其他评分信息
                    if "last_updated" in doc_text:
                        import re
                        date_matches = re.findall(r"'last_updated':\s*'([^']+)'", doc_text)
                        if date_matches:
                            doc_info["metadata"]["last_updated"] = date_matches[0]
                            
                    source_docs.append(doc_info)
        elif isinstance(response_data, str):
            # 如果响应是字符串，尝试解析它
            try:
                import json as json_module
                parsed_data = json_module.loads(response_data)
                if isinstance(parsed_data, dict) and "docs" in parsed_data:
                    docs_list = parsed_data["docs"]
                    for doc_item in docs_list:
                        source_docs.append({
                            "page_content": str(doc_item),
                            "metadata": {"source": "kb"}
                        })
            except:
                # 如果无法解析，保持source_docs为空列表
                pass
        
        print(f"匹配到的源文档数量: {len(source_docs)}")
        
        # 分析匹配质量
        matching_analysis = self.analyze_matching_quality(question, source_docs, expected_docs)
        
        test_result = {
            "question": question,
            "test_name": test_name,
            "response_time": end_time - start_time,
            "status_code": result["status_code"],
            "source_documents_count": len(source_docs),
            "source_documents": source_docs,
            "matching_analysis": matching_analysis,
            "raw_response": result["response"]
        }
        
        print(f"匹配分析: {matching_analysis}")
        
        # 保存测试结果
        self.test_results.append(test_result)
        
        return test_result
    
    def analyze_matching_quality(self, question: str, source_docs: list, expected_docs: list = None) -> dict:
        """
        分析向量匹配质量
        """
        analysis = {
            "question_relevance": 0,  # 相关性评分
            "content_relevance": [],  # 每个文档的相关性
            "relevance_found": False,
            "expected_docs_found": 0 if expected_docs else "N/A",
            "total_expected_docs": len(expected_docs) if expected_docs else "N/A"
        }
        
        if not source_docs:
            return analysis
        
        # 根据问题关键词分析文档相关性
        question_lower = question.lower()
        relevant_keywords = []
        
        if "价格" in question or "多少钱" in question or "收费" in question:
            relevant_keywords = ["价格", "收费", "元", "会员价", "标准价", "职工价"]
        elif "失眠" in question or "睡眠" in question or "睡不着" in question:
            relevant_keywords = ["失眠", "睡眠", "小愈机器人", "酸枣仁", "刮痧", "点穴", "调理"]
        elif "会员" in question or "钻石" in question:
            relevant_keywords = ["会员", "钻石", "9880", "权益", "套餐", "折扣"]
        elif "地址" in question or "位置" in question or "赵老师" in question:
            relevant_keywords = ["地址", "位置", "电话", "联系", "西城区", "广益大厦"]
        elif "护眼仪" in question or "试用" in question:
            relevant_keywords = ["护眼仪", "试用", "押金", "0元", "体验"]
        
        # 评估每个文档的相关性
        for i, doc in enumerate(source_docs):
            content = doc.get("page_content", "") if isinstance(doc, dict) else str(doc)
            content_lower = content.lower()
            
            # 计算关键词匹配数量
            keyword_matches = sum(1 for keyword in relevant_keywords if keyword in content_lower)
            
            doc_relevance = {
                "doc_id": i,
                "content_preview": content[:100] + ("..." if len(content) > 100 else ""),
                "keyword_matches": keyword_matches,
                "keywords_found": [kw for kw in relevant_keywords if kw in content_lower],
                "is_relevant": keyword_matches > 0
            }
            
            analysis["content_relevance"].append(doc_relevance)
            
            if keyword_matches > 0:
                analysis["relevance_found"] = True
                analysis["question_relevance"] += keyword_matches
        
        # 检查预期文档
        if expected_docs:
            expected_found = 0
            for expected in expected_docs:
                for doc in source_docs:
                    content = doc.get("page_content", "") if isinstance(doc, dict) else str(doc)
                    if expected.lower() in content.lower():
                        expected_found += 1
                        break
            analysis["expected_docs_found"] = expected_found
        
        return analysis
    
    def run_comprehensive_vector_test(self):
        """
        运行综合向量匹配测试
        """
        print("开始运行综合向量匹配测试...")
        
        # 测试用例1: 价格查询
        self.run_vector_matching_test(
            question="AI天眼筛查多少钱？",
            expected_docs=["50元", "47元", "34元"],
            test_name="价格信息向量匹配测试"
        )
        
        # 测试用例2: 健康方案
        self.run_vector_matching_test(
            question="我最近总是失眠，睡不着，有什么调理方案吗？",
            expected_docs=["失眠", "睡眠", "小愈机器人"],
            test_name="健康方案向量匹配测试"
        )
        
        # 测试用例3: 会员信息
        self.run_vector_matching_test(
            question="我想办个钻石会员，多少钱？包含什么？",
            expected_docs=["钻石会员", "9880元"],
            test_name="会员信息向量匹配测试"
        )
        
        # 测试用例4: 联系方式
        self.run_vector_matching_test(
            question="你们店在哪里？我想预约赵老师。",
            expected_docs=["地址", "电话", "赵老师"],
            test_name="联系方式向量匹配测试"
        )
        
        # 测试用例5: 产品试用
        self.run_vector_matching_test(
            question="那个护眼仪可以试用吗？",
            expected_docs=["护眼仪", "试用", "押金"],
            test_name="产品试用向量匹配测试"
        )
        
        # 生成向量匹配测试报告
        self.generate_vector_matching_report()
        
        # 输出汇总信息
        total = len(self.test_results)
        successful_matches = sum(1 for r in self.test_results if r["matching_analysis"]["relevance_found"])
        
        print(f"\n向量匹配测试完成！")
        print(f"总测试数: {total}")
        print(f"成功匹配相关文档: {successful_matches}")
        print(f"匹配成功率: {successful_matches/total*100:.2f}%")
        
        return self.test_results
    
    def generate_vector_matching_report(self):
        """
        生成向量匹配测试报告
        """
        import os
        # 创建报告目录
        report_dir = "test_reports"
        os.makedirs(report_dir, exist_ok=True)
        
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(report_dir, f"vector_matching_test_report_{timestamp}.json")
        
        # 统计测试结果
        total_tests = len(self.test_results)
        successful_matches = sum(1 for r in self.test_results if r["matching_analysis"]["relevance_found"])
        avg_response_time = sum(r["response_time"] for r in self.test_results) / total_tests if total_tests > 0 else 0
        avg_docs_found = sum(r["source_documents_count"] for r in self.test_results) / total_tests if total_tests > 0 else 0
        
        # 构建报告内容
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_tests": total_tests,
                "successful_matches": successful_matches,
                "match_rate": successful_matches / total_tests if total_tests > 0 else 0,
                "avg_response_time": avg_response_time,
                "avg_docs_found": avg_docs_found
            },
            "test_results": self.test_results
        }
        
        # 写入报告文件
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 生成摘要报告
        summary = f"""
向量匹配专项测试报告
========================
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
总测试数: {total_tests}
成功匹配数: {successful_matches}
匹配成功率: {report['report_metadata']['match_rate']:.2f}%
平均响应时间: {avg_response_time:.2f}秒
平均每项匹配文档数: {avg_docs_found:.2f}个

详细结果请查看: {report_filename}
"""
        
        print(summary)
        
        # 同时生成HTML格式报告
        html_report_filename = os.path.join(report_dir, f"vector_matching_test_report_{timestamp}.html")
        self.generate_html_vector_report(report, html_report_filename)
        
        return report_filename
    
    def generate_html_vector_report(self, report: dict, html_filename: str):
        """
        生成HTML格式的向量匹配测试报告
        """
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>向量匹配专项测试报告</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; padding: 15px; background-color: #e8f4fd; }}
        .test-result {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ border-left: 5px solid #4CAF50; }}
        .failed {{ border-left: 5px solid #f44336; }}
        .details {{ margin-top: 10px; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .doc-item {{ margin: 5px 0; padding: 5px; background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>向量匹配专项测试报告</h1>
        <p>生成时间: {report['report_metadata']['generated_at']}</p>
    </div>
    
    <div class="summary">
        <h2>测试摘要</h2>
        <p><strong>总测试数:</strong> {report['report_metadata']['total_tests']}</p>
        <p><strong>成功匹配数:</strong> {report['report_metadata']['successful_matches']}</p>
        <p><strong>匹配成功率:</strong> {report['report_metadata']['match_rate']:.2f}%</p>
        <p><strong>平均响应时间:</strong> {report['report_metadata']['avg_response_time']:.2f}秒</p>
        <p><strong>平均每项匹配文档数:</strong> {report['report_metadata']['avg_docs_found']:.2f}个</p>
    </div>
    
    <div>
        <h2>详细测试结果</h2>
"""
        
        for i, result in enumerate(report['test_results']):
            css_class = "passed" if result["matching_analysis"]["relevance_found"] else "failed"
            status_text = "匹配成功" if result["matching_analysis"]["relevance_found"] else "匹配失败"
            
            html_content += f"""
        <div class="test-result {css_class}">
            <h3>测试 {i+1}: {result.get('test_name', '未知测试')}</h3>
            <p><strong>问题:</strong> {result.get('question', 'N/A')}</p>
            <p><strong>状态:</strong> {status_text}</p>
            <p><strong>响应时间:</strong> {result.get('response_time', 0):.2f}秒</p>
            <p><strong>匹配文档数:</strong> {result.get('source_documents_count', 0)}</p>
            
            <div class="details">
                <h4>匹配分析:</h4>
                <p><strong>问题相关性评分:</strong> {result['matching_analysis'].get('question_relevance', 0)}</p>
                <p><strong>是否找到相关文档:</strong> {result['matching_analysis'].get('relevance_found', False)}</p>
                
                <h4>匹配的源文档:</h4>
"""
            
            for j, doc in enumerate(result.get('source_documents', [])):
                content_preview = doc.get('page_content', '')[:200] + '...' if len(doc.get('page_content', '')) > 200 else doc.get('page_content', '')
                html_content += f"""
                <div class="doc-item">
                    <p><strong>文档 {j+1}:</strong> {content_preview}</p>
                    <p><strong>元数据:</strong> {doc.get('metadata', {})}</p>
                </div>
"""
            
            html_content += """
            </div>
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
    # 运行向量匹配测试
    tester = VectorMatchingTest()
    tester.run_comprehensive_vector_test()
