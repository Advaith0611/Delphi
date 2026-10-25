import type { CanvasEditor, ExcalidrawElement } from './excalidraw'
import { useAppStore } from '../store/useAppStore'
import type {
  CanvasAction,
  CanvasActionBatchResult,
  CanvasActionResult,
  CanvasObjectKind,
  CanvasObjectSnapshot,
  CanvasRelationship,
  CanvasState,
  SceneGraph,
  SceneGraphNode,
} from '../ai/canvasProtocol'
import type { EmbeddedCanvasObject, EmbeddedCanvasObjectKind } from '../types'

const DEFAULT_EMBEDDED_SIZE = { w: 420, h: 300 }
const colors: Record<string, string> = {
  black: '#1e1e1e', blue: '#1971c2', green: '#2f9e44', grey: '#868e96',
  orange: '#e67700', red: '#e03131', violet: '#7048e8', white: '#ffffff', yellow: '#f08c00',
}

function color(value?: string) { return value ? (colors[value.toLowerCase()] ?? value) : '#1e1e1e' }
function fill(value?: string) { return value && value !== 'none' ? (value.startsWith('#') ? value : '#fff3bf') : 'transparent' }
function elementText(element: ExcalidrawElement) { return (element as ExcalidrawElement & { text?: string }).text }
function metadata(element: ExcalidrawElement) { return ((element as ExcalidrawElement & { customData?: Record<string, unknown> }).customData ?? {}) }

function embeddedKind(kind: EmbeddedCanvasObjectKind, mimeType?: string): CanvasObjectKind {
  return kind === 'file' && mimeType?.includes('markdown') ? 'markdown' : kind
}

function kindFromElement(element: ExcalidrawElement): CanvasObjectKind {
  if (element.type === 'rectangle') return 'rectangle'
  if (element.type === 'ellipse') return 'circle'
  if (element.type === 'freedraw') return 'freehand'
  if (element.type === 'arrow' || element.type === 'line' || element.type === 'text') return element.type
  return element.type === 'image' ? 'image' : 'shape'
}

function relationships(element: ExcalidrawElement): CanvasRelationship[] {
  const groupId = element.groupIds.at(-1)
  return groupId ? [{ type: 'group', objectId: groupId }] : []
}

function buildSceneGraph(objects: CanvasObjectSnapshot[]): SceneGraph {
  const flat: SceneGraphNode[] = objects.map((object) => ({ id: object.id, source: object.source, kind: object.kind, parentId: object.parentId, children: [], bounds: object.bounds, layerIndex: object.layerIndex, relationships: object.relationships }))
  const byId = new Map(flat.map((node) => [node.id, node]))
  const roots: SceneGraphNode[] = []
  flat.forEach((node) => node.parentId && byId.has(node.parentId) ? byId.get(node.parentId)?.children.push(node) : roots.push(node))
  return { nodes: roots, flat }
}

function createEmbeddedObject(action: Extract<CanvasAction, { action: 'create_file' | 'create_image' | 'create_pdf' | 'create_markdown' | 'create_webpage' }>): EmbeddedCanvasObject {
  const id = action.id ?? `embed-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  if (action.action === 'create_webpage') return { id, kind: 'webpage', x: action.x, y: action.y, w: action.width, h: action.height, title: action.title ?? new URL(action.url).hostname.replace(/^www\./, ''), url: action.url, createdAt: new Date().toISOString(), metadata: action.metadata }
  return {
    id, kind: action.action === 'create_image' ? 'image' : action.action === 'create_pdf' ? 'pdf' : 'file',
    x: action.x, y: action.y, w: action.width || DEFAULT_EMBEDDED_SIZE.w, h: action.height || DEFAULT_EMBEDDED_SIZE.h,
    title: action.title, mimeType: action.mimeType, size: action.size, dataUrl: action.dataUrl, createdAt: new Date().toISOString(), metadata: action.metadata,
  }
}

function shapeFromAction(action: CanvasAction): Record<string, unknown> | null {
  if (!action.action.startsWith('create_')) return null
  const id = (action as { id?: string }).id ?? `shape-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const common = { id, strokeColor: color('color' in action ? action.color : undefined), backgroundColor: fill('fill' in action ? action.fill : undefined), customData: 'metadata' in action ? action.metadata ?? {} : {} }
  if (action.action === 'create_rectangle' || action.action === 'create_circle') return { ...common, type: action.action === 'create_circle' ? 'ellipse' : 'rectangle', x: action.x, y: action.y, width: action.width, height: action.height, label: action.text ? { text: action.text } : undefined }
  if (action.action === 'create_text') return { ...common, type: 'text', x: action.x, y: action.y, text: action.text, fontSize: 20, width: action.width }
  if (action.action === 'create_arrow' || action.action === 'create_line') return { ...common, type: action.action === 'create_arrow' ? 'arrow' : 'line', x: action.x, y: action.y, points: [[0, 0], [action.endX - action.x, action.endY - action.y]], label: action.text ? { text: action.text } : undefined }
  if (action.action === 'create_freehand' || action.action === 'create_polygon') {
    const first = action.points[0]
    if (!first) return null
    const points = action.points.map((point) => [point.x - first.x, point.y - first.y])
    if (action.action === 'create_polygon') points.push(points[0])
    return { ...common, type: 'line', x: first.x, y: first.y, points, strokeWidth: action.strokeWidth ?? 2 }
  }
  return null
}

