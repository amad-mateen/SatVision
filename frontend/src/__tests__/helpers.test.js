import { getSafeDownloadUrl } from '../utils/helpers';
import { BACKEND_URL } from '../constants/events';

describe('getSafeDownloadUrl helper tests', () => {
  test('returns "#" for null, undefined, or empty URLs', () => {
    expect(getSafeDownloadUrl(null)).toBe('#');
    expect(getSafeDownloadUrl(undefined)).toBe('#');
    expect(getSafeDownloadUrl('')).toBe('#');
  });

  test('rebuilds raw backend URLs correctly against BACKEND_URL', () => {
    const rawUrl = 'http://10.112.30.236:7860/mask/session123/file.png';
    const expectedUrl = `${BACKEND_URL}/mask/file.png`;
    expect(getSafeDownloadUrl(rawUrl)).toBe(expectedUrl);
  });

  test('rebuilds local dev URLs correctly', () => {
    const rawUrl = 'http://localhost:5000/mask/session456/image.jpg';
    const expectedUrl = `${BACKEND_URL}/mask/image.jpg`;
    expect(getSafeDownloadUrl(rawUrl)).toBe(expectedUrl);
  });
});
