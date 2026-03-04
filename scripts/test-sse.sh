#!/bin/bash
# SSE 流式响应测试脚本
# 用于验证 Android 小程序 SSE 修复是否成功

echo "========================================"
echo "SSE 流式响应测试"
echo "========================================"
echo ""

# API 配置
API_URL="https://api.cpagz.com"
ENDPOINT="/knowledge_base/local_kb/health%20clinic/chat/completions"

echo "测试地址: ${API_URL}${ENDPOINT}"
echo ""

# 测试 1: 检查响应头
echo "--- 测试 1: 检查响应头 ---"
echo "期望: 没有 content-encoding: gzip, 有 transfer-encoding: chunked"
echo ""

curl -s -D - -X POST "${API_URL}${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"model":"qwen3-max","messages":[{"role":"user","content":"你好"}],"stream":true}' \
  -o /dev/null

echo ""
echo ""

# 测试 2: 流式响应测试
echo "--- 测试 2: 流式响应测试 ---"
echo "期望: 文字逐字出现，不是一次性返回"
echo ""

echo "开始请求（按 Ctrl+C 中断）..."
echo ""

curl -N -X POST "${API_URL}${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"model":"qwen3-max","messages":[{"role":"user","content":"你好"}],"stream":true}' 2>/dev/null | while read -r line; do
    if [[ "$line" == data:* ]]; then
        content=$(echo "$line" | sed 's/^data: //')
        if [ "$content" != "[DONE]" ]; then
            echo -n "."
        fi
    fi
done

echo ""
echo ""
echo "========================================"
echo "测试完成"
echo "========================================"
echo ""
echo "判断标准:"
echo "- 如果在测试 2 中看到连续的 .... 而不是长时间空白后一次性输出，说明修复成功"
echo "- 如果响应头中有 gzip，说明配置未生效"