function reorder(editor: CanvasEditor, id: string, front: boolean) {
  const elements = [...editor.getElements()]
  const index = elements.findIndex((element) => element.id === id)
  if (index < 0) return false
  const [element] = elements.splice(index, 1)
  if (front) elements.push(element)
  else elements.unshift(element)
  editor.api.updateScene({ elements })
  return true
}

function applyAction(editor: CanvasEditor, action: CanvasAction): CanvasActionResult {
  const store = useAppStore.getState()
  try {
    const skeleton = shapeFromAction(action)
    if (skeleton) {
      const [element] = editor.createElements([skeleton] as never)
      return { action: action.action, ok: true, objectIds: [element.id] }
    }
    if (action.action.startsWith('create_')) {
      const object = createEmbeddedObject(action as Extract<CanvasAction, { action: 'create_file' | 'create_image' | 'create_pdf' | 'create_markdown' | 'create_webpage' }>)
      store.addEmbeddedObject(object)
      return { action: action.action, ok: true, objectIds: [object.id] }
    }
    const element = editor.getElements().find((item) => item.id === ('id' in action ? action.id : ''))
    const exists = Boolean(element || ('id' in action && store.embeddedObjects.some((object) => object.id === action.id)))
    if (action.action === 'move_object') {
      if (element) editor.updateElements((item) => item.id === action.id ? { ...item, x: action.x, y: action.y } : item)
      else store.updateEmbeddedObject(action.id, { x: action.x, y: action.y })
    } else if (action.action === 'resize_object') {
      if (element) editor.updateElements((item) => item.id === action.id ? { ...item, width: action.width, height: action.height } : item)
      else store.updateEmbeddedObject(action.id, { w: action.width, h: action.height })
    } else if (action.action === 'update_style') {
      if (!element) return { action: action.action, ok: false, objectIds: [action.id], error: 'Object not found' }
      editor.updateElements((item) => item.id === action.id ? { ...item, strokeColor: color(action.style.color ?? action.style.stroke ?? item.strokeColor), backgroundColor: fill(action.style.fill) ?? item.backgroundColor, strokeWidth: action.style.strokeWidth ?? item.strokeWidth, opacity: action.style.opacity ?? item.opacity } : item)
    } else if (action.action === 'relabel_object') {
      if (element && element.type === 'text') editor.updateElements((item) => item.id === action.id ? { ...item, text: action.text } : item)
      else if (!element) store.updateEmbeddedObject(action.id, { title: action.text })
      else return { action: action.action, ok: false, objectIds: [action.id], error: 'Only text elements can be relabelled' }
    } else if (action.action === 'update_webpage') store.updateEmbeddedObject(action.id, { url: action.url, title: action.title })
    else if (action.action === 'update_metadata') {
      if (element) editor.updateElements((item) => item.id === action.id ? { ...item, customData: action.metadata } : item)
      else store.updateEmbeddedObject(action.id, { metadata: action.metadata })
    } else if (action.action === 'delete_object') {
      if (element) editor.removeElements([action.id]); else store.deleteEmbeddedObject(action.id)
    } else if (action.action === 'duplicate_object') {
      if (element) editor.createElements([{ ...element, id: `${element.id}-copy-${Date.now()}`, x: element.x + 32, y: element.y + 32 }] as never)
      else store.duplicateEmbeddedObject(action.id)
    } else if (action.action === 'bring_to_front') reorder(editor, action.id, true)
    else if (action.action === 'send_to_back') reorder(editor, action.id, false)
    else if (action.action === 'group_objects') {
      const groupId = action.id ?? `group-${Date.now()}`
      const ids = new Set(action.ids)
      editor.updateElements((item) => ids.has(item.id) ? { ...item, groupIds: [...item.groupIds, groupId] } : item)
    } else if (action.action === 'ungroup_objects') {
      const ids = new Set(action.ids)
      editor.updateElements((item) => ids.has(item.id) ? { ...item, groupIds: [] } : item)
    } else if (action.action === 'select_objects') {
      editor.select(action.ids.filter((id) => editor.getElements().some((element) => element.id === id)))
      store.setSelectedEmbeddedObjectId(action.ids.find((id) => store.embeddedObjects.some((object) => object.id === id)) ?? null)
    } else return { action: action.action, ok: false, objectIds: [], error: 'Unsupported canvas action' }
    return { action: action.action, ok: exists || action.action === 'select_objects' || action.action.startsWith('group_') || action.action.startsWith('ungroup_'), objectIds: 'id' in action ? (action.id ? [action.id] : []) : action.ids }
  } catch (error) {
    return { action: action.action, ok: false, objectIds: [], error: error instanceof Error ? error.message : String(error) }
  }
}

