"""
main.py — Servidor FastAPI.
Expõe os endpoints que o frontend React consome.
"""

import asyncio
import re
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from mangadex import load_tags, get_cover_url_by_id
from agent import run_agent

app = FastAPI(title="MangaAI Recommender", version="1.0.0")

# CORS — permite o frontend React (porta 5173) acessar o backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str   # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Pré-carrega as tags do MangaDex na inicialização."""
    print("[Server] Carregando tags do MangaDex...")
    await load_tags()
    print("[Server] Tags carregadas. Servidor pronto.")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


MANGADEX_HEADERS = {
    "User-Agent": "MangaAI-Recommender/1.0 (local app; github.com/seu-user/manga-recommender)",
    "Accept": "application/json",
}

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

def is_valid_uuid(value: str) -> bool:
    return bool(UUID_RE.match(value.lower()))

async def fetch_covers_parallel(manga_ids: list[str]) -> dict[str, str | None]:
    """Busca as URLs de capa de vários mangas em paralelo.
    Ignora IDs que não são UUIDs válidos — a IA às vezes alucina slugs de texto.
    """
    async def fetch_one(client: httpx.AsyncClient, manga_id: str):
        if not is_valid_uuid(manga_id):
            print(f"[cover] IGNORADO (não é UUID): {manga_id}")
            return manga_id, None
        try:
            resp = await client.get(
                f"https://api.mangadex.org/manga/{manga_id}",
                params={"includes[]": "cover_art"},
                headers=MANGADEX_HEADERS,
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            url = get_cover_url_by_id(data)
            print(f"[cover] {manga_id[:8]}... → {url}")
            return manga_id, url
        except Exception as e:
            print(f"[cover] ERRO {manga_id[:8]}...: {e}")
            return manga_id, None

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetch_one(client, mid) for mid in manga_ids]
        results = await asyncio.gather(*tasks)

    return dict(results)



@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Endpoint principal.
    """
    # Converte o histórico
    history = [{"role": m.role, "content": m.content} for m in req.history]

    result = await run_agent(req.message, history)

    # Busca capas
    recs = result.get("recommendations", [])
    if recs:
        covers = await fetch_covers_parallel([r["id"] for r in recs])
        for rec in recs:
            rec["cover_url"] = covers.get(rec["id"])

    # === MELHORIA CRÍTICA: Salva contexto no histórico para próximas mensagens ===
    assistant_content = result.get("message", "Aqui estão as recomendações encontradas.")

    if result.get("search_context"):
        ctx = result["search_context"]
        assistant_content += f"\n\n[Contexto da busca: {ctx.get('summary', '')}]"

    # Adiciona ao histórico (o frontend deve salvar isso)
    result["assistant_message_for_history"] = {
        "role": "assistant",
        "content": assistant_content
    }

    return result


@app.get("/proxy/cover")
async def proxy_cover(url: str):
    """
    Proxy de imagens do MangaDex.
    Baixa a imagem no backend e serve os bytes — evita CORS e 403.
    User-Agent obrigatório conforme docs do MangaDex.
    """
    if not url.startswith("https://uploads.mangadex.org"):
        raise HTTPException(status_code=400, detail="URL inválida")

    headers = {
        "User-Agent": "MangaAI-Recommender/1.0 (local app; github.com/seu-user/manga-recommender)",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://mangadex.org/",
    }

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

            image_bytes = resp.content
            content_type = resp.headers.get("content-type", "image/jpeg")

            from fastapi.responses import Response
            return Response(
                content=image_bytes,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},  # cache 24h
            )
        except httpx.HTTPStatusError as e:
            print(f"[proxy/cover] HTTP {e.response.status_code} para {url}")
            raise HTTPException(status_code=502, detail=f"MangaDex retornou {e.response.status_code}")
        except httpx.HTTPError as e:
            print(f"[proxy/cover] Erro de conexão: {e}")
            raise HTTPException(status_code=502, detail="Erro ao buscar imagem")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)