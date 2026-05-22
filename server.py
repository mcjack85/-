from __future__ import annotations

import html
import json
import os
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
LANDING_PAGE = ROOT / "incardirect_winners_landing_page.html"
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "submissions.json"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5177"))
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")


def load_submissions() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_submission(payload: dict, client_ip: str) -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    submissions = load_submissions()
    submission = {
        "id": len(submissions) + 1,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": str(payload.get("name", "")).strip(),
        "phone": str(payload.get("phone", "")).strip(),
        "region": str(payload.get("region", "")).strip(),
        "career": str(payload.get("career", "")).strip(),
        "time": str(payload.get("time", "")).strip(),
        "client_ip": client_ip,
    }
    submissions.append(submission)
    DATA_FILE.write_text(
        json.dumps(submissions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return submission


def admin_page() -> str:
    submissions = list(reversed(load_submissions()))
    rows = "\n".join(
        f"""
        <tr>
          <td>{item["id"]}</td>
          <td>{html.escape(item["created_at"])}</td>
          <td>{html.escape(item["name"])}</td>
          <td><a href="tel:{html.escape(item["phone"])}">{html.escape(item["phone"])}</a></td>
          <td>{html.escape(item["region"])}</td>
          <td>{html.escape(item["career"])}</td>
          <td>{html.escape(item["time"] or "-")}</td>
        </tr>
        """
        for item in submissions
    )
    if not rows:
        rows = '<tr><td colspan="7" class="empty">아직 접수된 상담 신청이 없습니다.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>상담 신청 관리자 | 인카다이렉트 위너스</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f4ed;
      color: #132033;
    }}
    header {{
      padding: 28px clamp(18px, 4vw, 48px);
      background: #132033;
      color: white;
    }}
    header h1 {{ margin: 0; font-size: clamp(26px, 4vw, 40px); }}
    header p {{ margin: 8px 0 0; color: rgba(255,255,255,.72); }}
    main {{ padding: 28px clamp(18px, 4vw, 48px) 48px; }}
    .toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}
    .count {{ font-weight: 800; color: #0f766e; }}
    a.button {{
      display: inline-flex;
      min-height: 42px;
      padding: 0 14px;
      align-items: center;
      border-radius: 8px;
      background: #0f766e;
      color: white;
      text-decoration: none;
      font-weight: 800;
    }}
    .table-wrap {{
      overflow-x: auto;
      background: white;
      border: 1px solid rgba(19,32,51,.12);
      border-radius: 10px;
      box-shadow: 0 18px 50px rgba(19,32,51,.08);
    }}
    table {{ width: 100%; min-width: 880px; border-collapse: collapse; }}
    th, td {{
      padding: 14px 16px;
      border-bottom: 1px solid rgba(19,32,51,.08);
      text-align: left;
      font-size: 14px;
      white-space: nowrap;
    }}
    th {{
      background: #fbfaf7;
      color: #5d6878;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    td a {{ color: #0f766e; font-weight: 800; }}
    tr:last-child td {{ border-bottom: 0; }}
    .empty {{ padding: 42px 16px; text-align: center; color: #5d6878; }}
  </style>
</head>
<body>
  <header>
    <h1>상담 신청 관리자</h1>
    <p>인카다이렉트 위너스 랜딩페이지에서 접수된 상담 신청을 확인합니다.</p>
  </header>
  <main>
    <div class="toolbar">
      <div>전체 신청 <span class="count">{len(submissions)}</span>건</div>
      <a class="button" href="/">랜딩페이지 보기</a>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>번호</th>
            <th>접수일시</th>
            <th>이름</th>
            <th>연락처</th>
            <th>지역</th>
            <th>경력</th>
            <th>희망 시간</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </main>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path in {"/", "/index.html"}:
            self.send_file(LANDING_PAGE, "text/html; charset=utf-8")
        elif path == "/admin":
            if not self.is_admin_request(parsed.query):
                self.send_error(HTTPStatus.FORBIDDEN, "Admin key required")
                return
            self.send_text(admin_page(), "text/html; charset=utf-8")
        elif path == "/api/applications":
            if not self.is_admin_request(parsed.query):
                self.send_error(HTTPStatus.FORBIDDEN, "Admin key required")
                return
            self.send_json(load_submissions())
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/applications":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        required = ["name", "phone", "region", "career"]
        if any(not str(payload.get(field, "")).strip() for field in required):
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing required fields")
            return

        submission = save_submission(payload, self.client_address[0])
        self.send_json({"ok": True, "submission": submission}, HTTPStatus.CREATED)

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, body: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def is_admin_request(self, query: str) -> bool:
        if not ADMIN_KEY:
            return True
        keys = parse_qs(query).get("key", [])
        return bool(keys and keys[0] == ADMIN_KEY)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Server running at http://{HOST}:{PORT}")
    print(f"Admin page: http://{HOST}:{PORT}/admin")
    server.serve_forever()
