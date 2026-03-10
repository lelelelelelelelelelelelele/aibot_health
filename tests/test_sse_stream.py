import requests
import json
import time

url = "https://api.cpagz.com/knowledge_base/local_kb/health%20clinic/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream"
}
data = {
    "model": "Qwen/Qwen3.5-397B-A17B",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": True
}

print("开始请求...", flush=True)
start = time.time()
response = requests.post(url, headers=headers, json=data, stream=True)
first_chunk_time = time.time()
print(f"连接建立: {first_chunk_time - start:.3f}s, 状态码: {response.status_code}", flush=True)

chunk_count = 0
content_chunks = 0
for line in response.iter_lines():
    now = time.time()
    if line:
        chunk_count += 1
        decoded = line.decode('utf-8')
        if 'data:' in decoded and 'ping' not in decoded:
            content_chunks += 1
            elapsed = now - start
            print(f"[{elapsed:.2f}s] Chunk {chunk_count}: {decoded[:100]}", flush=True)
        elif 'ping' in decoded:
            print(f"[{now - start:.2f}s] Ping", flush=True)

    # 只看前几条实际的 data chunk
    if content_chunks >= 5:
        break

print(f"\n总结: {chunk_count} total chunks, {content_chunks} content chunks", flush=True)
print(f"首 chunk 延迟: {first_chunk_time - start:.3f}s", flush=True)