export function getCanvasState(editor: CanvasEditor): CanvasState {
  const elements = editor.getElements()
  const embeddedObjects = useAppStore.getState().embeddedObjects
  const snapshots: CanvasObjectSnapshot[] = elements.map((element, layerIndex) => ({
    id: element.id, source: 'tldraw', kind: kindFromElement(element), type: element.type,
    bounds: { x: element.x, y: element.y, w: element.width, h: element.height }, rotation: element.angle,
    layerIndex, groupId: element.groupIds.at(-1), text: elementText(element), style: { color: element.strokeColor, fill: element.backgroundColor, stroke: element.strokeColor, strokeWidth: element.strokeWidth, opacity: element.opacity, dash: element.strokeStyle }, relationships: relationships(element), metadata: metadata(element), raw: element,
  }))
  const embedded = embeddedObjects.map((object, index) => ({ id: object.id, source: 'embedded' as const, kind: embeddedKind(object.kind, object.mimeType), type: `embed:${object.kind}`, bounds: { x: object.x, y: object.y, w: object.w, h: object.h }, layerIndex: elements.length + index, text: object.url ?? object.title, url: object.url, mimeType: object.mimeType, size: object.size, title: object.title, style: {}, relationships: [], metadata: object.metadata ?? {}, raw: object }))
  const objects = [...snapshots, ...embedded]
  const viewport = editor.getViewport()
  const selectedObjectIds = [...editor.getSelectedIds(), ...(useAppStore.getState().selectedEmbeddedObjectId ? [useAppStore.getState().selectedEmbeddedObjectId!] : [])]
  return { schemaVersion: 'pythios.canvas.v1', capturedAt: new Date().toISOString(), viewport, objects, selectedObjectIds, visibleObjectIds: objects.map((object) => object.id), sceneGraph: buildSceneGraph(objects), embeddedObjects, metadata: { pageId: 'excalidraw-scene', shapeCount: elements.length, embeddedObjectCount: embeddedObjects.length } }
}

export function getSceneGraph(editor: CanvasEditor) { return getCanvasState(editor).sceneGraph }
export function getSelectedObjects(editor: CanvasEditor) { const state = getCanvasState(editor); const ids = new Set(state.selectedObjectIds); return state.objects.filter((object) => ids.has(object.id)) }
export function getVisibleObjects(editor: CanvasEditor) { return getCanvasState(editor).objects }
export function applyCanvasActions(editor: CanvasEditor, actions: CanvasAction[]): CanvasActionBatchResult { return { schemaVersion: 'pythios.canvas.actions.v1', appliedAt: new Date().toISOString(), results: actions.map((action) => applyAction(editor, action)) } }
