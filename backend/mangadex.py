"""
mangadex.py — Todas as chamadas à API do MangaDex.
Responsável por buscar tags, mangas (com paginação) e montar URLs de capa.
"""

import asyncio
import httpx
from typing import Optional

BASE_URL = "https://api.mangadex.org"
COVER_URL = "https://uploads.mangadex.org/covers"

# Cache de tags em memória (carregado uma vez na inicialização)
_tag_cache: dict[str, str] = {}  # nome → uuid


async def load_tags() -> dict[str, str]:
    """Carrega todas as tags do MangaDex e armazena em cache."""
    global _tag_cache
    if _tag_cache:
        return _tag_cache

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE_URL}/manga/tag")
        resp.raise_for_status()
        data = resp.json()

    _tag_cache = {
        tag["attributes"]["name"]["en"]: tag["id"]
        for tag in data["data"]
    }
    return _tag_cache


async def resolve_tag_ids(tag_names: list[str]) -> list[str]:
    """Converte nomes de tags em UUIDs. Ignora tags inválidas."""
    tags = await load_tags()
    ids = []
    for name in tag_names:
        # Busca case-insensitive
        for tag_name, tag_id in tags.items():
            if tag_name.lower() == name.lower():
                ids.append(tag_id)
                break
    return ids


def get_cover_url(manga: dict) -> Optional[str]:
    """Monta a URL da capa 512px a partir dos relacionamentos do manga."""
    for rel in manga.get("relationships", []):
        if rel["type"] == "cover_art":
            filename = rel.get("attributes", {}).get("fileName")
            if filename:
                manga_id = manga["id"]
                return f"{COVER_URL}/{manga_id}/{filename}.512.jpg"
    return None


def get_cover_url_by_id(manga: dict) -> Optional[str]:
    """Alias de get_cover_url — usado pelo main.py na busca paralela de capas."""
    return get_cover_url(manga)


def extract_manga_info(manga: dict) -> dict:
    """Extrai apenas os campos relevantes de um objeto manga da API."""
    attrs = manga.get("attributes", {})

    # Título: prefere pt-br, depois en, depois o primeiro disponível
    title_obj = attrs.get("title", {})
    title = (
        title_obj.get("pt-br")
        or title_obj.get("en")
        or title_obj.get("ja-ro")
        or next(iter(title_obj.values()), "Sem título")
    )

    # Descrição: prefere pt-br, depois en
    desc_obj = attrs.get("description", {})
    description = (
        desc_obj.get("pt-br")
        or desc_obj.get("en")
        or next(iter(desc_obj.values()), "")
    )

    # Tags como lista de nomes em inglês
    tags = [
        t["attributes"]["name"].get("en", "")
        for t in attrs.get("tags", [])
        if t.get("attributes", {}).get("name", {}).get("en")
    ]

    return {
        "id": manga["id"],
        "title": title,
        "description": description[:600],  # limita pra não explodir contexto
        "tags": tags,
        "status": attrs.get("status"),
        "year": attrs.get("year"),
        "lastChapter": attrs.get("lastChapter"),
        "lastVolume": attrs.get("lastVolume"),
        "demographic": attrs.get("publicationDemographic"),
        "contentRating": attrs.get("contentRating"),
        "originalLanguage": attrs.get("originalLanguage"),
        "cover_url": get_cover_url(manga),
    }


async def search_manga(
    included_tags: list[str] = [],
    excluded_tags: list[str] = [],
    status: list[str] = [],
    demographic: list[str] = [],
    content_rating: list[str] = ["safe", "suggestive"],
    original_language: list[str] = [],
    year: Optional[int] = None,
    title: Optional[str] = None,
    order_by: str = "followedCount",  # followedCount | rating | updatedAt | createdAt
    pages: int = 2,  # quantas páginas buscar (100 por página)
) -> list[dict]:
    """
    Busca mangas na API com filtros avançados.
    Faz `pages` chamadas paginadas, retornando até pages*100 mangas.
    """
    included_ids = await resolve_tag_ids(included_tags)
    excluded_ids = await resolve_tag_ids(excluded_tags)

    all_mangas = []

    async with httpx.AsyncClient(timeout=20) as client:
        for page in range(pages):
            params = {
                "limit": 100,
                "offset": page * 100,
                "order[followedCount]": "desc" if order_by == "followedCount" else "asc",
                "order[rating]": "desc" if order_by == "rating" else "asc",
                "includes[]": ["cover_art"],
                "contentRating[]": content_rating or ["safe", "suggestive"],
            }

            if included_ids:
                params["includedTags[]"] = included_ids
            if excluded_ids:
                params["excludedTags[]"] = excluded_ids
            if status:
                params["status[]"] = status
            if demographic:
                params["publicationDemographic[]"] = demographic
            if original_language:
                params["originalLanguage[]"] = original_language
            if year:
                params["year"] = year
            if title:
                params["title"] = title

            try:
                resp = await client.get(f"{BASE_URL}/manga", params=params)
                resp.raise_for_status()
                data = resp.json()
                mangas = data.get("data", [])
                all_mangas.extend(mangas)

                # Se veio menos de 100, não há mais páginas
                if len(mangas) < 100:
                    break

                # Respeita rate limit (~5 req/s)
                await asyncio.sleep(0.25)

            except httpx.HTTPError as e:
                print(f"[MangaDex] Erro na página {page}: {e}")
                break

    return [extract_manga_info(m) for m in all_mangas]


async def get_available_tags() -> list[dict]:
    """Retorna lista de todas as tags disponíveis com nome e grupo."""
    tags = await load_tags()
    # Também retorna o grupo de cada tag
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE_URL}/manga/tag")
        data = resp.json()

    return [
        {
            "name": t["attributes"]["name"].get("en", ""),
            "group": t["attributes"].get("group", ""),
            "id": t["id"],
        }
        for t in data["data"]
    ]
