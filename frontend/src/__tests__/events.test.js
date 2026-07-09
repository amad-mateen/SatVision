import { DEFAULT_ZOOM, FEATURED_EVENTS } from '../constants/events';

describe('events constants configuration tests', () => {
  test('DEFAULT_ZOOM is defined and within logical bounds', () => {
    expect(DEFAULT_ZOOM).toBeDefined();
    expect(typeof DEFAULT_ZOOM).toBe('number');
    expect(DEFAULT_ZOOM).toBeGreaterThanOrEqual(1);
    expect(DEFAULT_ZOOM).toBeLessThanOrEqual(20);
  });

  test('FEATURED_EVENTS contains valid structured preset anchors', () => {
    expect(Array.isArray(FEATURED_EVENTS)).toBe(true);
    expect(FEATURED_EVENTS.length).toBeGreaterThan(0);
    
    const customEvent = FEATURED_EVENTS.find(e => e.value === 'custom');
    expect(customEvent).toBeDefined();
    expect(customEvent.label).toContain('Custom');

    FEATURED_EVENTS.forEach(event => {
      expect(event.label).toBeDefined();
      expect(event.value).toBeDefined();
      if (event.value !== 'custom') {
        expect(event.lat).toBeDefined();
        expect(event.lon).toBeDefined();
        expect(event.date).toBeDefined();
        expect(typeof event.lat).toBe('number');
        expect(typeof event.lon).toBe('number');
        expect(typeof event.date).toBe('string');
      }
    });
  });
});
