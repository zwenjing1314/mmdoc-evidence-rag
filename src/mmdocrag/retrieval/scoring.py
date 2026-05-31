from __future__ import annotations

import math
import re
from collections import Counter, defaultdict


# 文本分词
def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", lowered)
    """
    正常情况：如果正则表达式找到了 token，就返回 tokens 列表。
    特殊情况：如果文本里全是标点符号或特殊字符（正则没匹配到任何东西），但文本本身不为空，它就返回整个去除了首尾空格的字符串作为一个单独的 token。
    空文本：如果输入是空的，就返回空列表 []。
    """
    return tokens or [lowered.strip()] if lowered.strip() else []


# BM25: 一个页面中出现了问题里的关键词，并且这些关键词比较有区分度，同时页面长度不过分占便宜，那么 BM25 分数就会更高。
"""
1. 实验数据准备
假设我们的文档库（docs）只有两句话：
    - Doc 0: "万科的营收是100亿"
    - Doc 1: "比亚迪的净利润是50亿"
用户查询（query）是："万科营收"

2. 初始化阶段 (__init__)
在打分之前，程序先做了一些统计工作：
    - 分词后 (self.tokens):
        Doc 0: ['万', '科', '的', '营', '收', '是', '100', '亿'] (长度 doc_len = 8)
        Doc 1: ['比', '亚', '迪', '的', '净', '利', '润', '是', '50', '亿'] (长度 doc_len = 10)
    - 总文档数 (self.doc_count): 2
    - 平均长度 (self.avgdl): (8 + 10) / 2 = 9.0
    - 参数: k1 = 1.5, b = 0.75
    - DF (Document Frequency, 词出现在几个文档里):
        '万': 1 (只在 Doc 0)
        '营': 1 (只在 Doc 0)
        '的': 2 (两个文档都有)
        '亿': 2 (两个文档都有)
        
3. 打分阶段 (score) 逐步执行
现在我们要计算 Query "万科营收" 对 Doc 0 ("万科的营收是100亿") 的分数。
    第一步：处理 Query
    query_tokens = ['万', '科', '营', '收']
    第二步：遍历 Doc 0 进行累加
    程序会逐个检查 Query 里的 token 是否在 Doc 0 里出现。
    
Token 1: "万"
检查存在性：'万' 在 Doc 0 里吗？→ 在。
获取 TF (Term Frequency)：tf['万'] = 1 (出现了1次)。
获取 DF：df = 1 (只有1个文档包含它)。
计算 IDF (逆文档频率)：
公式：math.log(1 + (2 - 1 + 0.5) / (1 + 0.5))
计算：log(1 + 1.5 / 1.5) = log(2) ≈ 0.693
意义：因为“万”字很稀有，所以 IDF 较高。
计算分母 (Denom)：
公式：tf + k1 * (1 - b + b * doc_len / avgdl)
代入：1 + 1.5 * (1 - 0.75 + 0.75 * 8 / 9)
计算：1 + 1.5 * (0.25 + 0.666) ≈ 1 + 1.5 * 0.916 ≈ 2.374
计算该 Token 的得分：
公式：IDF * tf * (k1 + 1) / denom
代入：0.693 * 1 * 2.5 / 2.374 ≈ 0.73

Token 2: "科"
逻辑同上。假设 '科' 也只出现在 Doc 0。
它会再贡献约 0.73 分。
当前总分: 0.73 + 0.73 = 1.46

Token 3: "营"
逻辑同上。假设 '营' 也只出现在 Doc 0。
它会再贡献约 0.73 分。
当前总分: 1.46 + 0.73 = 2.19

Token 4: "收"
逻辑同上。假设 '收' 也只出现在 Doc 0。
它会再贡献约 0.73 分。
最终总分 (Doc 0): 2.19 + 0.73 = 2.92

4. 对比：如果是 Doc 1 ("比亚迪的净利润是50亿")
当程序去算 Query 对 Doc 1 的分数时：
'万'：不在 Doc 1 里 → continue (跳过)
'科'：不在 Doc 1 里 → continue (跳过)
'营'：不在 Doc 1 里 → continue (跳过)
'收'：不在 Doc 1 里 → continue (跳过)
最终总分 (Doc 1): 0.0
"""


class SimpleBM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.tokens = [tokenize(doc) for doc in docs]  # 1. 把所有文档切分成单词列表
        self.k1 = k1  # 控制词频饱和的速度
        self.b = b  # 控制文档长度对分数的影响（防止长文档因为词多就占便宜）
        self.doc_count = len(self.tokens)  # 2. 统计总共有多少个文档
        self.avgdl = sum(len(doc) for doc in self.tokens) / max(
            self.doc_count, 1
        )  # 3. 计算文档的平均长度 (avg document length)

        # 4. 计算 DF (Document Frequency)：每个词出现在了多少个不同的页面里
        self.df: Counter[str] = Counter()
        for doc in self.tokens:
            self.df.update(set(doc))  # 用 set 去重，确保一个词在一个文档里只计一次

    def score(self, query: str) -> list[float]:
        query_tokens = tokenize(query)
        scores = []
        # score(t, d) = IDF(t) * 词频饱和项 * 文档长度惩罚项
        for doc_tokens in self.tokens:
            tf = Counter(doc_tokens)
            doc_len = len(doc_tokens)
            score = 0.0
            for token in query_tokens:
                if token not in tf:
                    continue
                df = self.df.get(token, 0)
                idf = math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))
                denom = tf[token] + self.k1 * (
                    1 - self.b + self.b * doc_len / max(self.avgdl, 1e-9)
                )
                score += idf * tf[token] * (self.k1 + 1) / denom
            scores.append(score)
        return scores


class SimpleTfidf:
    def __init__(self, docs: list[str]):
        self.docs = [tokenize(doc) for doc in docs]
        self.doc_count = len(self.docs)
        self.df: Counter[str] = Counter()
        for doc in self.docs:
            self.df.update(set(doc))
        self.vectors = [self._vector(doc) for doc in self.docs]

    def _idf(self, token: str) -> float:
        return math.log((self.doc_count + 1) / (self.df.get(token, 0) + 1)) + 1

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        total = max(sum(counts.values()), 1)
        return {token: count / total * self._idf(token) for token, count in counts.items()}

    def score(self, query: str) -> list[float]:
        query_vector = self._vector(tokenize(query))
        return [cosine(query_vector, doc_vector) for doc_vector in self.vectors]


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(value * right.get(token, 0.0) for token, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: defaultdict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] += 1.0 / (k + rank)
    return dict(scores)
