from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from webthinker import search_web,WebThinkerAgent
from dotenv import load_dotenv
import aiohttp
from langchain_openai import OpenAI
from langchain_ollama import OllamaLLM
from ast import literal_eval
load_dotenv('.env')
from os import getenv
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    timeout = aiohttp.ClientTimeout(total=10)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/113.0.0.0"
    }
    aiohttp_session = aiohttp.ClientSession(headers=headers, timeout=timeout)
    logging.info("Aiohttp session started!")

    if literal_eval(getenv('use_ollama')):
        client = OllamaLLM(
            model=getenv('EXTRACTION_MODEL'),
            temperature=0.1,
            base_url=getenv('OLLAMA_URL')
        )
    else:
        client = OpenAI(
            model=getenv('EXTRACTION_MODEL'),
            temperature=0.1,
            api_key=getenv('OPENAI_API_KEY'),
            max_tokens=2000
        )

    app.state.webthinker = WebThinkerAgent(client)
    app.state.aiohttp_session = aiohttp_session
    logging.info("WebThinker agent initialized!")


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.aiohttp_session.close()
    app.state.webthinker = None
    logging.info("WebThinker agent closed!")
    logging.info("Aiohttp session and webthinker closed!")

@app.get("/search")
async def search(request: Request, q: str = Query(..., min_length=2),):
    try:
        results = await search_web(request,q)
        return {"query": q, "results": results}
    except Exception as e:
        logging.error(f"Search failed: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


