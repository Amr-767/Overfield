/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  /** Optional raster tile template; defaults to OpenStreetMap. */
  readonly VITE_TILE_URL?: string
  /** Optional attribution HTML; defaults to the OpenStreetMap attribution. */
  readonly VITE_TILE_ATTRIBUTION?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
