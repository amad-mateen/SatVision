import React from 'react';

/* ─── ImageModal ─────────────────────────────────────────────────── */
const ImageModal = ({ url, date, title, source, onClose }) => {
  if (!url) return null;
  const freshUrl = `${url}?t=${new Date().getTime()}`;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        backgroundColor: 'rgba(0,0,0,0.6)',
        backdropFilter: 'blur(8px)',
        display: 'flex', justifyContent: 'center', alignItems: 'center',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          width: '90%', maxWidth: '820px', maxHeight: '90vh',
          display: 'flex', flexDirection: 'column', gap: '0',
          boxShadow: '0 24px 80px var(--shadow-color)',
          overflow: 'hidden',
          animation: 'slideDown 0.2s ease',
        }}
        className="theme-transition"
      >
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-color)',
        }}>
          <div>
            <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '15px', fontWeight: '600' }}>
              {title}
            </h3>
            <div style={{ marginTop: '4px', fontSize: '13px', color: 'var(--text-muted)' }}>
              Capture date: <strong style={{ color: 'var(--text-main)' }}>{date || '—'}</strong>
              <span style={{ margin: '0 8px', opacity: 0.4 }}>·</span>
              Source: <strong style={{ color: 'var(--text-main)' }}>{source || 'Sentinel-2'}</strong>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              border: '1px solid var(--border-color)', background: 'var(--bg-card-hover)',
              color: 'var(--text-main)', borderRadius: '6px',
              width: '32px', height: '32px',
              cursor: 'pointer', fontSize: '15px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'border-color 0.15s, color 0.15s, background-color 0.15s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.color = 'var(--text-main)'; }}
          >
            ✕
          </button>
        </div>

        {/* Image */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', justifyContent: 'center', alignItems: 'center', background: 'var(--bg-app)', minHeight: '220px' }}>
          <img
            src={freshUrl}
            alt="Satellite preview"
            style={{ maxWidth: '100%', maxHeight: '62vh', objectFit: 'contain', display: 'block' }}
            onError={() => console.error('[ImageModal] Failed to load:', freshUrl)}
          />
        </div>

        {/* Footer */}
        <div style={{ padding: '10px 20px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: '1px solid var(--border-color)',
              color: 'var(--text-muted)', borderRadius: '6px',
              padding: '6px 16px', fontSize: '13px',
              cursor: 'pointer', transition: 'border-color 0.15s, color 0.15s', fontFamily: 'inherit',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--text-main)'; e.currentTarget.style.color = 'var(--text-main)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.color = 'var(--text-muted)'; }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImageModal;
