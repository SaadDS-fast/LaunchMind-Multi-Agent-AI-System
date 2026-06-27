def log(component: str, message: str) -> None:
    """Print a consistent, human-readable workflow log message."""
    print(f"[{component}] {message}")


def log_success(component: str, message: str) -> None:
    """Print a consistent success log message."""
    log(component, f"OK {message}")


def log_skip(component: str, message: str) -> None:
    """Print a consistent optional-integration skip message."""
    log(component, f"Skipped: {message}")
