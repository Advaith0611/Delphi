import type { CanvasEditor, ExcalidrawElement } from './excalidraw'
import { useAppStore } from '../store/useAppStore'
import type { SpatialShape } from '../types'

function shapeText(shape: ExcalidrawElement) {
  const text = (shape as ExcalidrawElement & { text?: string }).text
  return typeof text === 'string' ? text : undefined
}

export function serializeShape(shape: ExcalidrawElement): SpatialShape {
  return {
    id: shape.id,
    type: shape.type,
    x: shape.x,
    y: shape.y,
    w: shape.width,
    h: shape.height,
    text: shapeText(shape),
    geo: shape.type,
    color: shape.strokeColor,
  }
}

export function getSerializableShapes(editor: CanvasEditor, selectedOnly: boolean): SpatialShape[] {
  const selectedIds = new Set(editor.getSelectedIds())
  const { embeddedObjects, selectedEmbeddedObjectId } = useAppStore.getState()
  const canvasShapes = editor
    .getElements()
    .filter((shape) => !selectedOnly || selectedIds.has(shape.id))
    .map(serializeShape)
  const embeddedShapes = embeddedObjects
    .filter((object) => !selectedOnly || selectedEmbeddedObjectId === object.id)
    .map((object) => ({
      id: object.id,
      type: `embed:${object.kind}`,
      x: object.x,
      y: object.y,
      w: object.w,
      h: object.h,
      text: object.url ?? object.title,
      geo: object.mimeType,
    }))

  return [...canvasShapes, ...embeddedShapes]
}
