#!/usr/bin/env python3
"""
将 Claude Code 的 JSONL 对话记录解析为 Obsidian Markdown
同时同步知识库到 Obsidian
用法: python3 export_chats.py
"""
import json, os, glob, re
from datetime import datetime

JSONL_DIR = os.path.expanduser("~/.claude/projects/-Users-zhaoxueqin")
OBSIDIAN_VAULT = os.path.expanduser("~/Documents/Obsidian Vault")
CHAT_DIR = os.path.join(OBSIDIAN_VAULT, "聊天记录")
KNOWLEDGE_DIR = os.path.join(OBSIDIAN_VAULT, "知识库")
os.makedirs(CHAT_DIR, exist_ok=True)
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

def sanitize(text):
    """脱敏处理：移除 token 等敏感信息"""
    return re.sub(r'ghp_[A-Za-z0-9]{36,40}', '[TOKEN已脱敏]', text)

def parse_session(filepath):
    """解析单个 JSONL 文件"""
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

            # 从 snapshot 或任何字段提取时间
            if not first_ts:
                snap = d.get("snapshot", {})
                ts_str = snap.get("timestamp", "")
                if not ts_str:
                    ts_str = d.get("timestamp", "")
                if ts_str and isinstance(ts_str, str) and "T" in ts_str:
                    first_ts = ts_str

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
                    "content": sanitize(str(text).strip()),
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
                    text = "\n".join(parts)
                else:
                    text = str(content)
                if not text.strip():
                    continue
                messages.append({
                    "role": "ai",
                    "content": sanitize(text.strip())
                })

    date_str = "未知日期"
    if first_ts and isinstance(first_ts, str) and "T" in first_ts:
        try:
            dt = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
        except:
            pass
    if date_str == "未知日期":
        try:
            mtime = os.path.getmtime(filepath)
            dt = datetime.fromtimestamp(mtime)
            date_str = dt.strftime("%Y-%m-%d")
        except:
            pass

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


def to_obsidian_md(session):
    """转为 Obsidian 友好的 Markdown"""
    lines = [
        "---",
        f"date: {session['date']}",
        f"tags: [聊天记录]",
        f"messages: {session['message_count']}",
        "---",
        f"# {session['title']}",
        ""
    ]
    for m in session["messages"]:
        if m["role"] == "user":
            lines.append("> **我**")
            for l in m["content"].split("\n"):
                lines.append(f"> {l}")
            lines.append("")
        else:
            lines.append("**旺财**")
            lines.append("")
            lines.append(m["content"])
            lines.append("")
            lines.append("---")
            lines.append("")
    return "\n".join(lines)


def export_knowledge():
    """将知识库 JSON 导出为 Obsidian 单条笔记"""
    kb_path = os.path.join(
        os.path.expanduser("~/amazon-workspace"),
        "knowledge", "knowledge.json"
    )
    if not os.path.exists(kb_path):
        return 0
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for k in data:
        fname = f"{k['id']} {k['title']}.md"
        fname = re.sub(r'[/\\:*?"<>|]', '', fname)
        md = "\n".join([
            "---",
            f"date: {k['date']}",
            f"category: {k['category']}",
            f"tags: [知识库, {k['category']}]",
            f"source: {k['source']}",
            "---",
            f"# {k['title']}",
            "",
            k['content']
        ])
        with open(os.path.join(KNOWLEDGE_DIR, fname), "w") as f:
            f.write(md)
        count += 1
    return count


def main():
    files = glob.glob(os.path.join(JSONL_DIR, "*.jsonl"))
    if not files:
        print("没有找到对话文件")
        return

    chat_count = 0
    for f in sorted(files, key=os.path.getmtime):
        session = parse_session(f)
        if session["message_count"] < 2:
            continue
        safe_title = re.sub(r'[/\\:*?"<>|]', '', session['title'])[:30]
        md_name = f"{session['date']} {safe_title}.md"
        md_path = os.path.join(CHAT_DIR, md_name)
        with open(md_path, "w", encoding="utf-8") as mf:
            mf.write(to_obsidian_md(session))
        chat_count += 1

    kb_count = export_knowledge()
    print(f"导出完成: {chat_count} 个对话 → {CHAT_DIR}")
    print(f"知识库: {kb_count} 条 → {KNOWLEDGE_DIR}")


if __name__ == "__main__":
    main()
