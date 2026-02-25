#!/usr/bin/env python3
"""
将 Claude Code 的 JSONL 对话记录解析为可读的 JSON + Markdown
用法: python3 export_chats.py
输出: ~/amazon-workspace/chats/
"""
import json, os, glob, re
from datetime import datetime

JSONL_DIR = os.path.expanduser("~/.claude/projects/-Users-zhaoxueqin")
OUTPUT_DIR = os.path.expanduser("~/amazon-workspace/chats")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_session(filepath):
    """解析单个 JSONL 文件，提取对话内容"""
    messages = []
    session_id = os.path.basename(filepath).replace(".jsonl","")
    first_ts = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except:
                continue

            msg_type = d.get("type", "")

            if msg_type == "user":
                text = d.get("message", "")
                if isinstance(text, dict):
                    text = text.get("content", "")
                if isinstance(text, list):
                    parts = []
                    for item in text:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                parts.append(item.get("text",""))
                            elif item.get("type") == "image":
                                parts.append("[图片]")
                        elif isinstance(item, str):
                            parts.append(item)
                    text = "\n".join(parts)
                if not text or len(str(text).strip()) == 0:
                    continue
                ts = d.get("timestamp")
                if ts and not first_ts:
                    first_ts = ts
                messages.append({
                    "role": "user",
                    "content": str(text).strip(),
                    "timestamp": ts
                })

            elif msg_type == "assistant":
                msg = d.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                t = item.get("text", "")
                                if t.strip():
                                    parts.append(t.strip())
                            elif item.get("type") == "tool_use":
                                name = item.get("name","")
                                parts.append(f"[工具调用: {name}]")
                    text = "\n".join(parts)
                else:
                    text = str(content)
                if not text.strip():
                    continue
                messages.append({
                    "role": "ai",
                    "content": text.strip()
                })

    # 确定日期
    date_str = "未知日期"
    if first_ts:
        try:
            ts_num = int(first_ts) if isinstance(first_ts, str) else first_ts
            if ts_num > 1e12:
                ts_num = ts_num / 1000
            dt = datetime.fromtimestamp(ts_num)
            date_str = dt.strftime("%Y-%m-%d")
        except:
            pass

    # 提取标题：用第一条用户消息的前50字
    title = "无标题对话"
    for m in messages:
        if m["role"] == "user":
            title = m["content"][:50].replace("\n"," ")
            break

    return {
        "session_id": session_id,
        "date": date_str,
        "title": title,
        "message_count": len(messages),
        "messages": messages
    }


def to_markdown(session):
    """将一个对话转为 Markdown"""
    lines = [f"# {session['title']}", f"日期: {session['date']}\n"]
    for m in session["messages"]:
        role = "👤 我" if m["role"] == "user" else "🤖 旺财"
        lines.append(f"### {role}\n")
        lines.append(m["content"])
        lines.append("")
    return "\n".join(lines)


def main():
    files = glob.glob(os.path.join(JSONL_DIR, "*.jsonl"))
    if not files:
        print("没有找到对话文件")
        return

    all_sessions = []
    for f in sorted(files, key=os.path.getmtime):
        session = parse_session(f)
        if session["message_count"] < 2:
            continue
        all_sessions.append(session)

        # 导出单个 Markdown
        md_path = os.path.join(
            OUTPUT_DIR,
            f"{session['date']}_{session['session_id'][:8]}.md"
        )
        with open(md_path, "w", encoding="utf-8") as mf:
            mf.write(to_markdown(session))

    # 生成 chat-data.js 供网页加载
    js_data = []
    for s in all_sessions:
        clean_msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in s["messages"]
        ]
        js_data.append({
            "date": s["date"],
            "title": s["title"],
            "session_id": s["session_id"],
            "message_count": s["message_count"],
            "messages": clean_msgs
        })

    js_path = os.path.join(OUTPUT_DIR, "chat-data.js")
    with open(js_path, "w", encoding="utf-8") as jf:
        jf.write("var CHAT_DATA = ")
        json.dump(js_data, jf, ensure_ascii=False, indent=2)
        jf.write(";")

    print(f"导出完成: {len(all_sessions)} 个对话")
    print(f"JS 数据: {js_path}")
    print(f"Markdown: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()


