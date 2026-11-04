# -*- coding: utf-8 -*-
"""RAG 问答 CLI: 问题 -> 检索 -> 拼装提示 -> GLM 生成带出处的答案.

用法: python app/ask.py "冷链一级告警多少分钟内响应?"
"""
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.rag import API_KEY, search  # noqa: E402

CHAT_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

SYSTEM_PROMPT = """你是物流公司的制度问答助手。严格依据给定的参考资料回答问题。
规则:
- 只使用参考资料中的信息, 资料里没有的明确说"资料中未提及", 不要编造
- 回答末尾列出依据的资料来源(文档名+小节标题)
- 回答简洁, 分点陈述"""


def ask(question: str, k: int = 4) -> str:
    print(f"\n问题: {question}")
    hits = search(question, k=k)
    print("检索到的片段:")
    for h in hits:
        first_line = h["text"].split("\n")[0][:40]
        print(f"  [{h['score']:.3f}] {h['doc']} | {first_line}")

    context = "\n\n---\n\n".join(h["text"] for h in hits)
    payload = {
        "model": "glm-4-flash",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"参考资料:\n{context}\n\n问题: {question}"},
        ],
        "temperature": 0.1,
    }
    resp = requests.post(
        CHAT_URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=payload, timeout=60,
    )
    resp.raise_for_status()
    answer = resp.json()["choices"][0]["message"]["content"]
    print(f"\n回答:\n{answer}")
    return answer


if __name__ == "__main__":
    ask(" ".join(sys.argv[1:]) or "冷链一级告警的处理时限是什么?")
