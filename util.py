def try_int(x, default=0):
    try:
        return int(x)
    except (ValueError, TypeError):
        return default
