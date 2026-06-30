import React from 'react';
import { getSafeDownloadUrl } from '../utils/helpers';

const Sidebar = ({ history, expandedHistoryId, isMobile, sidebarOpen, onLoad, onClose }) => (
  <>
    {/* Mobile backdrop */}
    {isMobile && sidebarOpen && (
      <div
        onClick={onClose}
        style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 2999, backdropFilter: 'blur(4px)' }}
      />
    )}

    <div
      style={{
        width: isMobile ? '290px' : '360px',
        backgroundColor: 'var(--bg-sidebar)',
        backdropFilter: 'var(--glass-blur)',
        borderRight: '1px solid var(--border-color)',
        padding: '20px',
        display: 'flex', flexDirection: 'column', gap: '20px',
        overflowY: 'auto',
        position: isMobile ? 'absolute' : 'relative',
        height: '100%',
        left: isMobile ? (sidebarOpen ? '0' : '-100%') : '0',
        zIndex: 3000,
        transition: 'left 0.3s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.3s, border-color 0.3s',
        boxShadow: isMobile && sidebarOpen ? '4px 0 20px var(--shadow-color)' : 'none',
        flexShrink: 0,
      }}
      className="textured-overlay theme-transition"
    >
      <div style={{ position: 'relative', zIndex: 2 }}>
        <h3 style={{
          color: 'var(--text-main)', fontSize: '15px', fontWeight: '600',
          borderBottom: '2px solid var(--accent)',
          paddingBottom: '10px', marginBottom: '16px',
        }}>
          Session History
        </h3>

        {history.length === 0 ? (
          <EmptyState />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {history.map((item) => (
              <HistoryCard
                key={item.id}
                item={item}
                isExpanded={expandedHistoryId === item.id}
                onClick={() => onLoad(item)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  </>
);

/* ─── Empty state ──────────────────────────────────────────────────── */
const EmptyState = () => (
  <div style={{
    color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center',
    marginTop: '16px', padding: '24px 20px',
    backgroundColor: 'var(--bg-app)', borderRadius: '8px',
    border: '1px dashed var(--border-color)', lineHeight: '1.6',
  }} className="theme-transition">
    No analyses run yet.
    <br />
    Use the controls to analyse a region.
  </div>
);

/* ─── History card ─────────────────────────────────────────────────── */
const HistoryCard = ({ item, isExpanded, onClick }) => {
  const isSAR     = item.meta?.latest_source?.includes('SAR');
  const floodArea = item.meta?.report?.metrics?.flood_sq_km;

  return (
    <div
      onClick={onClick}
      style={{
        backgroundColor: 'var(--bg-card)',
        padding: '13px',
        borderRadius: '8px',
        border: isExpanded ? '1px solid var(--accent)' : '1px solid var(--border-color)',
        display: 'flex', flexDirection: 'column', gap: '7px',
        cursor: 'pointer',
        transition: 'border-color 0.2s, background-color 0.2s, box-shadow 0.2s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--accent)';
        e.currentTarget.style.boxShadow = '0 0 0 1px var(--accent-glow)';
        e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = isExpanded ? 'var(--accent)' : 'var(--border-color)';
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.backgroundColor = 'var(--bg-card)';
      }}
    >
      {/* Name + download */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <div style={{ color: 'var(--text-main)', fontSize: '13px', fontWeight: '600', lineHeight: '1.4', flex: 1 }}>
          {item.name}
        </div>
        {item.meta?.report?.download_url && (
          <a
            href={getSafeDownloadUrl(item.meta.report.download_url)}
            target="_blank" rel="noopener noreferrer"
            title="Download PDF Report"
            onClick={(e) => e.stopPropagation()}
            style={{
              textDecoration: 'none',
              backgroundColor: 'var(--accent-glow)',
              color: 'var(--accent)',
              border: '1px solid var(--border-color)',
              padding: '3px 8px', borderRadius: '5px',
              fontSize: '11px', fontWeight: '500',
              flexShrink: 0, transition: 'background 0.15s, border-color 0.15s, color 0.15s',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--accent)';
              e.currentTarget.style.color = 'var(--button-text)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--accent-glow)';
              e.currentTarget.style.color = 'var(--accent)';
            }}
          >
            Report
          </a>
        )}
      </div>

      {/* Date + sensor badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Date: {item.date}</span>
        <SensorBadge isSAR={isSAR} />
      </div>

      {/* Flood area */}
      {floodArea > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#ff7b72', fontSize: '12px' }}>
          <span style={{ width: '8px', height: '8px', backgroundColor: '#ff7b72', borderRadius: '50%', display: 'inline-block', flexShrink: 0 }} />
          {floodArea.toFixed(1)} sq km flooded
        </div>
      )}

      {/* Expanded report text */}
      {isExpanded && item.meta?.report?.text && (
        <div style={{
          marginTop: '4px', padding: '10px',
          backgroundColor: 'var(--bg-app)', borderRadius: '6px',
          border: '1px solid var(--border-color)',
          color: 'var(--text-main)', fontSize: '12px', lineHeight: '1.65',
          maxHeight: '240px', overflowY: 'auto', whiteSpace: 'pre-wrap',
          animation: 'slideDown 0.15s ease',
        }} className="theme-transition">
          {item.meta.report.text}
        </div>
      )}
    </div>
  );
};

/* ─── Sensor badge ─────────────────────────────────────────────────── */
const SensorBadge = ({ isSAR }) => (
  <span style={{
    fontSize: '10px', fontWeight: '600', padding: '2px 7px', borderRadius: '4px',
    letterSpacing: '0.04em',
    backgroundColor: isSAR ? 'rgba(210,153,34,0.1)' : 'rgba(35,134,54,0.1)',
    color:           isSAR ? '#d29922' : '#3fb950',
    border:          isSAR ? '1px solid rgba(210,153,34,0.2)' : '1px solid rgba(35,134,54,0.2)',
  }}>
    {isSAR ? 'SAR' : 'Optical'}
  </span>
);

export default Sidebar;
