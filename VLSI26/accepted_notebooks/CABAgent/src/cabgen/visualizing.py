import matplotlib.pyplot as plt


def format_dict(d, indent=0):
    """
    Recursively pretty-print a nested dict with aligned keys.
    """
    # Get max key length at this level
    max_key_len = max(len(str(k)) for k in d.keys())
    result = []
    pad = " " * indent

    for k, v in d.items():
        key_str = f" {str(k):<{max_key_len}}"  # left-align keys
        if isinstance(v, dict):
            result.append(f"{pad}{key_str} :")
            result.append(format_dict(v, indent + 2))
        else:
            result.append(f"{pad}{key_str} : {v}")
    return "\n".join(result)