"""
agent.py — Loop de tool use entre a SLM (Ollama) e as funções Python.
"""

import json
import time
import ollama
from prompts import SYSTEM_PROMPT, SELECTION_PROMPT
from tools import TOOLS
from mangadex import search_manga, get_available_tags

# ── Cores ANSI ────────────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[36m"
YELLOW  = "\033[33m"
GREEN   = "\033[32m"
RED     = "\033[31m"
MAGENTA = "\033[35m"
BLUE    = "\033[34m"

def log(color, prefix, msg):
    print(f"{color}{BOLD}[{prefix}]{RESET} {msg}")

def log_dim(msg):
    print(f"{DIM}  {msg}{RESET}")

def log_section(title):
    bar = "─" * 50
    print(f"\n{DIM}{bar}{RESET}\n{BOLD}{title}{RESET}\n{DIM}{bar}{RESET}")


# ── Estado global da requisição ───────────────────────────────────────────────
current_search_context = None
real_manga_index: dict[str, dict] = {}   # id → manga completo retornado pela API


# ── Tool execution ─────────────────────────────────────────────────────────────
async def execute_tool(tool_name: str, tool_args: dict) -> str:
    global current_search_context, real_manga_index
    t0 = time.time()

    if tool_name == "get_available_tags":
        log(CYAN, "TOOL", "get_available_tags()")
        result = await get_available_tags()
        grouped = {}
        for tag in result:
            grouped.setdefault(tag.get("group", "other"), []).append(tag["name"])
        elapsed = time.time() - t0
        log_dim(f"✓ {sum(len(v) for v in grouped.values())} tags em {len(grouped)} grupos [{elapsed:.2f}s]")
        return json.dumps(grouped, ensure_ascii=False)

    elif tool_name == "set_search_context":
        summary  = tool_args.get("search_summary", "").strip()
        criteria = tool_args.get("selection_criteria", "").strip()
        current_search_context = {"summary": summary, "criteria": criteria}
        log(CYAN, "TOOL", "set_search_context")
        log_dim(f"📌 {summary[:150]}{'...' if len(summary) > 150 else ''}")
        if criteria:
            log_dim(f"🔎 {criteria[:120]}{'...' if len(criteria) > 120 else ''}")
        return json.dumps({"status": "context_set", "summary": summary})

    elif tool_name == "search_manga":
        if "pages" in tool_args:
            tool_args["pages"] = min(int(tool_args.get("pages", 2)), 3)

        inc  = tool_args.get("included_tags", [])
        exc  = tool_args.get("excluded_tags", [])
        stat = tool_args.get("status", [])
        demo = tool_args.get("demographic", [])
        lang = tool_args.get("original_language", [])
        year = tool_args.get("year")
        titl = tool_args.get("title")
        pgs  = tool_args.get("pages", 2)
        ordb = tool_args.get("order_by", "followedCount")

        log(CYAN, "TOOL", f"search_manga() [{pgs} pág × 100 = até {pgs*100} mangas]")
        if inc:  log_dim(f"tags incluídas : {', '.join(inc)}")
        if exc:  log_dim(f"tags excluídas : {', '.join(exc)}")
        if stat: log_dim(f"status         : {', '.join(stat)}")
        if demo: log_dim(f"demographic    : {', '.join(demo)}")
        if lang: log_dim(f"idioma         : {', '.join(lang)}")
        if year: log_dim(f"ano            : {year}")
        if titl: log_dim(f"título         : {titl}")
        log_dim(f"ordenação      : {ordb}")

        VALID_ARGS = {"included_tags","excluded_tags","status","demographic",
                      "content_rating","original_language","year","title","order_by","pages"}
        clean_args = {k: v for k, v in tool_args.items() if k in VALID_ARGS}

        mangas = await search_manga(**clean_args)
        elapsed = time.time() - t0

        # ── Guarda índice real de IDs ─────────────────────────────────────────
        for m in mangas:
            real_manga_index[m["id"]] = m

        log_dim(f"✓ {len(mangas)} mangas retornados [{elapsed:.2f}s]  |  índice total: {len(real_manga_index)}")

        return json.dumps({
            "search_context": current_search_context,
            "mangas": mangas,
        }, ensure_ascii=False)

    else:
        log(RED, "TOOL", f"Tool desconhecida: {tool_name}")
        return json.dumps({"error": f"Tool desconhecida: {tool_name}"})


