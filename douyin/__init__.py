"""抖音变现操作系统（Douyin Monetization OS）。

把 8 个专家模块（定位 / 细分 / 爆款 / 算法 / 制作 / 变现 / 分析 / 执行）
整合进 basic-agent，通过 /douyin 命令调用，模块间共享频道状态。
"""

from douyin.engine import DouyinOS, get_os

__all__ = ["DouyinOS", "get_os"]
