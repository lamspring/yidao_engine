# -*- coding: utf-8 -*-
"""
易道引擎 HTTP API 服务器 — 供 VS Code 插件调用

用法:
    python api_server.py --port 8765 --mode family --provider deepseek --worldview xiuxian
"""
import sys
import os
import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.config import PipelineConfig, LLMConfig
from pipeline.interactive_runner import InteractiveRunner


# ── CORS 处理器 ──

class CORSRequestHandler(BaseHTTPRequestHandler):
    """支持 CORS 的 HTTP 请求处理器。"""

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        return json.loads(body)

    def log_message(self, fmt, *args):
        # 精简日志，避免刷屏
        print(f"[API] {self.command} {self.path} — {args[1]}")


# ── 路由注册 ──

class Router:
    def __init__(self):
        self.routes = {}
        self.runner = None

    def register(self, method: str, path: str, handler):
        self.routes[(method.upper(), path)] = handler

    def handle(self, handler: CORSRequestHandler):
        parsed = urlparse(handler.path)
        path = parsed.path
        method = handler.command
        key = (method.upper(), path)

        if key not in self.routes:
            handler._send_json(404, {"error": f"未找到路由 {method} {path}"})
            return

        try:
            result = self.routes[key](handler)
            if result is not None:
                handler._send_json(200, result)
        except Exception as e:
            print(f"[API ERROR] {method} {path}: {e}")
            handler._send_json(500, {"error": str(e)})


# ── 全局路由实例 ──

router = Router()


# ── 路由实现 ──

def route_init(handler: CORSRequestHandler):
    """POST /init — 初始化世界。"""
    body = handler._read_json()
    mode = body.get("mode", "family")
    provider = body.get("provider", "deepseek")
    worldview = body.get("worldview")
    style = body.get("style", "polished")
    output_dir = body.get("output_dir", "./outputs")

    if mode == "single":
        cfg = PipelineConfig.default_single()
    elif mode == "dual":
        cfg = PipelineConfig.default_dual()
    else:
        cfg = PipelineConfig.default_family()

    cfg.style = style
    cfg.output_dir = output_dir

    # 加载 LLM 配置（支持传入 api_key 覆盖环境变量）
    api_key = body.get("api_key")
    try:
        cfg.llm = LLMConfig.from_provider(provider, api_key=api_key)
    except Exception as e:
        return {"error": f"LLM 配置加载失败: {e}", "initialized": False}

    # 加载世界观
    if worldview:
        from pipeline.config import WorldViewConfig
        try:
            cfg.worldview = WorldViewConfig.from_file(worldview)
        except Exception as e:
            print(f"[警告] 世界观加载失败: {e}")

    router.runner = InteractiveRunner(cfg, output_dir=output_dir)
    return {"initialized": True, "tick": 0, "mode": mode, "provider": provider}


def route_step(handler: CORSRequestHandler):
    """POST /step — 推进世界。"""
    if router.runner is None:
        return {"error": "世界未初始化，请先调用 POST /init", "initialized": False}
    body = handler._read_json()
    ticks = body.get("ticks", 150)
    result = router.runner.step(ticks)
    return result


def route_explain(handler: CORSRequestHandler):
    """POST /explain — 生成叙事。"""
    if router.runner is None:
        return {"error": "世界未初始化", "initialized": False}
    output = router.runner.explain()
    return {
        "output": output,
        "tick": router.runner.runner.world.tick_count,
        "narrative_count": len(router.runner.narrative_history),
        "tokens_used": router.runner._total_tokens_used,
    }


def route_reroll(handler: CORSRequestHandler):
    """POST /reroll — 重新生成。"""
    if router.runner is None:
        return {"error": "世界未初始化", "initialized": False}
    output = router.runner.reroll()
    return {
        "output": output,
        "tick": router.runner.runner.world.tick_count,
        "tokens_used": router.runner._total_tokens_used,
    }


def route_status(handler: CORSRequestHandler):
    """GET /status — 获取状态。"""
    if router.runner is None:
        return {"initialized": False, "tick": 0}

    runner = router.runner
    snaps = runner.current_snapshots
    entities = []
    for idx, t in enumerate(runner.runner.trackers):
        snap = snaps[idx] if idx < len(snaps) else {}
        entities.append({
            "id": t.entity_id,
            "gua": snap.get("center_gua_name", "?"),
            "protocol": snap.get("body_protocol", "?"),
            "phase": round(snap.get("center_phase", 0), 2),
            "pot": round(snap.get("center_pot", 0), 2),
        })

    return {
        "initialized": True,
        "tick": runner.runner.world.tick_count,
        "camera": runner.camera.to_dict(),
        "entities": entities,
        "narrative_count": len(runner.narrative_history),
        "tokens_used": runner._total_tokens_used,
    }


