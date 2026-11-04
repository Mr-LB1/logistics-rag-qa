# 物流制度知识库 RAG 问答（v1.1）

基于真实物流业务语料（冷链告警/结算/排线/网络货运等 8 篇制度文档）的检索增强问答。

## 架构

```
corpus/*.md --按标题切块(28块)--> data/index.json (文本 + 1024维向量)
                                      |
用户问题 --> 检索(bm25/vector/hybrid) Top4 --> 提示词拼装 --> GLM 生成带出处的答案
```

## 快速开始

```bash
python -m venv .venv && source .venv/Scripts/activate
pip install requests python-dotenv numpy jieba
# .env 配置 ZHIPU_API_KEY
python app/rag.py --with-vectors                 # 建索引(含向量)
python app/ask.py "冷链一级告警多少分钟内必须响应?" # 问答(默认hybrid)
python app/ask.py "新司机什么时候可以开始接单" --method bm25  # 切换检索方式
python tests/compare_retrieval.py                # 三种检索并排对比
```

## 设计决策（面试可讲）

1. **按标题切块**：制度文档天然按节组织，标题作语义锚点（28 块）
2. **BM25 零成本起步**：embedding API 付费（429 实测），先用 BM25 跑通全链路再升级——符合"基线先行"的工程习惯
3. **抗幻觉**：提示词强制"资料没有就说未提及"——已验证通过
4. **检索演进实测**（tests/compare_retrieval.py）：关键词型问题三家都命中；**语义型问题（"水果坏掉了找谁""什么时候能接单"）BM25 检索错文档，向量检索全中，hybrid 兼得**

## Roadmap

- [x] 向量检索（embedding-3 1024 维）+ BM25/向量/混合三路对比
- [ ] 检索评估集：Hit@K 命中率量化三种方式差距
- [ ] 重排序（rerank）提升对比

