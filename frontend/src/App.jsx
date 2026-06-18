import { useState, useRef, useEffect } from "react";
import Chat from "./components/Chat";
import MangaResults from "./components/MangaResults";
import "./App.css";

const BACKEND = "http://localhost:8000";

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Olá! Sou a Quarta Parede. Me diga que tipo de manga você procura — pode ser tão específico quanto quiser. Ex: *\"isekai completado, protagonista que não quer ser herói, mais de 80 capítulos\"*",
      recommendations: null,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const getHistory = () =>
  messages
  .filter((m) => m.role === "user" || m.role === "assistant")
  .filter((m) => m.content && m.content.trim())  // ignora mensagem inicial vazia
  .map((m) => {
    // Se a mensagem tem recomendações, resume para o modelo não perder contexto
    if (m.recommendations && m.recommendations.length > 0) {
      const titles = m.recommendations.map((r) => r.title).join(", ");
      return {
        role: "assistant",
        content: `${m.content} Recomendei: ${titles}.`,
      };
    }
    return { role: m.role, content: m.content };
  });

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await fetch(`${BACKEND}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: getHistory() }),
      });

      if (!res.ok) throw new Error(`Erro ${res.status}`);
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.message || "",
          recommendations: data.recommendations || [],
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ Erro ao conectar com o servidor: ${err.message}. Verifique se o backend está rodando na porta 8000.`,
          recommendations: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="app">
    <header className="header">
    <div className="header-inner">
    <span className="logo">
    <span className="logo-icon">光</span>
    Quarta Parede
    </span>
    <span className="header-sub">Recomendação por IA</span>
    </div>
    </header>

    <main className="main">
    <div className="chat-column">
    <Chat messages={messages} loading={loading} />
    <div ref={bottomRef} />
    </div>
    </main>

    <footer className="footer">
    <div className="input-wrap">
    <textarea
    className="input"
    value={input}
    onChange={(e) => setInput(e.target.value)}
    onKeyDown={handleKey}
    placeholder="Ex: quero um seinen de sobrevivência, sombrio, com mais de 100 capítulos..."
    rows={2}
    disabled={loading}
    />
    <button
    className={`send-btn ${loading ? "loading" : ""}`}
    onClick={send}
    disabled={loading || !input.trim()}
    >
    {loading ? (
      <span className="spinner" />
    ) : (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
      </svg>
    )}
    </button>
    </div>
    <p className="footer-hint">Enter para enviar · Shift+Enter para nova linha</p>
    </footer>
    </div>
  );
}
