# 物流制度知识库 RAG 问答（v1）

基于真实物流业务语料（冷链告警/结算/排线/网络货运等 8 篇制度文档）的检索增强问答。

## 架构

```
corpus/*.md --按标题切块(28块)--> data/index.json
                                      |
用户问题 --> BM25 检索 Top4 --> 提示词拼装 --> GLM 生成带出处的答案
```

## 快速开始

```bash
python -m venv .venv && source .venv/Scripts/activate
pip install requests python-dotenv numpy jieba
# .env 配置 ZHIPU_API_KEY
python app/rag.py                                  # 建索引
python app/ask.py "冷链一级告警多少分钟内必须响应?"   # 问答
```

## v1 设计决策（面试可讲）

1. **BM25 零成本起步**：embedding API 付费（429 实测），制度文档"术语+数字规则"场景 BM25 命中好；`search(method='vector')` 向量路径代码就绪，充值即可切换
2. **按标题切块**：制度文档天然按节组织，标题作语义锚点
3. **抗幻觉**：提示词强制"资料没有就说未提及"——已验证通过

## Roadmap

- [ ] 向量检索（embedding-3）+ BM25 vs 向量 vs 混合检索对比评估
- [ ] 重排序（rerank）提升对比
- [ ] 评估集：检索命中率（Hit@K）+ 答案质量
