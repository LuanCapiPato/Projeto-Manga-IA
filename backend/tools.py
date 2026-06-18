"""
tools.py — Definição das ferramentas que a SLM pode chamar.
Cada tool tem um schema JSON que o Ollama usa para extrair os parâmetros.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_available_tags",
            "description": (
                "Retorna todas as tags/gêneros disponíveis no MangaDex. "
                "Chame isso PRIMEIRO quando precisar saber quais tags existem "
                "antes de fazer uma busca. Use para descobrir o nome exato das tags."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_search_context",
            "description": (
                "Define o contexto/resumo do que você está procurando ANTES de chamar search_manga. "
                "Seja claro, específico e fiel ao pedido do usuário. "
                "Isso será devolvido junto com os resultados da busca para você não se perder."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "search_summary": {
                        "type": "string",
                        "description": "Resumo claro e objetivo do que está sendo buscado (em português)."
                    },
                    "selection_criteria": {
                        "type": "string",
                        "description": (
                            "Critérios que você vai usar para selecionar os melhores mangas "
                            "dentre os resultados (ex: foco em romance lento, personagens fortes, "
                            "evitar harem, etc)."
                        )
                    }
                },
                "required": ["search_summary"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_manga",
            "description": (
                "Busca mangas no MangaDex com filtros avançados. "
                "Retorna até 200 mangas com título, sinopse, tags, status, "
                "lastChapter, year e URL da capa. "
                "Use os filtros disponíveis na API diretamente, "
                "e depois analise os campos lastChapter, year e description "
                "para aplicar filtros que a API não suporta nativamente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "included_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Tags que o manga DEVE ter. Use nomes exatos em inglês "
                            "como retornados por get_available_tags. Ex: ['Action', 'Isekai']"
                        ),
                    },
                    "excluded_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Tags que o manga NÃO deve ter. Ex: ['Harem', 'Ecchi']"
                        ),
                    },
                    "status": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["ongoing", "completed", "hiatus", "cancelled"],
                        },
                        "description": "Status de publicação. Ex: ['completed'] para mangas finalizados.",
                    },
                    "demographic": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["shounen", "shoujo", "seinen", "josei"],
                        },
                        "description": "Público-alvo. Ex: ['seinen'] para adultos.",
                    },
                    "content_rating": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["safe", "suggestive", "erotica", "pornographic"],
                        },
                        "description": "Classificação de conteúdo. Padrão: ['safe', 'suggestive'].",
                    },
                    "original_language": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Idioma original. Use códigos ISO: 'ja' (japonês/manga), "
                            "'ko' (coreano/manhwa), 'zh' (chinês/manhua)."
                        ),
                    },
                    "year": {
                        "type": "integer",
                        "description": "Ano de publicação. Ex: 2020 para mangas de 2020.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Busca por título ou palavra-chave no nome.",
                    },
                    "order_by": {
                        "type": "string",
                        "enum": ["followedCount", "rating", "updatedAt", "createdAt"],
                        "description": "Ordenação dos resultados. Padrão: followedCount.",
                    },
                    "pages": {
                        "type": "integer",
                        "description": (
                            "Quantas páginas de 100 mangas buscar. "
                            "Use 1 para buscas simples, 2-3 para maior cobertura. "
                            "Máximo: 3."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
]
