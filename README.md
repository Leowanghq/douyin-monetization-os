# 🎬 抖音变现操作系统（Douyin Monetization OS）

一个基于**本地大模型（Ollama）**的多智能体 AI 应用：8 个专家角色协同工作，为抖音创作者提供从 0 到变现的完整解决方案。支持命令行与网页两种交互方式，全程离线、零成本。

> 核心价值：把「8 个独立提示词」升级成一个**有状态、可编排、可自动串联**的 Agent 系统。

## ✨ 项目亮点

- **多专家编排（Multi-Agent Orchestration）**：定位 → 细分 → 爆款 → 算法 → 制作 → 变现 → 分析 → 执行，8 个专家模块通过共享状态协同，前序决策自动传给后续模块
- **ReAct Agent 引擎**：`Think → Act → Observe` 循环，模型可自主调用工具完成多步任务
- **工具调用（Tool Calling）**：7 个内置工具——网络搜索、文件读写、计算器、日期时间、安全 shell、本地 RAG 检索
- **对话记忆**：短期缓冲 + 长期自动摘要
- **本地 RAG**：基于 ChromaDB + bge-m3 向量模型的知识库检索
- **结构化状态提取**：自动从模型回复中解析「状态更新」JSON（花括号配对解析，支持嵌套）并合并持久化
- **一键串联**：`/douyin run` 依次跑完 8 个模块，自动生成完整方案报告
- **Web UI**：Flask 网页版，浏览器直接操作，markdown 渲染
- **100% 本地免费**：无 API key、无云端、无遥测

## 🏗️ 技术架构

```
用户（CLI / 网页）
      │
      ▼
┌──────────────────────────────┐
│   Agent 核心（ReAct 循环）      │
│   Think → Act → Observe        │
└───────┬──────────────┬─────────┘
        │              │
   ┌────▼────┐     ┌───▼────────┐
   │ 工具注册 │     │  记忆系统    │
   │ 7 个工具 │     │ 短期 + 摘要  │
   └────┬────┘     └────────────┘
        │
   ┌────▼───────────────────────┐
   │  DouyinOS（专家编排层）       │
   │  8 模块 · 状态注入 · 持久化    │
   └────────────────────────────┘
        │
   Ollama（本地大模型 qwen2.5 / deepseek-r1 等）
```

## 🚀 快速开始

### 依赖

- [Ollama](https://ollama.com) 已安装并运行，拉取模型
- Python 3.12+

```bash
ollama pull qwen2.5:7b
ollama pull bge-m3
pip install -r requirements.txt
```

### 命令行版

```bash
python main.py
# 输入 /douyin 查看 8 个专家模块
```

### 网页版

```bash
venv/Scripts/python.exe webapp/app.py
# 浏览器打开 http://127.0.0.1:5000
```

## 🧩 8 个专家模块

| 命令 | 模块 | 功能 |
|---|---|---|
| `/douyin roadmap` | ①变现路线图 | 频道定位、内容支柱、增长与变现全案 |
| `/douyin niche` | ②细分市场 | 赛道分析、差异化定位、前 20 选题 |
| `/douyin viral` | ③爆款引擎 | 钩子、标题、缩略图、完整脚本 |
| `/douyin algo` | ④增长算法 | 推荐机制、测试方法、转粉策略 |
| `/douyin produce` | ⑤AI 制作 | 选题到发布到一鱼多吃的流水线 |
| `/douyin monetize` | ⑥变现机器 | 变现方式、引入时机、门槛 |
| `/douyin analyze` | ⑦分析优化 | 指标字典、周/月复盘框架 |
| `/douyin plan90` | ⑧90 天执行 | 分周计划、里程碑、KPI |

其它命令：`/douyin status`（查状态）、`/douyin set k=v`（记录决策）、`/douyin run`（一键串联）、`/douyin off`（退出）。

## 📸 演示

在 `docs/` 目录下放置截图或录屏，建议覆盖：
- 网页版主界面
- `/douyin run` 一键生成的完整方案报告
- 命令行交互过程

## 📁 项目结构

```
basic-agent/
├── main.py                # CLI 入口
├── agent/                 # Agent 核心
│   ├── core.py            #   ReAct 循环 + 专家模式
│   ├── llm.py             #   Ollama 接口（chat + embed）
│   ├── tools.py           #   工具基类 + 注册表
│   ├── memory.py          #   记忆系统
│   └── logger.py          #   工作日志
├── tools/                 # 7 个内置工具
├── douyin/                # 抖音变现操作系统
│   ├── prompts.py         #   8 个专家模块提示词
│   ├── engine.py          #   DouyinOS 编排器 + 状态持久化
│   └── README.md
├── webapp/                # 网页版
│   ├── app.py             #   Flask 后端
│   └── templates/index.html
└── knowledge/             # RAG 知识库
```

## 🧰 如何扩展

添加自定义工具只需继承 `BaseTool`：

```python
from agent.tools import BaseTool

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "查询城市天气"
    parameters = {"city": {"type": "string", "description": "城市名"}}

    def execute(self, city: str) -> str:
        return f"{city}：晴，25°C"

registry.register(WeatherTool())
```

## License

MIT
