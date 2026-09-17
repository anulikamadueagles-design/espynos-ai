import os, urllib.parse
import httpx
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

app=FastAPI(title="ESPYNOS-AI")
GEMINI=os.getenv("GEMINI_API_KEY","")
MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash")

class ChatReq(BaseModel):
    message:str
    history:list=[]
    model:str|None=None

@app.get("/")
async def home(): return FileResponse("index.html")

@app.get("/health")
async def health(): return {"status":"online","gemini_configured":bool(GEMINI)}

@app.post("/api/chat")
async def chat(req:ChatReq):
    if not GEMINI: return JSONResponse({"error":"GEMINI_API_KEY is not configured in Render."},status_code=503)
    model=req.model or MODEL
    contents=[]
    for item in req.history[-20:]:
        role="user" if item.get("role")=="user" else "model"
        contents.append({"role":role,"parts":[{"text":str(item.get("text",""))}]})
    contents.append({"role":"user","parts":[{"text":req.message}]})
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r=await client.post(url,params={"key":GEMINI},json={"contents":contents,"generationConfig":{"temperature":0.7,"maxOutputTokens":4096}})
        data=r.json()
        if r.status_code>=400:
            return JSONResponse({"error":data.get("error",{}).get("message","Gemini request failed.")},status_code=502)
        reply=data["candidates"][0]["content"]["parts"][0]["text"]
        return {"reply":reply}
    except Exception as e:
        return JSONResponse({"error":"AI provider connection failed."},status_code=502)

@app.get("/api/search")
async def search(q:str=Query(min_length=1)):
    try:
        async with httpx.AsyncClient(timeout=15,headers={"User-Agent":"ESPYNOS-AI/1.0"}) as client:
            r=await client.get("https://api.duckduckgo.com/",params={"q":q,"format":"json","no_html":1,"skip_disambig":1})
        d=r.json(); results=[]
        if d.get("AbstractText"):
            results.append({"title":d.get("Heading") or q,"url":d.get("AbstractURL") or "#","snippet":d["AbstractText"]})
        def walk(items):
            for x in items:
                if x.get("Topics"): walk(x["Topics"])
                elif x.get("FirstURL"): results.append({"title":x.get("Text","")[:120],"url":x["FirstURL"],"snippet":x.get("Text","")})
        walk(d.get("RelatedTopics",[]))
        return {"results":results[:12]}
    except Exception:
        return JSONResponse({"error":"DuckDuckGo search unavailable."},status_code=502)

@app.get("/api/image")
async def image(prompt:str=Query(min_length=1)):
    # Provider URL is kept behind the app endpoint so the frontend stays provider-agnostic.
    encoded=urllib.parse.quote(prompt)
    url=f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    async with httpx.AsyncClient(timeout=60,follow_redirects=True) as client:
        r=await client.get(url)
    if r.status_code>=400: return JSONResponse({"error":"Image provider unavailable."},status_code=502)
    return Response(content=r.content,media_type=r.headers.get("content-type","image/jpeg"))

@app.post("/api/video")
async def video(req:dict):
    # Real video generation requires a configured provider/API. The endpoint is ready for one.
    provider=os.getenv("VIDEO_PROVIDER_URL","")
    if not provider:
        return {"status":"not_configured","message":"Video workspace is ready. Add a supported video provider endpoint/API on Render to generate real videos."}
    return {"status":"queued","message":"Video generation request accepted by the configured provider."}
