import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';

import { FEATURED_EVENTS, BACKEND_URL, DEFAULT_ZOOM } from './constants/events';
import { simplifyStatusLog } from './utils/helpers';
import ImageModal from './components/ImageModal';
import Sidebar from './components/Sidebar';
import ControlPanel from './components/ControlPanel';
import MapExplorer from './components/MapExplorer';

/* ─── Minimal global styles ──────────────────────────────────────── */
const GLOBAL_STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg-app: #06090e;
    --bg-navbar: rgba(22, 27, 34, 0.75);
    --bg-sidebar: rgba(22, 27, 34, 0.6);
    --bg-panel: rgba(22, 27, 34, 0.85);
    --bg-card: #161b22;
    --bg-card-hover: #21262d;
    --border-color: rgba(48, 54, 61, 0.6);
    --border-hover: #20b2aa;
    --text-main: #e6edf3;
    --text-muted: #8b949e;
    --accent: #20b2aa;
    --accent-glow: rgba(32, 178, 170, 0.15);
    --button-text: #0d1117;
    --glass-blur: blur(12px);
    --texture-opacity: 0.08;
    --input-bg: #161b22;
    --shadow-color: rgba(0, 0, 0, 0.6);
    --backdrop-bg: rgba(13, 17, 23, 0.88);
    --noise-texture: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.035'/%3E%3C/svg%3E");
  }

  [data-theme="light"] {
    --bg-app: #f4f6f8;
    --bg-navbar: rgba(255, 255, 255, 0.8);
    --bg-sidebar: rgba(246, 248, 250, 0.8);
    --bg-panel: rgba(255, 255, 255, 0.85);
    --bg-card: #ffffff;
    --bg-card-hover: #f0f3f6;
    --border-color: rgba(208, 215, 222, 0.7);
    --border-hover: #008080;
    --text-main: #24292f;
    --text-muted: #57606a;
    --accent: #008080;
    --accent-glow: rgba(0, 128, 128, 0.12);
    --button-text: #ffffff;
    --glass-blur: blur(12px);
    --texture-opacity: 0.04;
    --input-bg: #ffffff;
    --shadow-color: rgba(0, 0, 0, 0.08);
    --backdrop-bg: rgba(255, 255, 255, 0.8);
    --noise-texture: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.015'/%3E%3C/svg%3E");
  }

  body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    background: var(--bg-app);
    color: var(--text-main);
    -webkit-font-smoothing: antialiased;
    transition: background-color 0.3s, color 0.3s;
  }

  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: var(--bg-app); }
  ::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--accent); }

  input[type="date"]::-webkit-calendar-picker-indicator {
    filter: invert(0.5) sepia(0.5);
    cursor: pointer;
    opacity: 0.7;
  }
  input[type="date"]::-webkit-calendar-picker-indicator:hover { opacity: 1; }

  select option { background: var(--bg-card); color: var(--text-main); }

  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-6px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes spin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }

  .textured-overlay {
    position: relative;
    background-image: var(--noise-texture);
  }
  .textured-overlay::before {
    content: "";
    position: absolute;
    inset: 0;
    background-size: 18px 18px;
    background-image: 
      linear-gradient(to right, var(--border-color) 0.5px, transparent 0.5px),
      linear-gradient(to bottom, var(--border-color) 0.5px, transparent 0.5px);
    opacity: var(--texture-opacity);
    pointer-events: none;
    z-index: 0;
  }

  .theme-transition {
    transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease, box-shadow 0.3s ease;
  }
