"""
collector.py - gathers files when you right-click SEVERAL files at once.

THE PROBLEM
    When you select 5 files and click "Merge into one PDF", Windows doesn't start
    our program once with 5 files. It starts it 5 times, once per file, at almost
    the same moment. Merge needs all 5 files in ONE place.

THE FIX (a tiny "leader election")
    Every copy tries to claim the same local network port (a numbered "door" on
    this computer only, 127.0.0.1, never the internet).
    - The first copy to grab it becomes the LEADER. It waits and listens.
    - Every later copy fails to grab the port (it's taken), so it becomes a
      HELPER: it connects to the leader, sends its file path, and quits.
    - When no new paths arrive for a short while, the leader stops listening and
      processes the whole list.
"""

import socket                      # local network connections between our own copies
import time                        # small pauses between retries

HOST = "127.0.0.1"                 # "this computer only" - nothing leaves your laptop

# One port per feature so a merge and a compress running together don't mix up files.
PORTS = {
    "merge": 51731,
    "office": 51732,
    "compress": 51733,
}

QUIET_SECONDS = 1.5                # leader stops after this long with no new files


def _try_become_leader(port):
    """Try to claim the port. Returns a listening socket, or None if someone has it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):          # Windows: forbid any other program sharing the port
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        sock.bind((HOST, port))                          # fails if another copy already claimed it
        sock.listen()                                    # start accepting helpers
        return sock
    except OSError:
        sock.close()
        return None


def _send_to_leader(port, paths):
    """Hand our file paths to the leader. Returns True if it worked."""
    try:
        with socket.create_connection((HOST, port), timeout=2) as conn:
            message = "\n".join(str(p) for p in paths)   # one path per line
            conn.sendall(message.encode("utf-8"))        # utf-8 keeps non-English file names intact
        return True
    except OSError:
        return False


def _listen_for_helpers(sock, paths):
    """Leader loop: keep accepting paths until it's quiet for QUIET_SECONDS."""
    sock.settimeout(QUIET_SECONDS)                       # accept() gives up after this long
    while True:
        try:
            conn, _ = sock.accept()                      # wait for a helper; the timer restarts each time
        except socket.timeout:
            break                                        # nobody new for a while: we're done
        with conn:
            conn.settimeout(2)
            chunks = []
            while True:                                  # read until the helper closes the connection
                data = conn.recv(65536)
                if not data:
                    break
                chunks.append(data)
        text = b"".join(chunks).decode("utf-8")
        paths.extend(line for line in text.splitlines() if line.strip())
    sock.close()


def gather(channel, my_paths):
    """Return the full list of files to process, or None if another copy will handle ours.

    channel  : which feature ("merge", "office", "compress") - picks the port
    my_paths : the file path(s) this copy of the program was started with
    """
    port = PORTS[channel]
    for _ in range(50):                                  # retry for ~5 seconds in case of a race
        sock = _try_become_leader(port)
        if sock:
            paths = list(my_paths)
            _listen_for_helpers(sock, paths)
            return list(dict.fromkeys(paths))            # remove duplicates, keep order
        if _send_to_leader(port, my_paths):
            return None                                  # leader has our files; this copy can quit
        time.sleep(0.1)                                  # leader was just closing; try again
    return list(my_paths)                                # last resort: process ours alone
