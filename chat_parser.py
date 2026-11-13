"""
Parser for Facebook Messenger JSON exports and simplified chat logs.
Handles:
- Standard Facebook Messenger format (messages array, timestamp_ms, sender_name, content, reactions, photos)
- Simplified / custom JSON formats (sender/author/from, text/message/body, timestamp/date/time)
- UTF-8 decoding / Facebook Latin-1 Mojibake repair (e.g. \u00c3\u00a1 -> á, 4-byte emojis)
- Chronological sorting & date range filtering
- Grouping by Month ('YYYY-MM'), Year ('YYYY'), or Single combined document ('ALL')
"""

import json
import os
from datetime import datetime, date
from typing import List, Dict, Any, Tuple, Optional


def fix_encoding(text: str) -> str:
    """
    Fix Facebook JSON Latin-1 mojibake encoding issues (e.g. \u00c3\u00a1 -> á).
    Only applies decode when text actually contains mojibake byte patterns,
    preserving already properly decoded UTF-8 strings.
    """
    if not isinstance(text, str):
        return text
    # Facebook UTF-8 mojibake commonly produces these Latin-1 characters:
    # \u00c3, \u00c2, \u00c4, \u00c5 (for accented letters) or \u00f0\u009f (for 4-byte emojis)
    if any(m in text for m in ("\u00c3", "\u00c2", "\u00c4", "\u00c5", "\u00f0\u009f", "\u00e2")):
        try:
            return text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text
    return text


def parse_timestamp(value: Any) -> datetime:
    """Parse various timestamp formats (ms epoch, s epoch, ISO strings) into a datetime object."""
    if value is None:
        return datetime.fromtimestamp(0)

    if isinstance(value, (int, float)):
        # If timestamp is in milliseconds (Facebook standard is 13 digits, > 1e11)
        if value > 1e11:
            return datetime.fromtimestamp(value / 1000.0)
        return datetime.fromtimestamp(value)

    if isinstance(value, str):
        value_str = value.strip()
        if value_str.isdigit():
            val = int(value_str)
            if val > 1e11:
                return datetime.fromtimestamp(val / 1000.0)
            return datetime.fromtimestamp(val)

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%d.%m.%Y %H:%M:%S",
            "%d.%m.%Y %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt)
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(value_str)
        except Exception:
            pass

    return datetime.fromtimestamp(0)