`;

const App = () => {
  /* ── Theme State ────────────────────────────────────────────────── */
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('satvision-theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('satvision-theme', theme);
  }, [theme]);

  /* ── State ─────────────────────────────────────────────────────── */
  const [mapBounds, setMapBounds]             = useState(null);
  const [targetLocation, setTargetLocation]   = useState(null);
  const [mapZoom, setMapZoom]                 = useState(DEFAULT_ZOOM);
  const [overlayBounds, setOverlayBounds]     = useState(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress]         = useState(0);
  const [statusLog, setStatusLog]       = useState('');
  const [errorMsg, setErrorMsg]         = useState(null);

  const [searchQuery, setSearchQuery]       = useState('');
  const [targetDate, setTargetDate]         = useState(new Date().toISOString().split('T')[0]);
  const [selectedEvent, setSelectedEvent]   = useState('custom');
  const [suggestions, setSuggestions]       = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchTimeoutRef = useRef(null);

  const [layers, setLayers] = useState({ latest: null, previous: null, flood: null });
  const [meta, setMeta]     = useState({});
  const [history, setHistory]                     = useState([]);
  const [expandedHistoryId, setExpandedHistoryId] = useState(null);

  const [showCurrentWater, setShowCurrentWater]   = useState(true);
  const [showHistoricWater, setShowHistoricWater] = useState(true);
  const [showFlood, setShowFlood]                 = useState(true);
  const [showActualImage, setShowActualImage]     = useState(true);

  const [modalData, setModalData] = useState(null);

  const [isMobile, setIsMobile]     = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [layerControlCollapsed, setLayerControlCollapsed] = useState(false);

  const [panelOffset, setPanelOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging]   = useState(false);
  const dragInfo = useRef({ startX: 0, startY: 0, isDragging: false });

  // Implicitly enable tidal buffer analysis behind the scenes
  const useTidalBuffer = true;

  /* ── Responsive ────────────────────────────────────────────────── */
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      setSidebarOpen(!mobile);
      if (mobile) setLayerControlCollapsed(true);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  /* ── Drag ──────────────────────────────────────────────────────── */
  const handlePointerDown = (e) => {
    dragInfo.current = { isDragging: true, startX: e.clientX - panelOffset.x, startY: e.clientY - panelOffset.y };
    setIsDragging(true);
    e.target.setPointerCapture(e.pointerId);
  };
  const handlePointerMove = (e) => {
    if (!dragInfo.current.isDragging) return;
    setPanelOffset({ x: e.clientX - dragInfo.current.startX, y: e.clientY - dragInfo.current.startY });
  };
  const handlePointerUp = (e) => {
    dragInfo.current.isDragging = false;
    setIsDragging(false);
    e.target.releasePointerCapture(e.pointerId);
  };

  /* ── Geocoder ──────────────────────────────────────────────────── */
  const fetchSuggestions = async (query) => {
    try {
      const res = await axios.get(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&countrycodes=pk&limit=5`
      );
      setSuggestions(res.data);
      setShowSuggestions(true);
    } catch (err) { console.error('[App] Suggestion fetch failed', err); }
  };

  const handleInputChange = (e) => {
    const val = e.target.value;
    setSearchQuery(val);
    setSelectedEvent('custom');
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    if (val.length > 2) searchTimeoutRef.current = setTimeout(() => fetchSuggestions(val), 500);
    else { setSuggestions([]); setShowSuggestions(false); }
  };

  const handleSuggestionSelect = (s) => {
    setSearchQuery(s.display_name);
    setTargetLocation([parseFloat(s.lat), parseFloat(s.lon)]);
    setMapZoom(DEFAULT_ZOOM);
    setShowSuggestions(false);
    setSuggestions([]);
  };

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery) return;
    try {
      const res = await axios.get(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&countrycodes=pk`
      );
      if (res.data?.[0]) {
        setTargetLocation([parseFloat(res.data[0].lat), parseFloat(res.data[0].lon)]);
        setMapZoom(DEFAULT_ZOOM);
        setShowSuggestions(false);
        setSelectedEvent('custom');
      } else setErrorMsg('Location not found in Pakistan.');
    } catch { setErrorMsg('Search failed. Please try again.'); }
  };

  const handleFeaturedEventChange = (e) => {
    const val = e.target.value;
    setSelectedEvent(val);
    if (val !== 'custom') {
      const ev = FEATURED_EVENTS.find((event) => event.value === val);
      if (ev) { setTargetLocation([ev.lat, ev.lon]); setTargetDate(ev.date); setMapZoom(ev.zoom); setSearchQuery(''); }
    }
  };

  const handleDateChange = (e) => { setTargetDate(e.target.value); setSelectedEvent('custom'); };

  /* ── History ───────────────────────────────────────────────────── */
  const loadHistoryItem = (item) => {
    setTargetLocation(item.targetLocation);
    setMapZoom(item.zoom || DEFAULT_ZOOM);
    setOverlayBounds(item.bounds);
    setLayers(item.layers);
    setMeta(item.meta);
    setExpandedHistoryId(item.id);
    if (isMobile) setSidebarOpen(false);
  };

  /* ── Analysis pipeline ─────────────────────────────────────────── */
  const handleDetectFloods = async () => {
    if (!mapBounds) return setErrorMsg('Please zoom or pan the map to select an area first.');
    setIsProcessing(true); setErrorMsg(null); setProgress(0);
    setStatusLog('Connecting to analysis server...');
    setLayers({ latest: null, previous: null, flood: null }); setMeta({});

    const currentBounds = mapBounds;
    const centerLoc     = [mapBounds.getCenter().lat, mapBounds.getCenter().lng];
    const currentZoom   = mapZoom;
    const controller    = new AbortController();
    const timeoutId     = setTimeout(() => controller.abort(), 180000);
    let finalLayers = null, finalMeta = null;

    try {
      const bbox = { north: currentBounds.getNorth(), south: currentBounds.getSouth(), east: currentBounds.getEast(), west: currentBounds.getWest() };
      const response = await fetch(`${BACKEND_URL}/api/detect_stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bbox, apply_buffer: useTidalBuffer, target_date: targetDate || undefined }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const rawLine of lines) {
          const line = rawLine.trim();
          if (!line) continue;
          try {
            const data = JSON.parse(line);
            if (data.progress !== undefined) setProgress(data.progress);
            if (data.log) setStatusLog(simplifyStatusLog(data.log));
            if (data.error) throw new Error(data.error);
            if (data.result) {
              finalLayers = { latest: data.result.latest, previous: data.result.previous, flood: data.result.flood };
              finalMeta   = { ...data.meta, report: data.report };
              setOverlayBounds(currentBounds);
              setLayers(finalLayers);
              setMeta(finalMeta);
              if (isMobile) setLayerControlCollapsed(false);
            }
          } catch (parseErr) { console.error('[App] Stream parse error:', parseErr); }
        }
      }
      setStatusLog('Analysis complete.');
      if (finalLayers && finalMeta) {
        let locName = searchQuery;
        if (!locName && selectedEvent !== 'custom') {
          const ev = FEATURED_EVENTS.find((e) => e.value === selectedEvent);
          locName = ev ? ev.label : 'Selected Area';
        } else if (!locName) locName = `${centerLoc[0].toFixed(2)}°N, ${centerLoc[1].toFixed(2)}°E`;
        const newItem = { id: Date.now(), name: locName, date: targetDate || new Date().toISOString().split('T')[0], bounds: currentBounds, targetLocation: centerLoc, zoom: currentZoom, layers: finalLayers, meta: finalMeta };
        setHistory((prev) => [newItem, ...prev]);
        setExpandedHistoryId(newItem.id);
      }
    } catch (err) { setErrorMsg(err.name === 'AbortError' ? 'The request timed out. Please try again.' : err.message); }
    finally { clearTimeout(timeoutId); setIsProcessing(false); }
  };

  /* ── Render ────────────────────────────────────────────────────── */
  return (
    <>
      <style>{GLOBAL_STYLES}</style>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'var(--bg-app)', position: 'relative' }} className="theme-transition">

        {/* ── Navbar ── */}
        <div style={{
          height: '58px', flexShrink: 0,
          backgroundColor: 'var(--bg-navbar)',
          backdropFilter: 'var(--glass-blur)',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px', gap: '16px',
        }} className="textured-overlay theme-transition">
          {/* Left: Hamburger menu (mobile) + Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', position: 'relative', zIndex: 2 }}>
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                style={{ background: 'none', border: '1px solid var(--border-color)', color: 'var(--text-muted)', borderRadius: '6px', width: '34px', height: '34px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'border-color 0.2s, color 0.2s' }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.color = 'var(--text-muted)'; }}
              >
                <svg width="18" height="12" viewBox="0 0 18 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M0 1H18M0 6H18M0 11H18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </button>
            )}
            <h2 style={{ margin: 0, color: 'var(--text-main)', fontSize: isMobile ? '17px' : '19px', fontWeight: '600', whiteSpace: 'nowrap' }}>
              SATVision
              {!isMobile && <span style={{ color: 'var(--text-muted)', fontWeight: '400' }}> | Map Explorer</span>}
            </h2>
          </div>

          {/* Right: Theme Toggle */}
          <div style={{ position: 'relative', zIndex: 2 }}>
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              style={{
                background: 'none',
                border: '1px solid var(--border-color)',
                color: 'var(--text-main)',
                borderRadius: '6px',
                padding: '6px 14px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'border-color 0.2s, background-color 0.2s',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-color)'; }}
            >
              {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
            </button>
          </div>
        </div>

        {/* ── Body ── */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
          <Sidebar
            history={history}
            expandedHistoryId={expandedHistoryId}
            isMobile={isMobile}
            sidebarOpen={sidebarOpen}
            onLoad={loadHistoryItem}
            onClose={() => setSidebarOpen(false)}
          />

          <div style={{ flex: 1, padding: isMobile ? '12px' : '18px', display: 'flex', flexDirection: 'column', gap: '14px', backgroundColor: 'var(--bg-app)', position: 'relative', overflow: 'hidden' }} className="theme-transition">
            <ControlPanel
              isMobile={isMobile}
              searchQuery={searchQuery}
              selectedEvent={selectedEvent}
              targetDate={targetDate}
              suggestions={suggestions}
              showSuggestions={showSuggestions}
              isProcessing={isProcessing}
              errorMsg={errorMsg}
              meta={meta}
              onInputChange={handleInputChange}
              onSuggestionSelect={handleSuggestionSelect}
              onSearchSubmit={handleSearch}
              onFeaturedEventChange={handleFeaturedEventChange}
              onDateChange={handleDateChange}
              onDetect={handleDetectFloods}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            />

            <MapExplorer
              overlayBounds={overlayBounds}
              layers={layers}
              meta={meta}
              showCurrentWater={showCurrentWater}
              showHistoricWater={showHistoricWater}
              showFlood={showFlood}
              showActualImage={showActualImage}
              isProcessing={isProcessing}
              progress={progress}
              statusLog={statusLog}
              isMobile={isMobile}
              layerControlCollapsed={layerControlCollapsed}
              panelOffset={panelOffset}
              isDragging={isDragging}
              targetLocation={targetLocation}
              mapZoom={mapZoom}
              onBoundsChange={setMapBounds}
              onLayerCollapse={() => setLayerControlCollapsed(true)}
              onLayerExpand={() => setLayerControlCollapsed(false)}
              onModalOpen={() => setModalData({ url: meta.latest_rgb, date: meta.latest_date, source: meta.latest_source, title: 'Post-Flood Satellite Image' })}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              toggleHandlers={{
                onFlood: (e) => setShowFlood(e.target.checked),
                onCurrentWater: (e) => setShowCurrentWater(e.target.checked),
                onHistoricWater: (e) => setShowHistoricWater(e.target.checked),
                onActualImage: (e) => setShowActualImage(e.target.checked),
              }}
            />
          </div>
        </div>

        {modalData && <ImageModal {...modalData} onClose={() => setModalData(null)} />}
      </div>
    </>
  );
};

export default App;
