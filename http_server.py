"""Hosted mode: the same MCP server over streamable HTTP, plus a teacher approval web page.

Two SEPARATE credentials keep the human gate intact over a network:
  LP_AGENT_TOKEN       bearer token for /mcp   (agents: add_evidence, get_profile, propose_update)
  LP_TEACHER_PASSWORD  HTTP Basic password for /teacher (username = teacher's name, recorded in the audit trail)
An agent holding only the agent token cannot approve anything.
Run:  LP_AGENT_TOKEN=... LP_TEACHER_PASSWORD=... python http_server.py   (uses $PORT, default 8000)"""
import base64, hashlib, hmac, html, json, os, sys
import uvicorn
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from mcp.server.transport_security import TransportSecuritySettings
import core
from server import mcp

AGENT = os.environ.get("LP_AGENT_TOKEN", "")
TEACH = os.environ.get("LP_TEACHER_PASSWORD", "")
if len(AGENT) < 16 or len(TEACH) < 12 or AGENT == TEACH:
    sys.exit("Set LP_AGENT_TOKEN (>=16 chars) and a different LP_TEACHER_PASSWORD (>=12 chars). Refusing to start unauthenticated.")

# Host-header (DNS-rebinding) protection is for unauthenticated localhost servers; here every route is authenticated.
mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app()

class AgentAuth:                                   # pure ASGI so streaming responses are untouched
    def __init__(self, a): self.a = a
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            got = dict(scope["headers"]).get(b"authorization", b"").decode()
            if not hmac.compare_digest(got, f"Bearer {AGENT}"):
                return await JSONResponse({"error": "unauthorized"}, 401, {"WWW-Authenticate": "Bearer"})(scope, receive, send)
        await self.a(scope, receive, send)
app.add_middleware(AgentAuth)

def who(req):                                      # returns teacher name, or None
    try:
        user, pw = base64.b64decode(req.headers.get("authorization", "")[6:]).decode().split(":", 1)
    except Exception: return None
    return user.strip() if user.strip() and hmac.compare_digest(pw, TEACH) else None
def need_login(): return PlainTextResponse("Teacher login required", 401, {"WWW-Authenticate": 'Basic realm="Teacher approval"'})
def csrf(pid, name): return hmac.new(TEACH.encode(), f"{pid}:{name}".encode(), hashlib.sha256).hexdigest()[:32]
E = html.escape

async def health(req): return JSONResponse({"ok": True})

async def teacher(req: Request):
    name = who(req)
    if not name: return need_login()
    c = core.conn(); out = []
    for p in c.execute("SELECT * FROM proposals WHERE status='pending' ORDER BY id"):
        ev = "".join(f"<li>[E{i}] {E(str(e['term']))} {E(e['subject'])} {E(e['kind'])} score={e['score']} by {E(e['teacher'])}: {E(e['note'] or '')}</li>"
                     for i in json.loads(p["evidence_ids"]) for e in [c.execute("SELECT * FROM evidence WHERE id=?", (i,)).fetchone()])
        out.append(f"""<section><h3>Proposal #{p['id']} for learner {E(p['learner'])} <small>(drafted by {E(p['model'])})</small></h3>
<p class=w>{E(p['wording'])}</p><details><summary>Profile changes</summary><pre>{E(json.dumps(json.loads(p['diff']), indent=1))}</pre></details>
<p>Evidence behind it:</p><ul>{ev}</ul>
<form method=post action=/teacher/decide><input type=hidden name=id value={p['id']}><input type=hidden name=t value={csrf(p['id'], name)}>
<input name=reason placeholder="Reason (optional)"> <button name=action value=approve>Approve as {E(name)}</button> <button name=action value=reject>Reject</button></form></section>""")
    return HTMLResponse(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Teacher approval</title><style>body{{font:16px/1.5 system-ui;max-width:760px;margin:2rem auto;padding:0 1rem}}section{{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem 0}}.w{{background:#eef7f3;padding:.6rem;border-radius:6px}}pre{{overflow:auto}}</style>
<h1>Pending proposals</h1><p>Signed in as <b>{E(name)}</b>. Nothing enters a learner's profile until you approve it.</p>{''.join(out) or '<p>Nothing waiting for approval.</p>'}""")

async def decide(req: Request):
    name = who(req)
    if not name: return need_login()
    f = await req.form(); pid = int(f["id"])
    if not hmac.compare_digest(str(f.get("t", "")), csrf(pid, name)): return PlainTextResponse("bad token", 403)
    try: core.approve(pid, name, f["action"] == "approve", str(f.get("reason", ""))[:300])
    except ValueError as e: return PlainTextResponse(str(e), 409)
    return RedirectResponse("/teacher", 303)

app.add_route("/health", health); app.add_route("/teacher", teacher); app.add_route("/teacher/decide", decide, methods=["POST"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
