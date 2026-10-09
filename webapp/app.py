"""
抖音变现操作系统 — 本地网页版。

把 basic-agent + DouyinOS 包成 Flask 网页，浏览器打开即可使用，数据和模型都在本机。

启动：
    venv/Scripts/python.exe webapp/app.py
然后访问 http://127.0.0.1:5000
"""

import argparse
import os
import sys
import threading

# 项目根目录加入 path，便于 import main / douyin
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from flask import Flask, jsonify, render_template, request  # noqa: E402

MODEL = os.environ.get("DOUYIN_MODEL", "qwen2.5:7b")

app = Flask(__name__)

# 懒加载单例 agent；首次请求才初始化（chromadb 加载要几秒）
_agent = None
_agent_lock = threading.Lock()
_run_lock = threading.Lock()  # 串行化请求，避免共享 memory/工具被并发打乱


def get_agent():
    global _agent
    if _agent is None:
        with _agent_lock:
            if _agent is None:
                from main import build_agent
                _agent = build_agent(model=MODEL)
    return _agent


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "⚠️ 消息不能为空。"}), 400

    agent = get_agent()
    with _run_lock:
        try:
            reply = agent.run(message)
        except Exception as e:
            reply = f"❌ 出错了：{e}"
    return jsonify({"reply": reply})


@app.route("/api/status")
def status():
    from douyin.engine import get_os
    os_ = get_os()
    return jsonify({
        "model": MODEL,
        "active_module": os_.active_module,
        "douyin_state": os_.state,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抖音变现操作系统 网页版")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--model", default=MODEL, help="Ollama 模型名")
    args = parser.parse_args()

    MODEL = args.model  # 更新全局，供 get_agent 使用

    print("\n" + "=" * 52)
    print("  🎬 抖音变现操作系统 网页版")
    print(f"  访问：http://{args.host}:{args.port}")
    print(f"  模型：{MODEL}")
    print("  关闭：Ctrl + C")
    print("=" * 52 + "\n")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
