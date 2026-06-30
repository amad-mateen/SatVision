import React from 'react';
import { FEATURED_EVENTS } from '../constants/events';

/* ─── Shared input style ─────────────────────────────────────────── */
const inputStyle = {
  height: '50px',
  backgroundColor: 'var(--input-bg)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  color: 'var(--text-main)',
  fontSize: '15px',
  outline: 'none',
  fontFamily: 'inherit',
  transition: 'border-color 0.2s, background-color 0.2s, color 0.2s',
};

const onFocusStyle  = (e) => (e.currentTarget.style.borderColor = 'var(--accent)');
const onBlurStyle   = (e) => (e.currentTarget.style.borderColor = 'var(--border-color)');

/* ─── ControlPanel ───────────────────────────────────────────────── */
const ControlPanel = ({
  isMobile, searchQuery, selectedEvent, targetDate, suggestions,
  showSuggestions, isProcessing, errorMsg, meta,
  onInputChange, onSuggestionSelect, onSearchSubmit, onFeaturedEventChange,
  onDateChange, onDetect, onFocus, onBlur,
}) => {
  const isSARFallback = meta?.latest_source?.includes('SAR');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }} className="theme-transition">

      {/* Row 1: Event selector + Geocoder */}
      <div style={{ display: 'flex', gap: '10px', flexDirection: isMobile ? 'column' : 'row', alignItems: isMobile ? 'stretch' : 'center' }}>

        {/* Event quick-select */}
        <select
          value={selectedEvent}
          onChange={onFeaturedEventChange}
          style={{
            ...inputStyle,
            padding: '0 14px',
            width: isMobile ? '100%' : '30%',
            cursor: 'pointer',
            flexShrink: 0,
          }}
          onFocus={onFocusStyle}
          onBlur={onBlurStyle}
        >
          {FEATURED_EVENTS.map((ev, i) => (
            <option key={i} value={ev.value}>{ev.label}</option>
          ))}
        </select>

        {/* Geocoder */}
        <form onSubmit={onSearchSubmit} style={{ flex: 1, position: 'relative', width: '100%' }}>
          <input
            style={{ ...inputStyle, width: '100%', padding: '0 16px', boxSizing: 'border-box' }}
            placeholder="Search custom location..."
            value={searchQuery}
            onChange={onInputChange}
            onFocus={(e) => { onFocusStyle(e); onFocus(); }}
            onBlur={(e)  => { onBlurStyle(e);  onBlur();  }}
          />

          {/* Autocomplete dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0,
              backgroundColor: 'var(--input-bg)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px', zIndex: 3000, overflow: 'hidden',
              boxShadow: '0 10px 30px var(--shadow-color)',
              animation: 'slideDown 0.15s ease',
            }}>
              {suggestions.map((s, i) => (
                <div
                  key={i}
                  onMouseDown={() => onSuggestionSelect(s)}
                  style={{
                    padding: '11px 16px', color: 'var(--text-main)', cursor: 'pointer',
                    borderBottom: i < suggestions.length - 1 ? '1px solid var(--border-color)' : 'none',
                    fontSize: '14px', transition: 'background 0.1s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  {s.display_name}
                </div>
              ))}
            </div>
          )}
        </form>
      </div>

      {/* Row 2: Date + Analyse button */}
      <div style={{ display: 'flex', gap: '10px', flexDirection: isMobile ? 'column' : 'row', alignItems: isMobile ? 'stretch' : 'center', justifyContent: 'space-between' }}>

        {/* Date picker */}
        <div style={{
          ...inputStyle,
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '0 14px',
          width: isMobile ? '100%' : '30%',
          boxSizing: 'border-box', flexShrink: 0,
        }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '13px', whiteSpace: 'nowrap' }}>Event Date:</span>
          <input
            type="date"
            value={targetDate}
            onChange={onDateChange}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-main)', fontSize: '14px', outline: 'none', cursor: 'pointer', flex: 1, fontFamily: 'inherit' }}
          />
        </div>

        {/* Analyse button */}
        <button
          onClick={onDetect}
          disabled={isProcessing}
          style={{
            backgroundColor: 'var(--accent)',
            color: 'var(--button-text)',
            border: 'none',
            padding: '0 28px',
            borderRadius: '8px',
            fontSize: '15px',
            fontWeight: '600',
            cursor: isProcessing ? 'not-allowed' : 'pointer',
            height: '50px',
            width: isMobile ? '100%' : 'auto',
            opacity: isProcessing ? 0.65 : 1,
            flexShrink: 0,
            transition: 'opacity 0.2s, transform 0.15s, box-shadow 0.15s',
            fontFamily: 'inherit',
          }}
          onMouseEnter={(e) => { if (!isProcessing) { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 4px 16px var(--accent-glow)'; } }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none'; }}
        >
          {isProcessing ? 'Processing...' : 'Analyse Area'}
        </button>
      </div>

      {/* Error banner */}
      {errorMsg && (
        <div style={{
          color: '#ff7b72',
          backgroundColor: 'rgba(255,123,114,0.08)',
          padding: '10px 14px', borderRadius: '8px',
          border: '1px solid rgba(255,123,114,0.3)',
          fontSize: '14px', lineHeight: '1.5',
          animation: 'fadeIn 0.2s ease',
        }}>
          {errorMsg}
        </div>
      )}

      {/* SAR fallback notice */}
      {isSARFallback && (
        <div style={{
          backgroundColor: 'rgba(210,153,34,0.08)',
          border: '1px solid rgba(210,153,34,0.3)',
          borderRadius: '8px', padding: '12px 14px',
          display: 'flex', gap: '12px', alignItems: 'flex-start',
          animation: 'fadeIn 0.2s ease',
        }}>
          <div style={{ width: '3px', borderRadius: '2px', backgroundColor: '#d29922', alignSelf: 'stretch', flexShrink: 0 }} />
          <div>
            <div style={{ color: '#d29922', fontSize: '13px', fontWeight: '600', marginBottom: '3px' }}>
              Radar imagery in use — cloud cover detected
            </div>
            <div style={{ color: 'var(--text-main)', fontSize: '13px', lineHeight: '1.5' }}>
              Optical sensors were obstructed. Results are based on Sentinel-1 Radar (SAR) data. Spatial detail may be reduced due to radar noise.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ControlPanel;
