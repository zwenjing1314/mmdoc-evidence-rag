# 项目交接说明：mmdoc-evidence-rag

## 1. 项目目标

这是周文静的毕业论文主仓库，研究主题是多模态长文档检索。目标不是复现 ColPali 后就结束，而是：

```text
完成 ColPali 官方复现
-> 阅读后续视觉文档检索、结构建模、视觉文本融合和检索训练论文
-> 根据实验诊断确定一个可验证的小论文问题和方法
-> 将小论文方法扩展为毕业论文
```

不要提前假设最终网络、模块或损失函数。它们必须由复现结果、错误案例和文献证据共同决定。

## 2. 已完成的官方 ColPali 复现

官方源码单独放在：

```text
C:\Users\WenJing\Documents\WorkTransfer\colpali-official-repro
```

官方模型：`vidore/colpali`。官方基础模型：`vidore/colpaligemma-3b-mix-448-base`。

Windows RTX 3080 Ti 12GB 上已完成 ViDoRe V1 10 个测试集的全量推理评测：

- 工具：`vidore-benchmark==5.0.0`
- 数据集合：`vidore/vidore-benchmark-667173f98e70a1c0fa4db00d`
- 数据格式：`qa`
- 三个 batch：均为 `1`
- 宏平均 nDCG@5：`80.00%`
- 结果 JSON：官方复现仓库的 `outputs/colpali_full/`
- 详细记录：`docs/reproduction/colpali_vidore_v1_reproduction_20260830.md`

官方 README 的公开值为 81.3。80.00% 与其不完全一致，主要可能来自数据 collection、benchmark 版本和依赖版本差异；当前应表述为“在当前 ViDoRe V1 collection 上完成可复查的官方 checkpoint GPU 评测复现”。

官方复现环境与主项目环境分开：

- `vidore-eval`：官方 `vidore-benchmark` 全量评测。
- `colpali`：主项目中的 ColPali + MMDocIR 接入。
- `base`：不要用于实验。

## 3. 主仓库已有基础

主仓库已经有 MMDocIR 数据适配、页面/布局节点/query/gold 读取、BM25、BGE-M3 Dense、Hybrid、统一评价和结果保存机制。

已新增或修改的 ColPali 接入文件：

| 文件 | 用途 |
| --- | --- |
| `src/mmdocrag/retrieval/colpali.py` | 加载 `vidore/colpali`，编码页面图片和 query，执行 MaxSim 排序；需要 CUDA |
| `src/mmdocrag/retrieval/pipeline.py` | 注册 `colpali_page` 检索器 |
| `configs/experiments/mmdocir_colpali.yaml` | MMDocIR 全量 ColPali 配置 |
| `configs/experiments/mmdocir_colpali_smoke.yaml` | 单文档快速验证配置 |
| `src/mmdocrag/datasets/adapters.py` | 从 MMDocIR parquet 的 `image_binary` 生成页面 JPEG，并保存 `page_image_path` |
| `tests/test_colpali_integration.py` | ColPali 接入测试 |
| `pyproject.toml` | 增加可选依赖 extra：`.[colpali]` |

图片会生成到：`data/interim/mmdocir_evaluation/page_images/`。ColPali 页面 embedding 默认缓存到：`artifacts/colpali/mmdocir_evaluation/vidore_colpali/`。这些数据、模型缓存、embedding 和运行结果不要提交 Git。

## 4. 当前正在做的任务：MMDocIR-ColPali

目的：把已经复现成功的 ColPali 作为主项目中的统一视觉检索 baseline，在 MMDocIR 上和现有 BM25、BGE-M3、Hybrid 使用同一数据层和评价接口比较。

Windows RTX 3080 Ti 上必须在 `colpali` 环境运行：

```powershell
conda activate colpali
cd C:\Users\WenJing\Documents\WorkTransfer\mmdoc-evidence-rag
python -m pip install -e ".[colpali]"

# 先跑一份文档，验证数据、图片、模型和 GPU 链路
mdr prepare --dataset mmdocir --limit-docs 1
mdr retrieve --config configs\experiments\mmdocir_colpali_smoke.yaml
mdr evaluate --run runs\retrieval\mmdocir_colpali_smoke\latest

# smoke 成功后重新准备全量数据，再跑正式实验
mdr prepare --dataset mmdocir
mdr retrieve --config configs\experiments\mmdocir_colpali.yaml
mdr evaluate --run runs\retrieval\mmdocir_colpali\latest
```

先确认 CUDA：

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

应显示 CUDA 可用和 `NVIDIA GeForce RTX 3080 Ti`。如果在 `base` 环境导入 torch 报 DLL 错误，不代表 `colpali` 环境正常性；先激活正确环境再检查。

## 5. 研究解释

ColPali 的原始输入是文本 query 和单页文档图片，输出页面级相关性分数。它使用视觉 patch 多向量、query token 多向量和 ColBERT MaxSim；它不显式输出段落/表格/图像证据区域，也不直接使用 MMDocIR 的 OCR/VLM 节点文本和布局节点。

MMDocIR 用于检验更复杂的长文档证据检索场景：它同时有页面 gold、layout box、区域类型和区域级 gold。先诊断 ColPali 是否出现“正确页面召回但页面内证据区域未定位”的现象，再决定是否设计结构模块。

建议统计四类案例：

- A：正确页面命中，正确区域也命中。
- B：正确页面命中，但正确区域未命中。是布局区域模块的直接动机。
- C：ColPali 页面未命中，但 OCR/VLM 文本方法命中。说明可能需要视觉-文本融合。
- D：页面和区域都失败。分析 query、图片质量或跨页证据问题。

## 6. 毕业论文推进顺序

1. 完成并理解 ColPali 官方复现：方法流程、权重、MaxSim、指标和误差案例。
2. 完成主项目 MMDocIR 上的 ColPali、BM25、BGE-M3、Hybrid 同条件结果。
3. 阅读后续论文，记录表示方式、结构模块、匹配函数、损失、监督和消融结论。
4. 根据 MMDocIR 错误诊断提出 2--3 个候选小方案，不要一次堆叠所有模块。
5. 选择一个核心问题完成小论文：baseline、一个核心改动、公平对比、消融和案例分析。
6. 在小论文有效结果上扩展任务、数据、结构建模、融合、训练和效率分析，形成毕业论文。

当前不要直接开始写完整 StructDocIR，也不要把 MMDocIR evaluation gold 用来训练和最终测试。若训练结构模块，必须有独立 train/dev/test 文档划分或其他训练来源。

## 7. 协作约束

- 代码优先兼容 Windows PowerShell 和 CUDA GPU。
- 不要复制官方 ColPali 仓库到主项目核心源码；只保留复现记录和接入层。
- 修改已有文件前先说明；不要擅自重写已有研究文档。
- 每一步命令都说明目的、所在 Conda 环境和预期输出。
- 研究结论必须以实验结果为依据，不要把候选网络或假设写成已证实结论。
