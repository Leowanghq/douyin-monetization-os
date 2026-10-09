"""
抖音变现操作系统 — 编排器 + 持久化频道状态。

把 prompts.py 里的 8 个专家模块串成一个「系统」：
- 每个模块对应一个命令（/douyin roadmap、/d1 ...）
- 激活模块时，把当前频道状态注入到提示词里
- 模块产出的决策可用 /douyin set 记录回状态，供后续模块复用
- 状态持久化到 douyin/state.json
"""

import json
import os
from datetime import datetime

from douyin.prompts import MODULES, DEFAULT_STATE

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")


# 一键串联时每个模块的启动提问（状态已通过 persona 注入）
KICKOFFS = {
    "roadmap": "请基于当前状态，输出我的抖音账号从零到变现的完整运营方案：定位、受众、内容支柱、视频格式、上传策略、增长系统、变现计划、每周执行表。",
    "niche": "请帮我选定细分赛道：分析候选赛道、给出排名、差异化定位、受众画像、内容分类，以及前 20 个视频选题。",
    "viral": "请基于已确定的赛道，产出 3 个爆款选题的完整创作方案（钩子、标题、缩略图、脚本、留存设计、CTA）。",
    "algo": "请讲解抖音算法增长逻辑，并针对当前赛道给出发布频率、测试方法、优化策略和转粉机制。",
    "produce": "请设计一套 AI 辅助的抖音制作流水线（选题到发布到一鱼多吃），给出工具、步骤、模板和质检清单。",
    "monetize": "请基于当前阶段，给出分阶段的变现方案（方式、引入时机、优先级、门槛和风险）。",
    "analyze": "请建立频道数据分析与复盘系统（指标字典、周/月复盘框架、优化动作库、复盘模板）。",
    "plan90": "请基于当前已确定的赛道和定位，制定 90 天冲刺变现门槛的详细行动计划。",
}


