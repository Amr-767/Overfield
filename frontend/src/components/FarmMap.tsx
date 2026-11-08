import L from 'leaflet'
// Side-effect import: registers Geoman controls and augments the Leaflet types.
import '@geoman-io/leaflet-geoman-free'
import { useEffect, useMemo, useRef } from 'react'
import { MapContainer, Marker, TileLayer, useMap } from 'react-leaflet'

import type { BoundaryGeometry, PointGeometry } from '../api/types'
import {
  DEFAULT_CENTER,
  DEFAULT_TILE_ATTRIBUTION,
  DEFAULT_TILE_URL,
  DEFAULT_ZOOM,
} from '../lib/mapConfig'

export type MapMode = 'draw' | 'point' | 'readonly'

interface FarmMapProps {
  mode: MapMode
  center?: [number, number]
  zoom?: number
  boundary?: BoundaryGeometry | null
  marker?: PointGeometry | null
  onBoundaryChange?: (boundary: BoundaryGeometry | null) => void
  onMarkerChange?: (marker: PointGeometry) => void
  className?: string
  /** Increment to clear the drawn polygon layer. */
  clearSignal?: number
}

const markerIcon = L.divIcon({
  className: 'farm-marker',
  html: '<span class="farm-marker-dot"></span>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
})

const polygonStyle: L.PathOptions = {
  color: '#2f6b3a',
  weight: 3,
  fillColor: '#2f6b3a',
  fillOpacity: 0.16,
}

function toBoundaryGeometry(geometry: GeoJSON.Geometry | null | undefined): BoundaryGeometry | null {
  if (!geometry) return null
  if (geometry.type === 'Polygon' || geometry.type === 'MultiPolygon') {
    return geometry as BoundaryGeometry
  }
  return null
}

