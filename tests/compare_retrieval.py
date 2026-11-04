# -*- coding: utf-8 -*-
"""三种检索方式并排对比: BM25 vs 向量 vs 混合.

用法: python tests/compare_retrieval.py
观察点: 关键词型问题 BM25 是否够用; 语义型(换说法)问题向量是否反超
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.rag import search  # noqa: E402

QUERIES = [
    "冷链一级告警多少分钟内必须响应?",       # 关键词型: 告警/响应直接出现在文档
    "水果在冷库里坏掉了应该找谁处理",         # 语义型: "坏掉"文档里没有, 须理解=质控/告警
    "运费多长时间结一次款",                   # 语义型: "结款"文档里写的是"对账/付款"
    "上报平台失败的单据怎么处理",             # 关键词型: 上报/失败直接命中
    "新司机什么时候可以开始接单",             # 语义型: "接单"=派单权限
]


def first_line(text: str) -> str:
    return text.split("\n")[0].replace("【", "").replace("】", " ")[46:]


for q in QUERIES:
    print(f"\n{'='*62}\n问题: {q}")
    for method in ("bm25", "vector", "hybrid"):
        hits = search(q, k=3, method=method)
        tops = " | ".join(f"{h['doc']}/{h['text'].split(chr(10))[0][46:][:12]}" for h in hits)
        print(f"  [{method:6s}] {tops}")
