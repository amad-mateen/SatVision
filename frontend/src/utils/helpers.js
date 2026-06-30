// ─────────────────────────────────────────────────────────────────
// SATVision — Asset URL Helpers
// ─────────────────────────────────────────────────────────────────
import { BACKEND_URL } from '../constants/events';

/**
 * Strips any origin from a backend-generated URL and rebuilds it
 * against the canonical public `BACKEND_URL`.
 *
 * Background: The HuggingFace inference server occasionally returns
 * download URLs containing its internal private IP instead of the
 * public Space hostname. This function normalises all such URLs so
 * that the browser fetches from the correct, publicly-accessible
 * endpoint regardless of what the server returned.
 *
 * @param {string | null | undefined} url - The raw URL received from the backend.
 * @returns {string} A safe, publicly-resolvable download URL, or "#" if
 *                   the input is falsy.
 *
 * @example
 * getSafeDownloadUrl('http://10.0.0.5/mask/report_2022-09-10.pdf')
 * // → 'https://satvision-app.hf.space/mask/report_2022-09-10.pdf'
 */
export const getSafeDownloadUrl = (url) => {
  if (!url) return '#';
  const parts = url.split('/');
  const filename = parts[parts.length - 1];
  return `${BACKEND_URL}/mask/${filename}`;
};

/**
 * Cleans status log messages: strips technical jargon/emojis and translates
 * them into simpler, professional status statements.
 *
 * @param {string} log - Raw log message from backend.
 * @returns {string} Simplified, reader-friendly status log.
 */
export const simplifyStatusLog = (log) => {
  if (!log) return '';

  // Strip emojis and other non-standard unicode characters
  let clean = log.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2700}-\u{27BF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{2600}-\u{26FF}]|[\u{1F1E6}-\u{1F1FF}]/gu, '');
  // Strip common symbols like brain, gear, satellite, wave, warning
  clean = clean.replace(/[🧠📡⚙️🌊⚠️🛰️📁🗓️≡✕👁️⌕▾]/g, '').trim();

  const lower = clean.toLowerCase();
  
  if (lower.includes('optical clear') || lower.includes('cloud cover')) {
    return 'Clear skies. Initializing assessment.';
  }
  if (lower.includes('launching inference') || lower.includes('inference')) {
    return 'Processing satellite imagery.';
  }
  if (lower.includes('downloading') || lower.includes('sentinel')) {
    return 'Retrieving satellite files.';
  }
  if (lower.includes('water index') || lower.includes('calculation') || lower.includes('ndwi')) {
    return 'Analyzing surface water.';
  }
  if (lower.includes('extracting flood') || lower.includes('flood detection')) {
    return 'Calculating flood extent.';
  }
  if (lower.includes('pdf report') || lower.includes('generating report')) {
    return 'Compiling analysis report.';
  }
  if (lower.includes('connecting to') || lower.includes('server')) {
    return 'Connecting to server.';
  }

  // Fallback: trim to max 6 words
  const words = clean.split(/\s+/);
  if (words.length > 6) {
    return words.slice(0, 5).join(' ') + '...';
  }
  
  if (clean.length > 0) {
    clean = clean.charAt(0).toUpperCase() + clean.slice(1);
  }
  return clean;
};


