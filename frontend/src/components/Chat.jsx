import MangaResults from "./MangaResults";

const BACKEND = "http://localhost:8000";

function parseMarkdown(text) {
  // Suporte básico a *italic* e **bold**
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br/>");
}

function UserBubble({ content }) {
  return (
    <div className="msg-row msg-row--user">
      <div className="bubble bubble--user">{content}</div>
    </div>
  );
}

function AssistantBubble({ content, recommendations }) {
  const hasRecs = recommendations && recommendations.length > 0;

  return (
    <div className="msg-row msg-row--assistant">
      <div className="avatar">卷</div>
      <div className="assistant-content">
        {content && (
          <div
            className="bubble bubble--assistant"
            dangerouslySetInnerHTML={{ __html: parseMarkdown(content) }}
          />
        )}
        {hasRecs && <MangaResults items={recommendations} />}
        {recommendations && recommendations.length === 0 && content && (
          <p className="no-results">Nenhum manga encontrado para esse critério.</p>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="msg-row msg-row--assistant">
      <div className="avatar">卷</div>
      <div className="bubble bubble--assistant typing">
        <span /><span /><span />
      </div>
    </div>
  );
}

export default function Chat({ messages, loading }) {
  return (
    <div className="chat">
      {messages.map((msg, i) =>
        msg.role === "user" ? (
          <UserBubble key={i} content={msg.content} />
        ) : (
          <AssistantBubble
            key={i}
            content={msg.content}
            recommendations={msg.recommendations}
          />
        )
      )}
      {loading && <TypingIndicator />}
    </div>
  );
}
