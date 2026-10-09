# 抖音变现操作系统（Douyin Monetization OS）

集成在 basic-agent 里的一个「专家模式」模块，把 8 个抖音变现专家提示词串成一个可运行、带记忆的系统。

## 使用方式

启动 agent 后，用 `/douyin` 查看菜单：

```text
/douyin            显示 8 个模块菜单
/douyin roadmap    激活模块 1（变现路线图）     或 /d1
/douyin niche      激活模块 2（细分市场）       或 /d2
/douyin viral      激活模块 3（爆款视频引擎）   或 /d3
/douyin algo       激活模块 4（增长与算法）     或 /d4
/douyin produce    激活模块 5（AI 制作流程）    或 /d5
/douyin monetize   激活模块 6（变现机器）       或 /d6
/douyin analyze    激活模块 7（分析优化）       或 /d7
/douyin plan90     激活模块 8（90 天执行）      或 /d8

/douyin status     查看当前频道状态
/douyin set k=v    记录一条决策（如 /douyin set channel.niche=家居收纳）
/douyin off        退出专家模式
/douyin run        一键串联 8 个模块，自动生成完整方案
```

激活某个模块后，直接输入你的需求即可，该模块的角色提示词 + 当前频道状态会被注入到对话里。

## 状态如何互通

8 个模块共享一份频道状态，持久化在 `douyin/state.json`。前一个模块产出的决策可以用 `/douyin set` 记录，后续模块会自动读到。

例如先跑完模块 2（细分）确定赛道后：

```text
/douyin set channel.niche=家居收纳
/douyin set channel.audience=25-35岁一二线城市租房人群
/douyin set content.formats=["口播干货","沉浸式改造"]
```

再激活 `/douyin plan90` 时，系统会把这条赛道和受众信息一并注入，让计划更贴合。

## 建议执行顺序

`roadmap → niche → viral → algo → produce → monetize → analyze → plan90`

## 一键串联

输入 `/douyin run`，系统会依次跑完 8 个模块：

- 每个模块独立生成，前一个模块提取出的「状态更新」会自动合入频道状态，传给后续模块；
- 全程无需手动干预，最后把 8 份结果 + 最终状态汇总成一份 `douyin/report_时间戳.md` 完整方案。

> 提示：本地模型跑 8 个模块耗时较长（7B 模型约几分钟到十几分钟），耐心等待即可。

## 说明

- 本地小模型（如 qwen2.5:7b）不一定能稳定输出末尾的结构化 JSON，属正常现象；关键决策建议手动用 `/douyin set` 记录。
- 状态文件在 `douyin/state.json`，可手动编辑。