def normalize_message(raw_msg: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single message dictionary into a standardized schema."""
    content = (
        raw_msg.get("content")
        or raw_msg.get("text")
        or raw_msg.get("message")
        or raw_msg.get("body")
        or raw_msg.get("zprava")
        or ""
    )
    content = fix_encoding(str(content))

    sender = (
        raw_msg.get("sender_name")
        or raw_msg.get("senderName")
        or raw_msg.get("sender")
        or raw_msg.get("author")
        or raw_msg.get("from")
        or raw_msg.get("name")
        or raw_msg.get("odesilatel")
        or raw_msg.get("autor")
        or "Unknown"
    )
    sender = fix_encoding(str(sender))

    ts_val = (
        raw_msg.get("timestamp_ms")
        or raw_msg.get("timestamp")
        or raw_msg.get("date")
        or raw_msg.get("created_at")
        or raw_msg.get("time")
        or raw_msg.get("cas")
    )
    dt = parse_timestamp(ts_val)

    # Reactions extraction
    reactions = []
    raw_reactions = raw_msg.get("reactions") or raw_msg.get("reakce") or []
    if isinstance(raw_reactions, list):
        for r in raw_reactions:
            if isinstance(r, dict):
                r_emoji = r.get("reaction") or r.get("emoji") or ""
                r_actor = (
                    r.get("actor")
                    or r.get("sender_name")
                    or r.get("senderName")
                    or r.get("sender")
                    or r.get("odesilatel")
                    or ""
                )
                if r_emoji:
                    reactions.append({
                        "emoji": fix_encoding(str(r_emoji)),
                        "actor": fix_encoding(str(r_actor)),
                    })
            elif isinstance(r, str) and r:
                reactions.append({
                    "emoji": fix_encoding(r),
                    "actor": "",
                })
    elif isinstance(raw_reactions, str) and raw_reactions:
        reactions.append({"emoji": fix_encoding(raw_reactions), "actor": ""})

    # Photos / Media / Attachments
    photos = []
    raw_photos = (
        raw_msg.get("photos")
        or raw_msg.get("media")
        or raw_msg.get("attachments")
        or raw_msg.get("fotky")
        or []
    )
    if isinstance(raw_photos, list):
        for p in raw_photos:
            if isinstance(p, dict):
                uri = p.get("uri") or p.get("url") or p.get("path") or p.get("src") or ""
                if uri:
                    photos.append(uri)
            elif isinstance(p, str) and p:
                photos.append(p)

    return {
        "text": content,
        "sender": sender,
        "datetime": dt,
        "reactions": reactions,
        "photos": photos,
        "raw": raw_msg,
    }


def load_messages_from_data(data: Any) -> List[Dict[str, Any]]:
    """Extract a list of normalized messages from a parsed JSON object."""
    messages_raw = []
    if isinstance(data, list):
        messages_raw = data
    elif isinstance(data, dict):
        if "messages" in data and isinstance(data["messages"], list):
            messages_raw = data["messages"]
        elif "data" in data and isinstance(data["data"], list):
            messages_raw = data["data"]
        elif "zpravy" in data and isinstance(data["zpravy"], list):
            messages_raw = data["zpravy"]
        else:
            messages_raw = [data]

    normalized = []
    for m in messages_raw:
        if isinstance(m, dict):
            norm = normalize_message(m)
            if norm["text"] or norm["photos"] or norm["reactions"]:
                normalized.append(norm)
    return normalized


def load_chat_files(paths: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Load chat messages from one or more JSON file paths.
    Returns: (sorted_messages, metadata)
    """
    all_messages = []
    participants = set()

    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "participants" in data:
                for p in data["participants"]:
                    p_name = p.get("name") if isinstance(p, dict) else str(p)
                    if p_name:
                        participants.add(fix_encoding(p_name))
            msgs = load_messages_from_data(data)
            all_messages.extend(msgs)
        except Exception as e:
            print(f"Error reading file {path}: {e}")

    # Chronological sort (oldest first)
    all_messages.sort(key=lambda m: m["datetime"])

    for m in all_messages:
        participants.add(m["sender"])

    metadata = {
        "participants": sorted(list(participants)),
        "total_messages": len(all_messages),
    }

    return all_messages, metadata


def filter_messages_by_date_range(
    messages: List[Dict[str, Any]],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Filter normalized messages inclusively between start_date and end_date."""
    if not start_date and not end_date:
        return messages

    filtered = []
    for msg in messages:
        msg_date = msg["datetime"].date()
        if start_date and msg_date < start_date:
            continue
        if end_date and msg_date > end_date:
            continue
        filtered.append(msg)
    return filtered


def group_messages_by_month(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group messages by 'YYYY-MM' key, preserving chronological order."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for msg in messages:
        dt: datetime = msg["datetime"]
        key = dt.strftime("%Y-%m")
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(msg)
    return grouped


def group_messages_by_year(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group messages by 'YYYY' key, preserving chronological order."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for msg in messages:
        dt: datetime = msg["datetime"]
        key = dt.strftime("%Y")
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(msg)
    return grouped


def group_messages(
    messages: List[Dict[str, Any]], mode: str = "month"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group messages according to selected mode:
    - 'month': grouped by 'YYYY-MM'
    - 'year': grouped by 'YYYY'
    - 'single': all messages in one group ('Complete_Chat')
    """
    mode = (mode or "month").lower()
    if mode == "year":
        return group_messages_by_year(messages)
    elif mode == "single":
        return {"Complete": list(messages)} if messages else {}
    return group_messages_by_month(messages)
