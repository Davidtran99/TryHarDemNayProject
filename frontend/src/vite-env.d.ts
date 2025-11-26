/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_LEGAL_UPLOAD_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}




















