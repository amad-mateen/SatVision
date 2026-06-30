import React, { useEffect } from 'react';
import { MapContainer, TileLayer, ImageOverlay, useMap } from 'react-leaflet';
import L from 'leaflet';
import { DEFAULT_ZOOM } from '../constants/events';

/* ─── Leaflet icon fix ───────────────────────────────────────────── */
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl:       require('leaflet/dist/images/marker-icon.png'),
  shadowUrl:     require('leaflet/dist/images/marker-shadow.png'),
});

/* ─── Layer pane z-indexes ───────────────────────────────────────── */
const PANE_CONFIG = [
  { name: 'pane-rgb',      zIndex: 301 }, // L1 — True-color satellite
  { name: 'pane-previous', zIndex: 302 }, // L2 — Permanent water baseline
  { name: 'pane-latest',   zIndex: 303 }, // L3 — Current water mask
  { name: 'pane-flood',    zIndex: 304 }, // L4 — New flood (always on top)
];

/* ─── PaneInitializer ────────────────────────────────────────────── */
const PaneInitializer = () => {
  const map = useMap();
  useEffect(() => {
    PANE_CONFIG.forEach(({ name, zIndex }) => {
      if (!map.getPane(name)) {
        const pane = map.createPane(name);
        pane.style.zIndex = String(zIndex);
        pane.style.pointerEvents = 'none';
      }
    });
  }, [map]);
  return null;
};

/* ─── MapController ──────────────────────────────────────────────── */
const MapController = ({ onBoundsChange }) => {
  const map = useMap();
  useEffect(() => {
    const h = () => onBoundsChange(map.getBounds());
    map.on('moveend', h);
    onBoundsChange(map.getBounds());
    return () => map.off('moveend', h);
  }, [map, onBoundsChange]);
  return null;
};

/* ─── MapFlyTo ───────────────────────────────────────────────────── */
const MapFlyTo = ({ targetLocation, targetZoom }) => {
  const map = useMap();
  useEffect(() => {
    if (targetLocation) map.flyTo(targetLocation, targetZoom || DEFAULT_ZOOM, { animate: true, duration: 1.5 });
  }, [targetLocation, targetZoom, map]);
  return null;
};

/* ─── MapExplorer ────────────────────────────────────────────────── */
const MapExplorer = ({
  overlayBounds, layers, meta, showCurrentWater, showHistoricWater,
  showFlood, showActualImage, isProcessing, progress, statusLog,
  isMobile, layerControlCollapsed, panelOffset, isDragging,
  targetLocation, mapZoom, onBoundsChange, onLayerCollapse, onLayerExpand,
  onModalOpen, onPointerDown, onPointerMove, onPointerUp, toggleHandlers,
}) => {
  const cacheBust = Date.now();
  const showLayerPanel = overlayBounds && !isProcessing && (!isMobile || !layerControlCollapsed);

  return (
    <div style={{ flex: 1, borderRadius: '10px', overflow: 'hidden', border: '1px solid var(--border-color)', position: 'relative' }} className="theme-transition">

      {/* Processing overlay */}
      {isProcessing && <ProcessingOverlay progress={progress} statusLog={statusLog} />}

      {/* Mobile: collapsed layer toggle */}
      {overlayBounds && !isProcessing && isMobile && layerControlCollapsed && (
        <button
          onClick={onLayerExpand}
          style={{
            position: 'absolute', bottom: '20px', right: '12px', zIndex: 1000,
            backgroundColor: 'var(--accent)', color: 'var(--button-text)',
            border: 'none', borderRadius: '50px',
            padding: '10px 18px', fontWeight: '600', fontSize: '13px',
            boxShadow: '0 4px 14px var(--shadow-color)',
            cursor: 'pointer', fontFamily: 'inherit',
            transition: 'background-color 0.3s, color 0.3s, box-shadow 0.3s',
          }}
        >
          Layers
        </button>
      )}

      {/* Layer controls */}
      {showLayerPanel && (
        <LayerControlPanel
          isMobile={isMobile} isDragging={isDragging} panelOffset={panelOffset}
          showFlood={showFlood} showCurrentWater={showCurrentWater}
          showHistoricWater={showHistoricWater} showActualImage={showActualImage}
          meta={meta} onLayerCollapse={onLayerCollapse} onModalOpen={onModalOpen}
          onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp}
          toggleHandlers={toggleHandlers}
        />
      )}

      {/* Leaflet map */}
      <MapContainer
        center={[30.3753, 69.3451]} zoom={DEFAULT_ZOOM}
        minZoom={6} maxZoom={16} zoomSnap={0.5}
        zoomControl={false} scrollWheelZoom={false}
        doubleClickZoom={false} touchZoom={false} dragging={true}
        style={{ width: '100%', height: '100%' }}
      >
        <PaneInitializer />
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution="Esri &amp; Carto"
        />
        <MapController onBoundsChange={onBoundsChange} />
        <MapFlyTo targetLocation={targetLocation} targetZoom={mapZoom} />

        {overlayBounds && (<>
          {showActualImage   && meta.latest_rgb  && <ImageOverlay url={`${meta.latest_rgb}?t=${cacheBust}`}   bounds={overlayBounds} opacity={1.0} pane="pane-rgb"      />}
          {showHistoricWater && layers.previous  && <ImageOverlay url={`${layers.previous}?t=${cacheBust}`}   bounds={overlayBounds} opacity={0.6} pane="pane-previous" />}
          {showCurrentWater  && layers.latest    && <ImageOverlay url={`${layers.latest}?t=${cacheBust}`}     bounds={overlayBounds} opacity={0.6} pane="pane-latest"   />}
          {showFlood         && layers.flood     && <ImageOverlay url={`${layers.flood}?t=${cacheBust}`}      bounds={overlayBounds} opacity={0.8} pane="pane-flood"    />}
        </>)}
      </MapContainer>
    </div>
  );
};

