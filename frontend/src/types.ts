import type { CanvasActionBatch, CanvasState, CanvasVisualContext } from './ai/canvasProtocol'

export type ComponentType =
  | 'metric'
  | 'chart'
  | 'table'
  | 'button'
  | 'input'
  | 'list'
  | 'kanban'
  | 'timeline'
  | 'workflow'
  | 'note'

export interface SpatialShape {
  id: string
  type: string
  x: number
  y: number
  w: number
  h: number
  text?: string
  geo?: string
  color?: string
}

export interface GeneratedComponent {
  id: string
  type: ComponentType
  title: string
  label?: string
  value?: string
  detail?: string
  items?: string[]
  columns?: string[]
  rows?: Array<Record<string, string | number>>
  accent?: string
}

export interface GeneratedUI {
  id: string
  app_type: string
  title: string
  summary: string
  theme: 'light' | 'dark'
  layout: 'dashboard' | 'app' | 'workflow' | 'wireframe'
  generated_at: string
  source: 'backend' | 'local'
  components: GeneratedComponent[]
}

export type EmbeddedCanvasObjectKind = 'image' | 'pdf' | 'file' | 'webpage'

export interface EmbeddedCanvasObject {
  id: string
  kind: EmbeddedCanvasObjectKind
  x: number
  y: number
  w: number
  h: number
  title: string
  mimeType?: string
  size?: number
  dataUrl?: string
  url?: string
  createdAt: string
  metadata?: Record<string, unknown>
}

export interface GenerationRequest {
  shapes: SpatialShape[]
  canvasState?: CanvasState
  visualContext?: CanvasVisualContext
  prompt?: string
  selectedOnly?: boolean
  projectId?: string
}

export interface ProjectBuildInfo {
  projectId: string
  url?: string | null
  status: 'created' | 'updated' | 'failed'
  activity: string[]
  error?: string | null
}

export interface GenerationResponse {
  actionBatch: CanvasActionBatch
  generatedUI?: GeneratedUI | null
  source: 'ai-core'
  project?: ProjectBuildInfo | null
}