class DouyinOS:
    """编排 8 个专家模块，维护并共享频道状态。"""

    def __init__(self, state_path: str = STATE_PATH):
        self.state_path = state_path
        self.state = self._load()
        self.active_module = None

    # ── 状态持久化 ───────────────────────────────────────────────

    def _load(self) -> dict:
        """加载状态；不存在或损坏时回退到默认状态（深拷贝）。"""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return {**DEFAULT_STATE, **json.load(f)}
            except Exception as e:
                print(f"[douyin] 状态加载失败，使用默认状态: {e}")
        return json.loads(json.dumps(DEFAULT_STATE))

    def _save(self) -> None:
        self.state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ── 命令入口 ─────────────────────────────────────────────────

    def menu(self) -> str:
        lines = ["🎬 **抖音变现操作系统** — 8 个专家模块：", ""]
        for key, mod in MODULES.items():
            lines.append(f"  /douyin {key:<9}（或 /d{mod['order']}）— {mod['name']}")
        lines += [
            "",
            "其它命令：",
            "  /douyin status     查看当前频道状态",
            "  /douyin set k=v    记录一条决策（如 /douyin set channel.niche=家居收纳）",
            "  /douyin off        退出专家模式，恢复通用助手",
            "  /douyin run        一键串联 8 个模块，自动生成完整方案",
            "",
            "建议顺序：roadmap → niche → viral → algo → produce → monetize → analyze → plan90",
        ]
        return "\n".join(lines)

    def status(self) -> str:
        return (
            "📋 **当前频道状态**\n```json\n"
            + json.dumps(self.state, ensure_ascii=False, indent=2)
            + "\n```"
        )

    def set_state(self, kv: str) -> str:
        """按点路径写入一条决策，例如 channel.niche=家居收纳。"""
        if "=" not in kv:
            return "用法：/douyin set <路径>=<值>，例如 /douyin set channel.niche=家居收纳"
        path, value = kv.split("=", 1)
        path, value = path.strip(), value.strip()
        keys = [k for k in path.split(".") if k]
        if not keys:
            return "❌ 路径为空。"
        node = self.state
        for k in keys[:-1]:
            if not isinstance(node, dict):
                return f"❌ 无法写入：{path} 的中间层级不是对象。"
            node = node.setdefault(k, {})
        node[keys[-1]] = self._coerce(value)
        self._save()
        return f"✅ 已记录：{path} = {value}"

    @staticmethod
    def _coerce(value: str):
        v = value.strip()
        if v.lower() in ("true", "false"):
            return v.lower() == "true"
        if v.startswith("[") and v.endswith("]"):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            return v

    def deactivate(self) -> str:
        self.active_module = None
        return "已退出抖音专家模式，恢复通用助手。"

    def activate(self, key: str) -> tuple[str, str]:
        """激活一个模块，返回 (persona_prompt, 提示语)。"""
        key = key.lower().strip()
        # 支持用序号激活：/d1 ... /d8
        if key in [str(i) for i in range(1, 9)]:
            for k, m in MODULES.items():
                if m["order"] == int(key):
                    key = k
                    break
        # 支持用名称/中文别名激活
        if key not in MODULES:
            for k, m in MODULES.items():
                if key == m["name"].lower() or key in [a.lower() for a in m.get("aliases", [])]:
                    key = k
                    break
        if key not in MODULES:
            return "", f"❌ 未知模块：{key}。可用：{', '.join(MODULES)}"

        self.active_module = key
        mod = MODULES[key]
        persona = self._render_persona(key)
        reply = (
            f"🎬 已激活模块 {mod['order']}「{mod['name']}」。\n"
            f"现在直接输入你的需求（例如：我的赛道是 XX，帮我分析），"
            f"或先用 /douyin set 补充频道信息。\n退出用 /douyin off。"
        )
        return persona, reply

    def _render_persona(self, key: str) -> str:
        """把模块提示词 + 当前状态拼成 secondary system prompt。"""
        mod = MODULES[key]
        state_block = json.dumps(self.state, ensure_ascii=False, indent=2)
        return (
            f"{mod['prompt']}\n\n"
            f"══════════════════════════════════════\n"
            f"【系统注入 · 当前频道状态】\n{state_block}\n"
            f"══════════════════════════════════════\n\n"
            f"请基于以上状态展开分析。状态里为空/占位的字段说明尚未确定，"
            f"请在你的回答中给出建议并标注推荐值。\n"
            f"回答末尾请用「## 状态更新」输出一段 JSON，列出本次产出的关键决策"
            f"（字段尽量贴合上面的状态结构），方便系统记录。"
        )


    # ── 一键串联 ─────────────────────────────────────────────────

    def run_all(self, agent) -> str:
        """依次跑完 8 个模块，状态自动传递，最终生成完整方案报告。"""
        print("\n🚀 开始一键串联 8 个模块（每个模块调用一次本地模型，请耐心等待）...\n")
        report = ["# 抖音变现完整方案", ""]
        for key, mod in MODULES.items():
            print(f"[{mod['order']}/8] 正在生成「{mod['name']}」...")
            persona, _ = self.activate(key)
            agent.set_persona(persona)
            # 每个模块独立上下文：状态已通过 persona 注入，避免历史互相污染
            agent.memory.clear()
            try:
                response = agent.run(KICKOFFS.get(key, "请直接输出完整分析结果。"))
            except Exception as e:
                response = f"（模块生成失败：{e}）"
            parsed = self._extract_state_update(response)
            if parsed:
                self._merge_state(parsed)
                self._save()
                print("    ↳ 已提取「状态更新」并落库")
            else:
                print("    ↳ 未提取到结构化状态（可稍后用 /douyin set 手动补）")
            report.append(f"\n\n---\n\n## 模块{mod['order']}：{mod['name']}\n\n{response}")

        report.append(
            "\n\n---\n\n## 最终频道状态\n\n```json\n"
            + json.dumps(self.state, ensure_ascii=False, indent=2)
            + "\n```"
        )
        path = self._write_report("\n".join(report))
        agent.clear_persona()
        self.active_module = None
        print(f"\n✅ 完成！完整方案已保存到：{path}\n")
        return self._run_summary(path)

    @staticmethod
    def _extract_state_update(text: str):
        """从回复里提取「状态更新」之后的第一个合法 JSON 对象（支持嵌套）。"""
        if not text:
            return None
        idx = text.find("状态更新")
        if idx == -1:
            idx = 0
        start = text.find("{", idx)
        if start == -1:
            return None
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except (json.JSONDecodeError, ValueError):
                        return None
        return None

    def _merge_state(self, incoming: dict) -> None:
        """深合并：把新状态合入现有状态，保留已有字段。"""
        def merge(dst, src):
            for k, v in src.items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    merge(dst[k], v)
                else:
                    dst[k] = v
        merge(self.state, incoming)

    def _write_report(self, content: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"report_{ts}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _run_summary(self, path: str) -> str:
        ch = self.state.get("channel", {})
        mo = self.state.get("monetization", {})
        lines = [
            "🎬 **抖音变现完整方案已生成**",
            f"📄 报告文件：{path}",
            "",
            "**已落库的关键状态**：",
            f"  · 赛道 niche：{ch.get('niche') or '（未确定）'}",
            f"  · 定位 positioning：{ch.get('positioning') or '（未确定）'}",
            f"  · 内容支柱：{ch.get('content_pillars') or '（未确定）'}",
            f"  · 变现方式：{mo.get('streams') or '（未确定）'}",
        ]
        return "\n".join(lines)


_os = None


def get_os() -> DouyinOS:
    """模块级单例，供 agent/core.py 懒加载调用。"""
    global _os
    if _os is None:
        _os = DouyinOS()
    return _os
