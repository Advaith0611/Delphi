import { exportToCanvas } from '@excalidraw/excalidraw'
import type { CanvasEditor } from './excalidraw'
import { useAppStore } from '../store/useAppStore'
import type { CanvasBounds, CanvasVisualContext } from '../ai/canvasProtocol'
import type { EmbeddedCanvasObject } from '../types'

const MAX_VISUAL_WIDTH = 1600
const MAX_VISUAL_HEIGHT = 1000

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Could not load image for canvas visual context'))
    image.src = src
  })
}

function objectIntersectsViewport(object: EmbeddedCanvasObject, bounds: CanvasBounds) {
  return object.x + object.w >= bounds.x && object.x <= bounds.x + bounds.w && object.y + object.h >= bounds.y && object.y <= bounds.y + bounds.h
}

function drawEmbeddedFallback(ctx: CanvasRenderingContext2D, object: EmbeddedCanvasObject, x: number, y: number, w: number, h: number) {
  ctx.fillStyle = object.kind === 'webpage' ? '#17120e' : '#15100c'
  ctx.strokeStyle = object.kind === 'webpage' ? '#d6a24c' : '#3a2a1d'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, 8)
  ctx.fill()
  ctx.stroke()

  ctx.fillStyle = '#f1e6d4'
  ctx.font = '500 14px "DM Mono", monospace'
  ctx.fillText(object.kind.toUpperCase(), x + 14, y + 28)

  ctx.fillStyle = '#ad9c88'
  ctx.font = '400 13px "DM Sans", sans-serif'
  const label = object.url ?? object.title
  ctx.fillText(label.slice(0, 72), x + 14, y + 52)
}

async function drawEmbeddedObject(
  ctx: CanvasRenderingContext2D,
  object: EmbeddedCanvasObject,
  viewportBounds: CanvasBounds,
  scale: number,
) {
  const x = (object.x - viewportBounds.x) * scale
  const y = (object.y - viewportBounds.y) * scale
  const w = object.w * scale
  const h = object.h * scale

  if (object.kind === 'image' && object.dataUrl) {
    try {
      const image = await loadImage(object.dataUrl)
      ctx.drawImage(image, x, y, w, h)
      ctx.strokeStyle = '#3a2a1d'
      ctx.lineWidth = 1
      ctx.strokeRect(x, y, w, h)
      return
    } catch {
      drawEmbeddedFallback(ctx, object, x, y, w, h)
      return
    }
  }

  drawEmbeddedFallback(ctx, object, x, y, w, h)
}

function createBlankDataUrl(width: number, height: number) {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (ctx) {
    ctx.fillStyle = '#0d0b09'
    ctx.fillRect(0, 0, width, height)
  }
  return canvas.toDataURL('image/png')
}

export async function captureCanvasVisualContext(editor: CanvasEditor): Promise<CanvasVisualContext> {
  const viewportPageBounds = editor.getViewportSceneBounds()
  const screenBounds = editor.getViewport().screenBounds
  const exportScale = Math.min(1, MAX_VISUAL_WIDTH / screenBounds.w, MAX_VISUAL_HEIGHT / screenBounds.h)
  const width = Math.max(1, Math.round(screenBounds.w * exportScale))
  const height = Math.max(1, Math.round(screenBounds.h * exportScale))
  const pageToImageScale = width / viewportPageBounds.w
  const elements = editor.getElements()
  const notes = [
    'Captured only when the user clicked Generate.',
    'Webpage embeds are represented by their visible frame metadata because browser security prevents reading cross-origin iframe pixels.',
  ]

  let baseImage = { url: createBlankDataUrl(width, height), width, height }
  if (elements.length) {
    try {
      const exported = await exportToCanvas({
        elements,
        appState: { ...editor.api.getAppState(), viewBackgroundColor: '#f7efe3' },
        files: editor.api.getFiles(),
        maxWidthOrHeight: Math.max(width, height),
      })
      baseImage = { url: exported.toDataURL('image/png'), width: exported.width, height: exported.height }
    } catch {
      notes.push('Excalidraw bitmap export failed; using a generated visual context fallback.')
    }
  }

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return {
      schemaVersion: 'pythios.canvas.visual.v1',
      capturedAt: new Date().toISOString(),
      format: 'image/png',
      dataUrl: createBlankDataUrl(width, height),
      width,
      height,
      viewportPageBounds,
      notes: [...notes, 'Browser canvas context was unavailable; using a blank visual context fallback.'],
    }
  }

  ctx.fillStyle = '#0d0b09'
  ctx.fillRect(0, 0, width, height)

  try {
    const image = await loadImage(baseImage.url)
    ctx.drawImage(image, 0, 0, width, height)
  } catch {
    notes.push('Excalidraw bitmap export could not be loaded into the visual context canvas.')
  }

  const embeddedObjects = useAppStore
    .getState()
    .embeddedObjects.filter((object) => objectIntersectsViewport(object, viewportPageBounds))

  for (const object of embeddedObjects) {
    await drawEmbeddedObject(ctx, object, viewportPageBounds, pageToImageScale)
  }

  return {
    schemaVersion: 'pythios.canvas.visual.v1',
    capturedAt: new Date().toISOString(),
    format: 'image/png',
    dataUrl: canvas.toDataURL('image/png'),
    width,
    height,
    viewportPageBounds,
    notes,
  }
}
