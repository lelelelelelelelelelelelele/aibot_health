# SSE 流式响应测试脚本 (PowerShell)
# 用于验证 Android 小程序 SSE 修复是否成功

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SSE 流式响应测试" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# API 配置
$API_URL = "https://api.cpagz.com"
$ENDPOINT = "/knowledge_base/local_kb/health%20clinic/chat/completions"

Write-Host "测试地址: ${API_URL}${ENDPOINT}"
Write-Host ""

# 测试 1: 检查响应头
Write-Host "--- 测试 1: 检查响应头 ---" -ForegroundColor Yellow
Write-Host "期望: 没有 content-encoding: gzip, 有 transfer-encoding: chunked"
Write-Host ""

$response = Invoke-WebRequest -Uri "${API_URL}${ENDPOINT}" `
    -Method POST `
    -Headers @{
        "Content-Type" = "application/json"
        "Accept" = "text/event-stream"
    } `
    -Body '{"model":"qwen3-max","messages":[{"role":"user","content":"你好"}],"stream":true}' `
    -UseBasicParsing

Write-Host "状态码: $($response.StatusCode)"
Write-Host ""
Write-Host "响应头:"
$response.Headers | Format-Table -AutoSize

# 检查关键头
$contentEncoding = $response.Headers["content-encoding"]
$transferEncoding = $response.Headers["transfer-encoding"]

if ($contentEncoding -eq "gzip") {
    Write-Host "❌ 警告: 检测到 gzip 压缩，SSE 可能无法正常工作" -ForegroundColor Red
} else {
    Write-Host "✓ 没有 gzip 压缩" -ForegroundColor Green
}

if ($transferEncoding -like "*chunked*") {
    Write-Host "✓ 检测到 chunked 传输" -ForegroundColor Green
} else {
    Write-Host "⚠ 未检测到 chunked 传输" -ForegroundColor Yellow
}

Write-Host ""

# 测试 2: 流式内容测试
Write-Host "--- 测试 2: 流式内容测试 ---" -ForegroundColor Yellow
Write-Host "这个测试需要在命令行使用 curl 来观察实时流"
Write-Host ""
Write-Host "请运行以下命令观察流式效果:"
Write-Host ""
Write-Host "curl -N -X POST ${API_URL}${ENDPOINT} `" -ForegroundColor Green
Write-Host "  -H `"Content-Type: application/json`" `" -ForegroundColor Green
Write-Host "  -H `"Accept: text/event-stream`" `" -ForegroundColor Green
Write-Host "  -d '{`"model`":`"qwen3-max`",`"messages`":[{`"role`":`"user`",`"content`":`"你好`"}],`"stream`":true}'" -ForegroundColor Green
Write-Host ""
Write-Host "期望: 文字逐字出现，不是等待很久后一次性出现" -ForegroundColor Cyan
Write-Host ""
