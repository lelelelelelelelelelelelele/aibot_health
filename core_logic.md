## 请求体（Request Body）

**messages**
```
history = get_messages_history(ctx.get("history_len", 0))
messages = history + [{"role": "user", "content": prompt}]
```

**extra_body（透传给后端的 KB 参数）**
```
extra_body = dict(
	top_k=kb_top_k,
	score_threshold=score_threshold,
	temperature=ctx.get("temperature"),
	prompt_name=prompt_name,
	return_direct=return_direct,
)
```

**model / stream**
```
llm_model
stream=True
```

## 流式响应处理（Streaming）

```
for d in client.chat.completions.create(
	messages=messages,
	model=llm_model,
	stream=True,
	extra_body=extra_body,
):
	if first:
		chat_box.update_msg("\n\n".join(d.docs), element_index=0, streaming=False, state="complete")
		chat_box.update_msg("", streaming=False)
		first = False
		continue
	text += d.choices[0].delta.content or ""
	chat_box.update_msg(text.replace("\n", "\n\n"), streaming=True)
chat_box.update_msg(text, streaming=False)
```