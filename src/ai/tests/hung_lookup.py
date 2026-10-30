"""Make one transport call whose name lookup hangs, then exit (a subprocess helper).

Run as `python -m ai.tests.hung_lookup` with `src` on the path. It prints the
outcome; the parent test times how long the interpreter takes to exit.
"""

import os
import socket
import time

import django

HANG = 20


def _hang(*args, **kwargs):
    time.sleep(HANG)
    raise OSError("synthetic lookup that never answers in time")


def main():
    """Run the call with every name lookup hanging, and print its outcome."""
    os.environ["DJANGO_SETTINGS_MODULE"] = "relay.settings.test"
    django.setup()
    from ai import gateway  # noqa: PLC0415 - models need django.setup() first

    socket.getaddrinfo = _hang
    deadline = time.monotonic() + 0.5
    try:
        gateway._run(gateway._exchange("https://localhost:9/llm", {}, b"{}", deadline))
    except TimeoutError:
        print("timeout", flush=True)
    else:
        print("no timeout", flush=True)


if __name__ == "__main__":
    main()
