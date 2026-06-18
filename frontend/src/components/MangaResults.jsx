import { useState } from "react";

const BACKEND = "http://localhost:8000";

const STATUS_LABELS = {
  ongoing: "Em andamento",
  completed: "Completo",
  hiatus: "Hiato",
  cancelled: "Cancelado",
};

const STATUS_COLORS = {
  ongoing: "#4ade80",
  completed: "#60a5fa",
  hiatus: "#fbbf24",
  cancelled: "#f87171",
};

const DEMO_LABELS = {
  shounen: "Shounen",
  shoujo: "Shoujo",
  seinen: "Seinen",
  josei: "Josei",
};

function MangaCard({ item, index }) {
  const [imgError, setImgError] = useState(false);

  const coverSrc =
    item.cover_url && !imgError
      ? `${BACKEND}/proxy/cover?url=${encodeURIComponent(item.cover_url)}`
      : null;

  const statusColor = STATUS_COLORS[item.status] || "#888";

  return (
    <div className="manga-card" style={{ animationDelay: `${index * 80}ms` }}>
      <div className="manga-cover">
        {coverSrc ? (
          <img
            src={coverSrc}
            alt={item.title}
            onError={() => setImgError(true)}
            loading="lazy"
          />
        ) : (
          <div className="manga-cover-placeholder">
            <span>卷</span>
          </div>
        )}
        <div
          className="manga-status-badge"
          style={{ background: statusColor }}
        >
          {STATUS_LABELS[item.status] || item.status || "—"}
        </div>
      </div>

      <div className="manga-info">
        <h3 className="manga-title">{item.title}</h3>

        <div className="manga-meta">
          {item.year && <span className="meta-chip">{item.year}</span>}
          {item.demographic && (
            <span className="meta-chip meta-chip--demo">
              {DEMO_LABELS[item.demographic] || item.demographic}
            </span>
          )}
          {item.lastChapter && (
            <span className="meta-chip meta-chip--chapters">
              {Math.round(item.lastChapter)} cap.
            </span>
          )}
        </div>

        <div className="manga-tags">
          {(item.tags || []).slice(0, 5).map((tag) => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>

        {item.reason && (
          <p className="manga-reason">
            <span className="reason-icon">✦</span> {item.reason}
          </p>
        )}
      </div>
    </div>
  );
}

export default function MangaResults({ items }) {
  if (!items || items.length === 0) return null;

  return (
    <div className="manga-results">
      <p className="results-label">
        {items.length} recomendação{items.length !== 1 ? "ões" : ""}
      </p>
      <div className="manga-grid">
        {items.map((item, i) => (
          <MangaCard key={item.id || i} item={item} index={i} />
        ))}
      </div>
    </div>
  );
}
