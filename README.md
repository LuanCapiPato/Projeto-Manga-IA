# MangaAI Recommender

Ferramenta de recomendação de mangás usando uma SLM local (Qwen3:8b via Ollama) + API pública do MangaDex. Totalmente gratuito, sem nuvem, roda no seu PC.

## Como funciona

```
Usuário → React (chat) → FastAPI → Ollama (Qwen3:8b)
                                        ↓ tool call
                              GET api.mangadex.org/manga
                                        ↓ JSON com até 300 obras
                              SLM filtra por capítulos, data, sinopse
                                        ↓
                              5 recomendações com justificativa
```

A SLM extrai automaticamente da frase do usuário:
- **Filtros diretos da API**: tags (gêneros), status, demographic, idioma original
- **Filtros pós-busca**: quantidade de capítulos (`lastChapter`), ano de lançamento, características subjetivas da sinopse

## Requisitos

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) instalado
- GPU com ~6GB VRAM (ou roda em CPU, mais lento)

## Setup

### 1. Ollama + Modelo

```bash
# Instala o Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Baixa o modelo (~5GB)
ollama pull qwen3:8b
```

### 2. Backend (Python)

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Servidor disponível em `http://localhost:8000`  
Documentação automática em `http://localhost:8000/docs`

### 3. Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

Interface disponível em `http://localhost:5173`

## Exemplos de uso

- *"quero isekai completado, protagonista que não quer ser herói, mais de 80 capítulos"*
- *"seinen de sobrevivência, sombrio e psicológico, lançado depois de 2015"*
- *"manhwa de romance, protagonista feminina forte, em andamento"*
- *"manga de ação curto (menos de 30 capítulos) para começar hoje"*

## Estrutura

```
manga-recommender/
├── backend/
│   ├── main.py        # Servidor FastAPI + endpoints
│   ├── agent.py       # Loop de tool use com Ollama
│   ├── mangadex.py    # Chamadas à API MangaDex (com paginação)
│   ├── tools.py       # Definição das ferramentas para a SLM
│   ├── prompts.py     # System prompt do agente
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx
        └── components/
            ├── Chat.jsx
            └── MangaResults.jsx
```

## Tecnologias

- **SLM**: Qwen3:8b via Ollama (tool calling nativo, 128K contexto)
- **Backend**: Python + FastAPI + httpx
- **Frontend**: React + Vite
- **API**: MangaDex API v5 (pública, sem autenticação)
# Projeto-Manga-IA
# Projeto-Manga-IA
# Projeto-Manga-IA
# Projeto-Manga-IA
