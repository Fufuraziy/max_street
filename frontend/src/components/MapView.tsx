import { useEffect } from 'react';
import L from 'leaflet';
import { MapContainer, Marker, TileLayer, ZoomControl, useMap, useMapEvents } from 'react-leaflet';
import { SPB_CENTER, SPORTS, TILE_URL } from '../lib/constants';
import { hexToRgba } from '../lib/format';
import type { Court, SportType } from '../types';

interface MapViewProps {
  courts: Court[];
  selectedId: number | null;
  activeSport: SportType | null;
  userLocation: [number, number] | null;
  onSelect: (courtId: number) => void;
  onMapReady: (map: L.Map) => void;
  onMapClick: () => void;
}

const iconCache = new Map<string, L.DivIcon>();

/** Маркер-«капля» цвета вида спорта; бейдж — число сборов сегодня, «+N» — другие виды спорта. */
function courtIcon(court: Court, activeSport: SportType | null, selected: boolean): L.DivIcon {
  const sport = activeSport && court.sport_types.includes(activeSport) ? activeSport : court.sport_types[0];
  const meta = SPORTS[sport] ?? SPORTS.basketball;
  const extra = court.sport_types.length - 1;
  const games = court.active_games_today;
  const rental = court.is_commercial;
  const key = `${sport}|${extra}|${games}|${selected ? 1 : 0}|${rental ? 1 : 0}`;

  let icon = iconCache.get(key);
  if (!icon) {
    icon = L.divIcon({
      className: 'court-pin-wrapper',
      html: `<div class="court-pin${selected ? ' is-selected' : ''}${rental ? ' is-rental' : ''}" style="--pin:${meta.color};--pin-ring:${hexToRgba(meta.color, 0.35)}">
        <div class="court-pin__body"><span class="court-pin__emoji">${meta.emoji}</span></div>
        ${games > 0 ? `<span class="court-pin__badge">${games}</span>` : ''}
        ${extra > 0 ? `<span class="court-pin__extra">+${extra}</span>` : ''}
        ${rental ? '<span class="court-pin__rent" title="Аренда">₽</span>' : ''}
      </div>`,
      iconSize: [44, 52],
      iconAnchor: [22, 48],
    });
    iconCache.set(key, icon);
  }
  return icon;
}

const userIcon = L.divIcon({
  className: 'user-dot-wrapper',
  html: '<div class="user-dot"><span></span></div>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

function MapEvents({ onMapReady, onMapClick }: Pick<MapViewProps, 'onMapReady' | 'onMapClick'>) {
  const map = useMap();
  useEffect(() => {
    onMapReady(map);
  }, [map, onMapReady]);
  useMapEvents({ click: () => onMapClick() });
  return null;
}

export default function MapView({
  courts,
  selectedId,
  activeSport,
  userLocation,
  onSelect,
  onMapReady,
  onMapClick,
}: MapViewProps) {
  return (
    <MapContainer
      center={SPB_CENTER}
      zoom={12}
      minZoom={9}
      maxZoom={19}
      zoomControl={false}
      className="absolute inset-0 z-0 h-full w-full"
    >
      <TileLayer
        url={TILE_URL}
        subdomains={['a', 'b', 'c']}
        maxZoom={19}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>'
      />
      <ZoomControl position="bottomright" />
      <MapEvents onMapReady={onMapReady} onMapClick={onMapClick} />
      {courts.map((court) => (
        <Marker
          key={court.id}
          position={[court.latitude, court.longitude]}
          icon={courtIcon(court, activeSport, court.id === selectedId)}
          zIndexOffset={court.id === selectedId ? 1000 : court.active_games_today * 10}
          title={court.title}
          alt={court.title}
          eventHandlers={{ click: () => onSelect(court.id) }}
        />
      ))}
      {userLocation && <Marker position={userLocation} icon={userIcon} interactive={false} zIndexOffset={-100} />}
    </MapContainer>
  );
}
