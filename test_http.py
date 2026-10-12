"""Starts the hosted server and exercises auth, MCP over HTTP, and the teacher approval page."""
import asyncio, base64, json, os, re, subprocess, sys, tempfile, time, urllib.request, urllib.error
PORT = 8765; AG = "agent-token-0123456789"; TP = "teacher-pass-123456"
env = {**os.environ, "LP_DB": tempfile.mktemp(suffix=".db"), "LP_AGENT_TOKEN": AG, "LP_TEACHER_PASSWORD": TP, "PORT": str(PORT)}
srv = subprocess.Popen([sys.executable, "http_server.py"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
B = f"http://127.0.0.1:{PORT}"
def req(path, hdr=None, data=None):
    r = urllib.request.Request(B + path, data=data, headers=hdr or {})
    try:
        with urllib.request.urlopen(r) as x: return x.status, x.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()
basic = lambda u, p: {"Authorization": "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()}
try:
    for _ in range(40):
        try: req("/health"); break
        except Exception: time.sleep(0.25)
    print("health:", req("/health")[0])
    print("mcp without token:", req("/mcp", {"Accept": "application/json, text/event-stream"})[0])
    print("teacher page without login:", req("/teacher")[0], "| with AGENT token as password:", req("/teacher", basic("x", AG))[0])
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async def agent():
        async with streamablehttp_client(B + "/mcp", headers={"Authorization": f"Bearer {AG}"}) as (r, w, _), ClientSession(r, w) as s:
            await s.initialize(); J = lambda x: json.loads(x.content[0].text)
            print("tools over HTTP:", [t.name for t in (await s.list_tools()).tools])
            for t, sc in [("2025-T1", 70), ("2025-T2", 78), ("2025-T3", 84)]:
                await s.call_tool("add_evidence", dict(learner_id="L-H", term=t, subject="Science", kind="quiz", teacher="Ms W", score=sc))
            pr = J(await s.call_tool("propose_update", dict(learner_id="L-H", wording="Science results rise across three terms [E1] [E2] [E3]. What does the learner enjoy most?", model_name="http-test")))
            print("proposal accepted:", pr["accepted"], "id", pr.get("proposal_id"))
            return pr["proposal_id"], J
    pid, _ = asyncio.run(agent())
    st, page = req("/teacher", basic("Ms Wanjiru", TP)); print("teacher page:", st, "| shows proposal:", f"Proposal #{pid}" in page)
    tok = re.search(r'name=t value=(\w+)', page).group(1)
    print("forged csrf:", req("/teacher/decide", basic("Ms Wanjiru", TP), f"id={pid}&t=bad&action=approve".encode())[0])
    print("approve:", req("/teacher/decide", basic("Ms Wanjiru", TP), f"id={pid}&t={tok}&action=approve".encode())[0])
    async def after():
        async with streamablehttp_client(B + "/mcp", headers={"Authorization": f"Bearer {AG}"}) as (r, w, _), ClientSession(r, w) as s:
            await s.initialize(); p = json.loads((await s.call_tool("get_profile", dict(learner_id="L-H"))).content[0].text)
            print("profile after approval:", p["subjects"]["Science"]["level"], "| approved by", p["approved_summary"]["approved_by"])
    asyncio.run(after())
finally: srv.terminate()
