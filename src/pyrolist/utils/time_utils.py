def format_duration(ms: int) -> str:
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_duration_short(ms: int) -> str:
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02d}"


def format_time_ago(dt) -> str:
    from datetime import datetime, timedelta
    if not dt:
        return "Unknown"
    now = datetime.utcnow()
    diff = now - dt
    if diff < timedelta(minutes=1):
        return "Just now"
    elif diff < timedelta(hours=1):
        return f"{int(diff.total_seconds() / 60)}m ago"
    elif diff < timedelta(days=1):
        return f"{int(diff.total_seconds() / 3600)}h ago"
    elif diff < timedelta(days=30):
        return f"{int(diff.days)}d ago"
    else:
        return f"{int(diff.days / 30)}mo ago"