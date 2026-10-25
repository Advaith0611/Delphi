import type { EmbeddedCanvasObject } from '../types'

// Kept as "tldraw" on the wire for compatibility with the existing backend
// protocol. The frontend renderer is now Excalidraw.
export type CanvasObjectSource = 'tldraw' | 'embedded'

export type CanvasObjectKind =
  | 'shape'
  | 'rectangle'
  | 'circle'
  | 'arrow'
  | 'line'
  | 'polygon'
  | 'freehand'
  | 'text'
  | 'group'
  | 'image'
  | 'pdf'
  | 'markdown'
  | 'file'
  | 'webpage'

export interface CanvasBounds {
  x: number
  y: number
  w: number
  h: number
}

export interface CanvasStyle {
  color?: string
  fill?: string
  stroke?: string
  strokeWidth?: number
  opacity?: number
  dash?: string
  font?: string
  fontSize?: number
}

export interface CanvasRelationship {
  type: 'parent' | 'child' | 'group' | 'binding' | 'embed'
  objectId: string
}

export interface CanvasObjectSnapshot {
  id: string
  source: CanvasObjectSource
  kind: CanvasObjectKind
  type: string
  bounds: CanvasBounds
  rotation?: number
  layerIndex: number
  parentId?: string
  groupId?: string
  text?: string
  url?: string
  mimeType?: string
  size?: number
  title?: string
  style: CanvasStyle
  relationships: CanvasRelationship[]
  metadata: Record<string, unknown>
  raw: unknown
}

export interface SceneGraphNode {
  id: string
  source: CanvasObjectSource
  kind: CanvasObjectKind
  parentId?: string
  children: SceneGraphNode[]
  bounds: CanvasBounds
  layerIndex: number
  relationships: CanvasRelationship[]
}

export interface SceneGraph {
  nodes: SceneGraphNode[]
  flat: SceneGraphNode[]
}

export interface CanvasState {
  schemaVersion: 'pythios.canvas.v1'
  capturedAt: string
  viewport: {
    x: number
    y: number
    z: number
    screenBounds: CanvasBounds
  }
  objects: CanvasObjectSnapshot[]
  selectedObjectIds: string[]
  visibleObjectIds: string[]
  sceneGraph: SceneGraph
  embeddedObjects: EmbeddedCanvasObject[]
  metadata: Record<string, unknown>
}

export interface CanvasVisualContext {
  schemaVersion: 'pythios.canvas.visual.v1'
  capturedAt: string
  format: 'image/png'
  dataUrl: string
  width: number
  height: number
  viewportPageBounds: CanvasBounds
  notes: string[]
}

export type CanvasCreateAction =
  | {
      action: 'create_rectangle' | 'create_circle'
      id?: string
      x: number
      y: number
      width: number
      height: number
      fill?: string
      color?: string
      text?: string
      metadata?: Record<string, unknown>
    }
  | {
      action: 'create_text'
      id?: string
      x: number
      y: number
      width?: number
      text: string
      color?: string
      metadata?: Record<string, unknown>
    }
  | {
      action: 'create_arrow' | 'create_line'
      id?: string
      x: number
      y: number
      endX: number
      endY: number
      color?: string
      text?: string
      metadata?: Record<string, unknown>
    }
  | {
      action: 'create_polygon' | 'create_freehand'
      id?: string
      points: Array<{ x: number; y: number }>
      color?: string
      fill?: string
      strokeWidth?: number
      metadata?: Record<string, unknown>
    }
  | {
      action: 'create_file' | 'create_image' | 'create_pdf' | 'create_markdown'
      id?: string
      x: number
      y: number
      width: number
      height: number
      title: string
      mimeType?: string
      size?: number
      dataUrl?: string
      metadata?: Record<string, unknown>
    }
  | {
      action: 'create_webpage'
      id?: string
      url: string
      x: number
      y: number
      width: number
      height: number
      title?: string
      metadata?: Record<string, unknown>
    }

export type CanvasUpdateAction =
  | {
      action: 'move_object'
      id: string
      x: number
      y: number
    }
  | {
      action: 'resize_object'
      id: string
      width: number
      height: number
    }
  | {
      action: 'update_style'
      id: string
      style: CanvasStyle
    }
  | {
      action: 'relabel_object'
      id: string
      text: string
    }
  | {
      action: 'update_webpage'
      id: string
      url: string
      title?: string
    }
  | {
      action: 'update_metadata'
      id: string
      metadata: Record<string, unknown>
    }

export type CanvasStructuralAction =
  | {
      action: 'delete_object' | 'duplicate_object' | 'bring_to_front' | 'send_to_back'
      id: string
    }
  | {
      action: 'group_objects'
      ids: string[]
      id?: string
    }
  | {
      action: 'ungroup_objects'
      ids: string[]
    }
  | {
      action: 'select_objects'
      ids: string[]
    }

export type CanvasAction = CanvasCreateAction | CanvasUpdateAction | CanvasStructuralAction

export interface CanvasActionResult {
  action: CanvasAction['action']
  ok: boolean
  objectIds: string[]
  error?: string
}

export interface CanvasActionBatch {
  schemaVersion: 'pythios.canvas.actions.v1'
  actions: CanvasAction[]
}

export interface CanvasActionBatchResult {
  schemaVersion: 'pythios.canvas.actions.v1'
  appliedAt: string
  results: CanvasActionResult[]
}
