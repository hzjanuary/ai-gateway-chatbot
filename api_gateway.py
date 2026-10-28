"""Compatibility entrypoint. Prefer `gateway serve`. No prototype auth or transports."""

from gateway.api import app

__all__ = ["app"]

if __name__ == "__main__":
    from gateway.cli import main

    main(["serve"])
