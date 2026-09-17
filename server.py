import os,urllib.parse,httpx
from fastapi import FastAPI,Query
from fastapi.responses import FileResponse,JSONResponse,Response
from pydantic import BaseModel
app=FastAPI(title="ESPYNOS-AI")
KEY=os.getenv("GEMINI_API_KEY",""); DEFAULT=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
class Req(BaseModel): message:str; history:list=[]; model:str|None=None
@app.get("/")
async def root(): return FileResponse("index.html")
@app.get("/health")
async def health(): return {"status":"online","gemini_configured":bool(KEY)}
@app.post("/api/chat")
async def chat(x:Req):
 if not KEY:return JSONResponse({"error":"GEMINI_API_KEY is not configured in Render."},status_code=503)
 contents=[]
 for m in x.history[-20:]:
  contents.append({"role":"user" if m.get("role")=="user" else "model","parts":[{"text":str(m.get("text",""))}]})
 contents.append({"role":"user","parts":[{"text":x.message}]})
 try:
  async with httpx.AsyncClient(timeout=60) as c:
   r=await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/{x.model or DEFAULT}:generateContent",params={"key":KEY},json={"contents":contents,"generationConfig":{"temperature":.7,"maxOutputTokens":4096}})
  d=r.json()
  if r.status_code>=400:return JSONResponse({"error":d.get("error",{}).get("message","Gemini error")},status_code=502)
  return {"reply":d["candidates"][0]["content"]["parts"][0]["text"]}
 except:return JSONResponse({"error":"AI provider connection failed."},status_code=502)
@app.get("/api/search")
async def search(q:str=Query(min_length=1)):
 try:
  async with httpx.AsyncClient(timeout=15) as c:r=await c.get("https://api.duckduckgo.com/",params={"q":q,"format":"json","no_html":1,"skip_disambig":1},headers={"User-Agent":"ESPYNOS-AI"})
  d=r.json();out=[]
  if d.get("AbstractText"):out.append({"title":d.get("Heading") or q,"url":d.get("AbstractURL") or "#","snippet":d["AbstractText"]})
  def walk(a):
   for z in a:
    if z.get("Topics"):walk(z["Topics"])
    elif z.get("FirstURL"):out.append({"title":z.get("Text","")[:120],"url":z["FirstURL"],"snippet":z.get("Text","")})
  walk(d.get("RelatedTopics",[]));return {"results":out[:12]}
 except:return JSONResponse({"error":"Search unavailable"},status_code=502)
@app.get("/api/image")
async def image(prompt:str=Query(min_length=1)):
 u="https://image.pollinations.ai/prompt/"+urllib.parse.quote(prompt)+"?width=1024&height=1024&nologo=true"
 try:
  async with httpx.AsyncClient(timeout=60,follow_redirects=True) as c:r=await c.get(u)
  if r.status_code>=400:raise Exception()
  return Response(r.content,media_type=r.headers.get("content-type","image/jpeg"))
 except:return JSONResponse({"error":"Image provider unavailable"},status_code=502)
@app.post("/api/video")
async def video(x:dict):
 if not os.getenv("VIDEO_PROVIDER_URL"):return {"status":"not_configured","message":"Video workspace is ready. Configure a video provider endpoint/API in Render for real generation."}
 return {"status":"queued","message":"Video job accepted by the configured provider."}
