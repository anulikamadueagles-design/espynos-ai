import os,urllib.parse,httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
app=FastAPI(title="ESPYNOS-AI");KEY=os.getenv("GEMINI_API_KEY","")
class Chat(BaseModel): message:str; history:list=[]; model:str="gemini-2.5-flash"
@app.get("/") 
def home(): return FileResponse("index.html")
@app.get("/manifest.json")
def manifest(): return FileResponse("manifest.json")
@app.get("/api/health")
def health(): return {"ok":True,"ai":bool(KEY)}
@app.post("/api/chat")
async def chat(x:Chat):
 if not KEY:return {"error":"GEMINI_API_KEY is not configured on Render."}
 contents=[{"role":"user" if m.get("role")=="user" else "model","parts":[{"text":str(m.get("text",""))}]} for m in x.history[-12:]]
 contents.append({"role":"user","parts":[{"text":x.message}]})
 payload={"system_instruction":{"parts":[{"text":"You are ESPYNOS-AI, a helpful coding, research and productivity assistant. Created by David Kamsi Elvis / Vectors element tech."}]},"contents":contents,"generationConfig":{"temperature":0.7,"maxOutputTokens":4096}}
 url=f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(x.model)}:generateContent?key={urllib.parse.quote(KEY)}"
 async with httpx.AsyncClient(timeout=90) as c:r=await c.post(url,json=payload)
 if r.status_code>=400:return {"error":f"Gemini API error {r.status_code}: {r.text[:500]}"}
 d=r.json();text="".join(p.get("text","") for c in d.get("candidates",[]) for p in c.get("content",{}).get("parts",[]));return {"text":text or "No response."}
@app.get("/api/search")
async def search(q:str):
 u="https://api.duckduckgo.com/?"+urllib.parse.urlencode({"q":q,"format":"json","no_html":1,"skip_disambig":1})
 async with httpx.AsyncClient(timeout=20,headers={"User-Agent":"ESPYNOS-AI"}) as c:r=await c.get(u)
 d=r.json();out=[]
 if d.get("AbstractURL"):out.append({"title":d.get("Heading",q),"url":d["AbstractURL"],"snippet":d.get("AbstractText","")})
 for z in d.get("RelatedTopics",[])[:15]:
  if z.get("FirstURL"):out.append({"title":z.get("Text","")[:100],"url":z["FirstURL"],"snippet":z.get("Text","")})
 return {"results":out}