# ── Validação pós-seleção ──────────────────────────────────────────────────────
def validate_and_fix(result: dict) -> dict:
    """
    Descarta recomendações cujo 'id' não estava nos resultados reais da API.
    Repõe campos faltantes a partir do índice real.
    """
    recs = result.get("recommendations", [])
    valid = []
    for r in recs:
        rid = r.get("id", "")
        if rid in real_manga_index:
            # Garante campos críticos vindos da API, não da imaginação da SLM
            real = real_manga_index[rid]
            r["title"]       = real.get("title",       r.get("title"))
            r["tags"]        = real.get("tags",         r.get("tags", []))
            r["status"]      = real.get("status",       r.get("status"))
            r["year"]        = real.get("year",         r.get("year"))
            r["lastChapter"] = real.get("lastChapter",  r.get("lastChapter"))
            r["demographic"] = real.get("demographic",  r.get("demographic"))
            valid.append(r)
        else:
            log(RED, "FILTRO", f"ID inválido removido: '{rid}' — '{r.get('title','?')}'")

    removed = len(recs) - len(valid)
    if removed:
        log(YELLOW, "FILTRO", f"{removed} manga(s) alucinado(s) removido(s). Restam {len(valid)}.")

    result["recommendations"] = valid
    return result


# ── Context summary ────────────────────────────────────────────────────────────
def build_context_summary(history: list[dict]) -> str:
    if not history:
        return ""
    
    user_messages = [m["content"] for m in history if m["role"] == "user"]
    if not user_messages:
        return ""
    
    context = "=== HISTÓRICO DE PEDIDOS DO USUÁRIO ===\n"
    for i, msg in enumerate(user_messages[-6:], 1):
        context += f"{i}. \"{msg}\"\n"
    
    return f"""{context}
INSTRUÇÕES OBRIGATÓRIAS PARA ESTA NOVA MENSAGEM:
- Você DEVE começar chamando `set_search_context` para atualizar o contexto.
- Depois chame `search_manga` com critérios refinados (combine histórico + novo pedido).
- Preserve conceitos abstratos anteriores (dark, psicológico, revenge, trauma, atmosfera, etc.).
- Só gere o JSON final após ter os resultados da nova busca."""

