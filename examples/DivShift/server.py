import argparse
import os
import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.web import create_app  # noqa: E402
from examples.DivShift.routes import register_divshift_routes  # noqa: E402


PORT = int(os.environ.get("PORT", "8420"))
DEFAULT_RUNTIME = os.environ.get("VIBECLEANING_RUNTIME", "local")

app = create_app(
    data_root=ROOT / "data",
    static_root=ROOT / "examples" / "DivShift" / "static",
)
register_divshift_routes(app, data_root=ROOT / "data")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime",
        choices=("local", "cluster"),
        default=DEFAULT_RUNTIME,
        help="Use cluster mode to bind 0.0.0.0 instead of 127.0.0.1.",
    )
    parser.add_argument("--host", default=None, help="Override the bind host.")
    parser.add_argument("--port", type=int, default=PORT, help="Override the bind port.")
    parser.add_argument(
        "--find-free-port",
        action="store_true",
        help="Choose an available port automatically.",
    )
    args = parser.parse_args()

    host = args.host or os.environ.get(
        "HOST",
        "0.0.0.0" if args.runtime == "cluster" else "127.0.0.1",
    )
    port = find_free_port() if args.find_free_port else args.port

    print(f"\n  DivShift Bias Dashboard ({args.runtime}): http://{host}:{port}\n")
    if args.runtime == "cluster":
        ssh_user = os.environ.get("USER", "YOUR_USERNAME")
        ssh_host = socket.gethostname()
        print("  Tunnel from your local machine:")
        print(f"    ssh -N -L {port}:localhost:{port} {ssh_user}@{ssh_host}")
        print(f"  Then open: http://localhost:{port}\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
