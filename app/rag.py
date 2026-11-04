# -*- coding: utf-8 -*-
"""RAG 核心: 文档分块 -> 索引 -> 检索 -> (问答见 ask.py).

学习路线对应: 90天计划 阶段3 (RAG全链路)
v1 设计取舍(面试可讲):
  - 语料 ~30 个片段, 规模小 -> BM25 本地检索零成本起步; 向量检索(embedding-3)
    代码就绪, 充值后 method='vector' 即可切换, 后续做 hybrid 混合检索对比
  - 切块策略 v1: 按 markdown 标题切块 (制度文档天然按节组织, 语义完整)
  - 检索演进路径: BM25 基线 -> 向量语义 -> 混合(加权融合) —— 正是简历 JD 里的
    "混合检索"能力
"""
import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_KEY = os.environ.get("ZHIPU_API_KEY", "").strip()
if not API_KEY:
    raise RuntimeError("未找到 ZHIPU_API_KEY, 请在 .env 配置")
if not API_KEY.isascii():
    raise RuntimeError("ZHIPU_API_KEY 含非 ASCII 字符(可能是占位符未替换)")

EMBED_URL = "https://open.bigmodel.cn/api/paas/v4/embeddings"
INDEX_PATH = ROOT / "data" / "index.json"


def chunk_documents(corpus_dir: Path) -> list[dict]:
    """按 markdown 标题切块: 每个 ## 小节一个 chunk, 携带文档标题作上下文."""
    chunks = []
    for md_path in sorted(corpus_dir.glob("*.md")):
        doc_title = md_path.stem
        text = md_path.read_text(encoding="utf-8")
        # 按 ## 标题切分, 保留标题行本身 (标题是块的"语义锚点")
        sections = re.split(r"\n(?=## )", text)
        for sec in sections:
            sec = sec.strip()
            if len(sec) < 40:  # 过短的(纯标题/空段)跳过
                continue
            # 块内容 = 文档标题 + 小节文本, 让向量同时编码"属于哪个主题"
            chunks.append({
                "doc": doc_title,
                "text": f"【{doc_title}】{sec}",
            })
    return chunks


def embed_texts(texts: list[str], batch_size: int = 16) -> list[list[float]]:
    """调用智谱 embedding-3 批量向量化. 逐批请求, 带简单重试."""
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for attempt in range(3):
            resp = requests.post(
                EMBED_URL,
                headers={"Authorization": f"Bearer {API_KEY}",
                         "Content-Type": "application/json"},
                json={"model": "embedding-3", "input": batch, "dimensions": 1024},
                timeout=30,
            )
            if resp.status_code == 200:
                break
            if resp.status_code in (429, 500, 502, 503) and attempt < 2:
                import time
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"Embedding 调用失败 HTTP {resp.status_code}: {resp.text[:150]}")
        data = resp.json()["data"]  # [{"embedding": [...], "index": 0}, ...]
        data.sort(key=lambda d: d["index"])  # 保证顺序与输入一致
        all_vectors.extend(d["embedding"] for d in data)
        print(f"  已向量化 {min(i + batch_size, len(texts))}/{len(texts)}")
    return all_vectors


def build_index(with_vectors: bool = False) -> int:
    """构建索引并落盘. 返回片段数.

    with_vectors=False: 仅分块(BM25 用), 零成本
    with_vectors=True:  额外调用 embedding-3 (付费, 账户需有余额)
    """
    chunks = chunk_documents(ROOT / "corpus")
    print(f"切块完成: {len(chunks)} 个片段")
    vectors: list = []
    if with_vectors:
        vectors = embed_texts([c["text"] for c in chunks])
    INDEX_PATH.parent.mkdir(exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps({"chunks": chunks, "vectors": vectors}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"索引已保存: {INDEX_PATH} (含向量: {bool(vectors)})")
    return len(chunks)


if __name__ == "__main__":
    import sys
    build_index(with_vectors="--with-vectors" in sys.argv)


def _tokenize(text: str) -> list[str]:
    """中文分词: jieba + 过滤停用级别的单字符虚词."""
    import jieba
    return [w for w in jieba.lcut(text) if w.strip() and len(w) > 1]


def search_bm25(query: str, k: int = 4) -> list[dict]:
    """BM25 关键词检索 (零成本基线, 不依赖 embedding API).

    制度文档多为"术语+数字规则", BM25 对这类精确词命中效果好.
    """
    import math

    if not INDEX_PATH.exists():
        raise RuntimeError("索引不存在, 请先运行 build_index (python app/rag.py)")
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    chunks = index["chunks"]

    # 建倒文档频率表 (每次现算, 语料小无所谓)
    docs_tokens = [_tokenize(c["text"]) for c in chunks]
    n_docs = len(docs_tokens)
    df: dict[str, int] = {}
    for toks in docs_tokens:
        for w in set(toks):
            df[w] = df.get(w, 0) + 1

    avg_len = sum(len(t) for t in docs_tokens) / n_docs
    k1, b = 1.5, 0.75
    q_tokens = _tokenize(query)
    scores = []
    for toks in docs_tokens:
        tf: dict[str, int] = {}
        for w in toks:
            tf[w] = tf.get(w, 0) + 1
        score = 0.0
        for w in q_tokens:
            if w not in tf:
                continue
            idf = math.log((n_docs - df[w] + 0.5) / (df[w] + 0.5) + 1)
            score += idf * (tf[w] * (k1 + 1)) / (
                tf[w] + k1 * (1 - b + b * len(toks) / avg_len)
            )
        scores.append(score)

    top_idx = sorted(range(n_docs), key=lambda i: scores[i], reverse=True)[:k]
    return [
        {**chunks[i], "score": round(scores[i], 4), "method": "bm25"}
        for i in top_idx if scores[i] > 0
    ]


def search(query: str, k: int = 4, method: str = "bm25") -> list[dict]:
    """检索入口: method = bm25 | vector.

    vector 需要智谱账户有余额(embedding-3 为付费模型), 充值后即可切换对比.
    """
    if method == "bm25":
        return search_bm25(query, k)

    import numpy as np

    if not INDEX_PATH.exists():
        raise RuntimeError("索引不存在, 请先运行 build_index")
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    q_vec = np.array(embed_texts([query])[0])
    mat = np.array(index["vectors"])                     # (N, 1024)
    sims = mat @ q_vec / (np.linalg.norm(mat, axis=1) * np.linalg.norm(q_vec))
    top_idx = np.argsort(sims)[::-1][:k]
    return [
        {**index["chunks"][int(i)], "score": round(float(sims[i]), 4), "method": "vector"}
        for i in top_idx
    ]


if __name__ == "__main__":
    build_index()