# ── Agent loop ─────────────────────────────────────────────────────────────────
async def run_agent(user_message: str, history: list[dict]) -> dict:
    global current_search_context, real_manga_index
    
    current_search_context = None
    real_manga_index = {}
    
    log_section("NOVA REQUISIÇÃO")
    log(BLUE, "USER", user_message)
    
    print(f"\n[DEBUG] Tamanho do history recebido: {len(history)}")
    for i, msg in enumerate(history):
        role = msg.get("role")
        content = msg.get("content", "")[:150] + "..." if len(str(msg.get("content",""))) > 150 else msg.get("content","")
        print(f"  {i} | {role:>10} | {content}")
    
    ctx_summary = build_context_summary(history)
    if ctx_summary:
        log(MAGENTA, "CTX", ctx_summary[:600] + "..." if len(ctx_summary) > 600 else ctx_summary)

    # Monta as mensagens com contexto forte
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history)

    if ctx_summary:
        messages.append({"role": "system", "content": ctx_summary})

    messages.append({"role": "user", "content": user_message})

    # === PARTE 3: Reforço extra de contexto abstrato ===
    if len(history) >= 2:
        messages.append({
            "role": "system", 
            "content": "Lembre-se: preserve conceitos abstratos do histórico (tom, tema emocional, intensidade, estilo narrativo, vibe). Não perca a essência da conversa anterior. Refine mantendo o que já foi pedido."
        })

    max_iterations = 7
    iteration = 0
    t_total = time.time()
    selection_injected = False

    while iteration < max_iterations:
        iteration += 1
        log_section(f"ITERAÇÃO {iteration}")
        log(YELLOW, "SLM", "Pensando...")

        t0 = time.time()
        response = ollama.chat(
            model="qwen3:8b",
            messages=messages,
            tools=TOOLS,
            options={"temperature": 0.2, "top_p": 0.85, "think": True},
        )
        elapsed = time.time() - t0
        msg = response.message

        # Thinking
        thinking = getattr(msg, "thinking", None)
        if thinking and thinking.strip():
            log(MAGENTA, "THINK", f"[{elapsed:.1f}s]")
            for line in thinking.strip().splitlines():
                if line.strip():
                    print(f"  {DIM}{line}{RESET}")

        # Conteúdo textual
        if msg.content and msg.content.strip():
            log(GREEN, "SLM", f"[{elapsed:.1f}s]")
            for line in msg.content.strip().splitlines():
                if line.strip():
                    print(f"  {line}")

        # ── Tool calls ────────────────────────────────────────────────────────
        if msg.tool_calls:
            log(YELLOW, "SLM", f"{len(msg.tool_calls)} tool call(s)")
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.function.name,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                tool_result = await execute_tool(tc.function.name, tc.function.arguments or {})
                messages.append({"role": "tool", "content": tool_result})

                # Após search_manga — injeta prompt de seleção UMA vez
                if tc.function.name == "search_manga" and not selection_injected:
                    selection_injected = True
                    ids_sample = list(real_manga_index.keys())[:8]  # mais exemplos
                    
                    full_selection_prompt = SELECTION_PROMPT + f"""

                HISTÓRICO DE CRITÉRIOS:
                {current_search_context.get('summary', '') if current_search_context else ''}
                {current_search_context.get('criteria', '') if current_search_context else ''}

                IMPORTANTE: Use SOMENTE estes IDs: {ids_sample}...
                Seja fiel ao contexto acima ao escolher."""
                    
                    messages.append({"role": "user", "content": full_selection_prompt})
                    log(CYAN, "CTX", f"Prompt de seleção injetado com {len(real_manga_index)} mangas")
        # ── Sem tool calls — tenta parsear resposta final ─────────────────────
        else:
            content = msg.content or ""
            json_str = None

            if "```json" in content:
                try:
                    s = content.index("```json") + 7
                    e = content.index("```", s)
                    json_str = content[s:e].strip()
                except ValueError:
                    pass

            if json_str is None and "{" in content:
                try:
                    s = content.index("{")
                    e = content.rindex("}") + 1
                    json_str = content[s:e]
                except ValueError:
                    pass

            if json_str:
                try:
                    result = json.loads(json_str)
                    if result.get("recommendations") is not None:
                        result = validate_and_fix(result)
                        if current_search_context:
                            result["search_context"] = current_search_context
                        n = len(result["recommendations"])
                        total_time = time.time() - t_total
                        log(GREEN, "SLM", f"Resposta final [{elapsed:.1f}s]")
                        log_section(f"CONCLUÍDO — {n} recomendações em {total_time:.1f}s")
                        for i, r in enumerate(result["recommendations"], 1):
                            log_dim(f"{i}. {r.get('title','?')} | {r.get('id','?')[:8]}... | {r.get('lastChapter','?')} cap.")
                        print()
                        return result
                except (json.JSONDecodeError, ValueError) as e:
                    log(RED, "ERRO", f"JSON inválido: {e}")

            # JSON ainda não veio — deixa o loop continuar
            log(YELLOW, "SLM", "Sem JSON válido ainda, continuando...")
            messages.append({"role": "assistant", "content": content})

    log(RED, "ERRO", "Máximo de iterações atingido")
    return {"message": "Não consegui completar a busca. Tente reformular seu pedido.", "recommendations": []}