function MapController({
  mode,
  boundary,
  marker,
  onBoundaryChange,
  onMarkerChange,
  clearSignal,
}: Pick<
  FarmMapProps,
  'mode' | 'boundary' | 'marker' | 'onBoundaryChange' | 'onMarkerChange' | 'clearSignal'
>) {
  const map = useMap()
  const groupRef = useRef<L.FeatureGroup | null>(null)
  const callbacks = useRef({ onBoundaryChange, onMarkerChange })
  const drawnSignatureRef = useRef<string>('')

  useEffect(() => {
    callbacks.current = { onBoundaryChange, onMarkerChange }
  }, [onBoundaryChange, onMarkerChange])

  // Group + Geoman event wiring (draw, edit, remove → GeoJSON callback).
  useEffect(() => {
    const group = L.featureGroup().addTo(map)
    groupRef.current = group

    const emitBoundary = () => {
      const layers = group.getLayers()
      if (layers.length === 0) {
        drawnSignatureRef.current = ''
        callbacks.current.onBoundaryChange?.(null)
        return
      }
      const layer = layers[0] as L.Polygon
      const feature = layer.toGeoJSON() as GeoJSON.Feature
      const geometry = toBoundaryGeometry(feature.geometry)
      if (geometry) {
        drawnSignatureRef.current = JSON.stringify(geometry)
        callbacks.current.onBoundaryChange?.(geometry)
      }
    }

    const handleCreate = (event: L.LeafletEvent) => {
      const created = (event as unknown as { layer: L.Layer }).layer
      group.clearLayers()
      group.addLayer(created)
      if (created instanceof L.Polygon) {
        created.setStyle(polygonStyle)
      }
      emitBoundary()
    }

    map.on('pm:create', handleCreate)
    map.on('pm:remove', emitBoundary)
    map.on('pm:update', emitBoundary)
    map.on('pm:edit', emitBoundary)
    map.on('pm:markerdragend', emitBoundary)

    return () => {
      map.off('pm:create', handleCreate)
      map.off('pm:remove', emitBoundary)
      map.off('pm:update', emitBoundary)
      map.off('pm:edit', emitBoundary)
      map.off('pm:markerdragend', emitBoundary)
      group.remove()
      groupRef.current = null
    }
  }, [map])

  // Geoman toolbar availability depends on the step.
  useEffect(() => {
    if (mode !== 'draw') {
      map.pm.removeControls()
      return
    }

    map.pm.addControls({
      position: 'topleft',
      drawMarker: false,
      drawPolygon: true,
      drawRectangle: false,
      drawCircle: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawText: false,
      editMode: true,
      dragMode: false,
      cutPolygon: false,
      removalMode: true,
      rotateMode: false,
    })
    map.pm.setPathOptions(polygonStyle)
    map.pm.setGlobalOptions({ allowSelfIntersection: false, limitMarkersToCount: -1 })

    return () => {
      map.pm.removeControls()
    }
  }, [map, mode])

  // Point fallback: a map click sets the farm location.
  useEffect(() => {
    if (mode !== 'point') return
    const handleClick = (event: L.LeafletMouseEvent) => {
      callbacks.current.onMarkerChange?.({
        type: 'Point',
        coordinates: [event.latlng.lng, event.latlng.lat],
      })
    }
    map.on('click', handleClick)
    return () => {
      map.off('click', handleClick)
    }
  }, [map, mode])

  // Explicit clear from the step UI.
  useEffect(() => {
    if (!clearSignal) return
    groupRef.current?.clearLayers()
    drawnSignatureRef.current = ''
  }, [clearSignal])

  // Render an existing boundary (draft restore, review, or saved farm).
  const boundarySignature = boundary ? JSON.stringify(boundary) : ''
  useEffect(() => {
    const group = groupRef.current
    if (!group) return

    if (!boundary) return
    if (boundarySignature === drawnSignatureRef.current) return

    group.clearLayers()
    const layer = L.geoJSON(boundary, { style: polygonStyle })
    layer.eachLayer((child) => group.addLayer(child))
    drawnSignatureRef.current = boundarySignature

    try {
      const bounds = group.getBounds()
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [28, 28], maxZoom: 17 })
      }
    } catch {
      // Ignore fit errors on degenerate geometry.
    }
  }, [boundarySignature, boundary, map])

  // Keep the marker in view when a point is chosen (geolocation or click).
  useEffect(() => {
    if (!marker) return
    const [lon, lat] = marker.coordinates
    map.panTo([lat, lon], { animate: true })
  }, [marker, map])

  return null
}

export function FarmMap({
  mode,
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
  boundary,
  marker,
  onBoundaryChange,
  onMarkerChange,
  className,
  clearSignal,
}: FarmMapProps) {
  const tileUrl = import.meta.env.VITE_TILE_URL?.trim() || DEFAULT_TILE_URL
  const attribution = import.meta.env.VITE_TILE_ATTRIBUTION?.trim() || DEFAULT_TILE_ATTRIBUTION

  const markerPosition = useMemo<[number, number] | null>(() => {
    if (!marker) return null
    const [lon, lat] = marker.coordinates
    return [lat, lon]
  }, [marker])

  return (
    <div className={`farm-map ${className ?? ''}`.trim()}>
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom
        className="farm-map-canvas"
        attributionControl
      >
        <TileLayer url={tileUrl} attribution={attribution} maxZoom={19} />
        {markerPosition ? <Marker position={markerPosition} icon={markerIcon} /> : null}
        <MapController
          mode={mode}
          boundary={boundary}
          marker={marker}
          onBoundaryChange={onBoundaryChange}
          onMarkerChange={onMarkerChange}
          clearSignal={clearSignal}
        />
      </MapContainer>
      <p className="farm-map-hint">
        {mode === 'draw'
          ? 'Use the polygon tool to trace your field. You can move the corners afterwards.'
          : mode === 'point'
            ? 'Tap the map to place your farm location.'
            : 'Farm boundary as saved in AgroSpace Quest.'}
      </p>
    </div>
  )
}