/* ─── Processing overlay ─────────────────────────────────────────── */
const ProcessingOverlay = ({ progress, statusLog }) => (
  <div style={{
    position: 'absolute', inset: 0, zIndex: 2000,
    backgroundColor: 'var(--backdrop-bg)',
    backdropFilter: 'var(--glass-blur)',
    display: 'flex', flexDirection: 'column',
    justifyContent: 'center', alignItems: 'center', gap: '16px',
  }} className="theme-transition">
    {/* Circular spinning loading indicator */}
    <div style={{
      width: '32px', height: '32px',
      border: '3px solid var(--border-color)',
      borderTop: '3px solid var(--accent)',
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
      marginBottom: '4px',
    }} />

    <h3 style={{ color: 'var(--text-main)', fontSize: '17px', fontWeight: '600', margin: 0 }}>
      Analysing Satellite Imagery
    </h3>

    {/* Progress bar */}
    <div style={{ width: '80%', maxWidth: '300px', height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
      <div style={{ width: `${progress}%`, height: '100%', backgroundColor: 'var(--accent)', borderRadius: '3px', transition: 'width 0.35s ease' }} />
    </div>
    <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', maxWidth: '280px', lineHeight: '1.5' }}>
      {statusLog}
    </div>
  </div>
);

/* ─── Layer control panel ────────────────────────────────────────── */
const LayerControlPanel = ({
  isMobile, isDragging, panelOffset, showFlood, showCurrentWater,
  showHistoricWater, showActualImage, meta, onLayerCollapse,
  onModalOpen, onPointerDown, onPointerMove, onPointerUp, toggleHandlers,
}) => (
  <div style={{
    position: 'absolute',
    top: isMobile ? 'auto' : '16px', bottom: isMobile ? '16px' : 'auto',
    right: isMobile ? '12px' : '16px', left: isMobile ? '12px' : 'auto',
    zIndex: 1000,
    backgroundColor: 'var(--bg-panel)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px', overflow: 'hidden',
    boxShadow: '0 8px 24px var(--shadow-color)',
    backdropFilter: 'var(--glass-blur)',
    transform: `translate(${panelOffset.x}px, ${panelOffset.y}px)`,
    minWidth: '220px',
  }} className="theme-transition">
    {/* Drag handle / header */}
    <div
      onPointerDown={onPointerDown} onPointerMove={onPointerMove}
      onPointerUp={onPointerUp} onPointerCancel={onPointerUp}
      style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border-color)',
        cursor: isDragging ? 'grabbing' : 'grab',
        touchAction: 'none', userSelect: 'none',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}
    >
      <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-main)', pointerEvents: 'none' }}>
        Layer Controls
      </span>
      {isMobile && (
        <button onClick={onLayerCollapse} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '15px', lineHeight: 1, padding: 0 }}>
          ✕
        </button>
      )}
    </div>

    {/* Layer toggles */}
    <div style={{ padding: '8px 0' }}>
      <LayerRow
        label="Flood Detection"
        checked={showFlood}
        onChange={toggleHandlers.onFlood}
        color="#ff4d4f"
      />
      <LayerRow
        label="Current Water"
        checked={showCurrentWater}
        onChange={toggleHandlers.onCurrentWater}
        color="#1890ff"
      />
      <LayerRow
        label="Permanent Water"
        checked={showHistoricWater}
        onChange={toggleHandlers.onHistoricWater}
        color="#36cfc9"
      />

      {/* Divider */}
      <div style={{ height: '1px', backgroundColor: 'var(--border-color)', margin: '6px 0' }} />

      {/* Satellite image row with preview button */}
      <div style={{ padding: '7px 14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <input
          type="checkbox"
          checked={showActualImage}
          onChange={toggleHandlers.onActualImage}
          style={{ accentColor: 'var(--accent)', width: '14px', height: '14px', cursor: 'pointer', flexShrink: 0 }}
        />
        <span style={{ fontSize: '13px', color: 'var(--text-main)', flex: 1, userSelect: 'none' }}>
          Satellite Image
        </span>
        <button
          onClick={onModalOpen}
          title="Preview source image"
          style={{
            border: '1px solid var(--border-color)', background: 'none',
            color: 'var(--text-muted)', cursor: 'pointer', borderRadius: '5px',
            padding: '3px 8px', fontSize: '12px',
            transition: 'border-color 0.15s, color 0.15s',
            fontFamily: 'inherit', whiteSpace: 'nowrap',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.color = 'var(--text-muted)'; }}
        >
          Preview
        </button>
      </div>
    </div>
  </div>
);

/* ─── Layer toggle row ───────────────────────────────────────────── */
const LayerRow = ({ label, checked, onChange, color }) => (
  <label style={{
    display: 'flex', alignItems: 'center', gap: '10px',
    padding: '7px 14px', cursor: 'pointer', userSelect: 'none',
    transition: 'background-color 0.1s',
  }}
    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
  >
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      style={{ accentColor: 'var(--accent)', width: '14px', height: '14px', cursor: 'pointer', flexShrink: 0 }}
    />
    <span style={{ width: '11px', height: '11px', backgroundColor: color, borderRadius: '2px', flexShrink: 0, opacity: checked ? 1 : 0.35, transition: 'opacity 0.2s' }} />
    <span style={{ fontSize: '13px', color: checked ? 'var(--text-main)' : 'var(--text-muted)', transition: 'color 0.2s' }}>{label}</span>
  </label>
);

export default MapExplorer;
