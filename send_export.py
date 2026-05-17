import sys
import requests
from pathlib import Path

def send(html_path: str, artifact_name: str, delivery_type: str, host: str = "http://localhost:5088"):
    html = Path(html_path).read_text(encoding="utf-8")
    resp = requests.post(
        f"{host}/export/zip",
        json={"html": html, "artifact_name": artifact_name, "delivery_type": delivery_type},
    )
    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}")
        sys.exit(1)
    out = Path(artifact_name).stem + "_export.zip"
    Path(out).write_bytes(resp.content)
    print(f"OK -> {out}")

if __name__ == "__main__":
    # Uso: python send_export.py <html_file> <artifact_name> <delivery_type>
    if len(sys.argv) != 4:
        print("Uso: python send_export.py <html_file> <artifact_name> <delivery_type>")
        sys.exit(1)
    send(sys.argv[1], sys.argv[2], sys.argv[3])