def route_focus(handler: CORSRequestHandler):
    """POST /focus — 设置聚焦。"""
    if router.runner is None:
        return {"error": "世界未初始化"}
    body = handler._read_json()
    target = body.get("target", "family")
    router.runner.camera.focus = target
    return {"focus": target}


def route_variant(handler: CORSRequestHandler):
    """POST /variant — 设置变体锁定。"""
    if router.runner is None:
        return {"error": "世界未初始化"}
    body = handler._read_json()
    tag = body.get("tag")
    if tag and tag.lower() in ("off", "none", "null"):
        router.runner.camera.variant_lock = None
        return {"variant_lock": None}
    router.runner.camera.variant_lock = tag
    return {"variant_lock": tag}


def route_reset(handler: CORSRequestHandler):
    """POST /reset — 重置世界。"""
    if router.runner is None:
        return {"error": "世界未初始化"}
    router.runner.reset()
    return {"reset": True, "tick": 0}


def route_save(handler: CORSRequestHandler):
    """POST /save — 保存会话。"""
    if router.runner is None:
        return {"error": "世界未初始化"}
    body = handler._read_json()
    name = body.get("name", "session")
    state_dir = body.get("state_dir", "./states")
    path = router.runner.save_session(name, state_dir)
    return {"saved": True, "path": path}


def route_load(handler: CORSRequestHandler):
    """POST /load — 加载会话。"""
    if router.runner is None:
        return {"error": "世界未初始化"}
    body = handler._read_json()
    name = body.get("name")
    state_dir = body.get("state_dir", "./states")
    if not name:
        return {"error": "缺少 name 参数"}
    ok = router.runner.load_session(name, state_dir)
    return {"loaded": ok, "tick": router.runner.runner.world.tick_count if ok else 0}


def route_shutdown(handler: CORSRequestHandler):
    """POST /shutdown — 关闭服务器。"""
    def shutdown():
        httpd.shutdown()
    import threading
    threading.Thread(target=shutdown, daemon=True).start()
    return {"shutdown": True}


# ── 注册路由 ──

router.register("POST", "/init", route_init)
router.register("POST", "/step", route_step)
router.register("POST", "/explain", route_explain)
router.register("POST", "/reroll", route_reroll)
router.register("GET", "/status", route_status)
router.register("POST", "/focus", route_focus)
router.register("POST", "/variant", route_variant)
router.register("POST", "/reset", route_reset)
router.register("POST", "/save", route_save)
router.register("POST", "/load", route_load)
router.register("POST", "/shutdown", route_shutdown)


# ── 请求分发 ──

class YidaoHTTPHandler(CORSRequestHandler):
    def do_GET(self):
        router.handle(self)

    def do_POST(self):
        router.handle(self)


# ── 主入口 ──

httpd = None


def main():
    parser = argparse.ArgumentParser(description="易道引擎 HTTP API 服务器")
    parser.add_argument("--port", type=int, default=8765, help="监听端口 (默认 8765)")
    parser.add_argument("--mode", default="family", choices=["single", "dual", "family"])
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--worldview", default=None)
    parser.add_argument("--style", default="polished", choices=["raw", "polished"])
    parser.add_argument("--output-dir", default="./outputs")
    args = parser.parse_args()

    global httpd
    server_address = ("127.0.0.1", args.port)
    httpd = HTTPServer(server_address, YidaoHTTPHandler)

    # 自动初始化
    print(f"[API] 启动中 http://127.0.0.1:{args.port}")
    cfg = PipelineConfig.default_family() if args.mode == "family" else \
          PipelineConfig.default_dual() if args.mode == "dual" else \
          PipelineConfig.default_single()
    cfg.style = args.style
    cfg.output_dir = args.output_dir
    try:
        cfg.llm = LLMConfig.from_provider(args.provider)
    except Exception as e:
        print(f"[警告] LLM 配置加载失败: {e}")
    if args.worldview:
        from pipeline.config import WorldViewConfig
        try:
            cfg.worldview = WorldViewConfig.from_file(args.worldview)
        except Exception as e:
            print(f"[警告] 世界观加载失败: {e}")

    router.runner = InteractiveRunner(cfg, output_dir=args.output_dir)
    print(f"[API] 世界已初始化 | mode={args.mode} | provider={args.provider} | tick=0")
    print(f"[API] 按 Ctrl+C 停止")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[API] 停止")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
