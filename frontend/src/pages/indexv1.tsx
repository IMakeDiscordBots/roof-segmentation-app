import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
// @ts-expect-error: No types available for mapbox-gl-geocoder
import MapboxGeocoder from '@mapbox/mapbox-gl-geocoder';

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN as string;

export default function Home() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (mapRef.current || !mapContainer.current) return;

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/satellite-streets-v12',
      center: [-96.9, 32.8],
      zoom: 4,
    });
    mapRef.current = map;

    map.on('load', () => {});
    const geocoder = new MapboxGeocoder({
      accessToken: mapboxgl.accessToken,
      mapboxgl,
      marker: false,
    });
    map.addControl(geocoder);

    geocoder.on('result', async (e: { result: { bbox?: number[] } }) => {
      const bbox: number[] = e.result.bbox || [];
      if (bbox.length !== 4) return;

      map.fitBounds(bbox as [number, number, number, number], { padding: 40 });

      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/segment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bbox, imgSize: 512 }),
      });
      const geojson = await res.json();

      if (map.getSource('roof')) {
        (map.getSource('roof') as mapboxgl.GeoJSONSource).setData(geojson);
      } else {
        map.addSource('roof', { type: 'geojson', data: geojson });
        map.addLayer({
          id: 'roof-fill',
          type: 'fill',
          source: 'roof',
          paint: {
            'fill-color': '#ff0066',
            'fill-opacity': 0.4,
          },
        });
      }
    });

    // Cleanup on unmount
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return <div ref={mapContainer} className="w-screen h-screen" />;
}