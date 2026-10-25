import { Copy, ExternalLink, FileText, RefreshCw, Trash2 } from 'lucide-react'
import { memo, useCallback, useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import type { CanvasEditor } from './excalidraw'
import { useAppStore } from '../store/useAppStore'
import type { EmbeddedCanvasObject } from '../types'

interface EmbeddedCanvasLayerProps {
  editor: CanvasEditor
}

interface DragState {
  id: string
  mode: 'move' | 'resize'
  startClientX: number
  startClientY: number
  startX: number
  startY: number
  startW: number
  startH: number
}

const MIN_WIDTH = 180
const MIN_HEIGHT = 140

function formatFileSize(bytes?: number) {
  if (!bytes) return 'Unknown size'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unitIndex = 0

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }

  return `${value >= 10 || unitIndex === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unitIndex]}`
}

function getHostName(url?: string) {
  if (!url) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

function FileSummary({ object }: { object: EmbeddedCanvasObject }) {
  return (
    <div className="embedded-file-summary">
      <div className="embedded-file-icon">
        <FileText size={42} />
      </div>
      <strong>{object.title}</strong>
      <span>{object.mimeType || 'File'}</span>
      <span>{formatFileSize(object.size)}</span>
    </div>
  )
}

function decodeTextDataUrl(dataUrl: string) {
  const [, payload = ''] = dataUrl.split(',', 2)
  try {
    return decodeURIComponent(escape(window.atob(payload)))
  } catch {
    try {
      return decodeURIComponent(payload)
    } catch {
      return ''
    }
  }
}

function isTextPreview(object: EmbeddedCanvasObject) {
  const mime = object.mimeType?.toLowerCase() ?? ''
  const title = object.title.toLowerCase()
  return (
    Boolean(object.dataUrl) &&
    (mime.startsWith('text/') ||
      mime.includes('json') ||
      mime.includes('javascript') ||
      title.endsWith('.md') ||
      title.endsWith('.markdown') ||
      title.endsWith('.json') ||
      title.endsWith('.js') ||
      title.endsWith('.jsx') ||
      title.endsWith('.ts') ||
      title.endsWith('.tsx') ||
      title.endsWith('.html') ||
      title.endsWith('.css') ||
      title.endsWith('.py'))
  )
}

function TextFilePreview({ object }: { object: EmbeddedCanvasObject }) {
  const text = useMemo(() => (object.dataUrl ? decodeTextDataUrl(object.dataUrl) : ''), [object.dataUrl])

  return (
    <div className="embedded-text-preview">
      <pre>{text || 'No previewable text content.'}</pre>
    </div>
  )
}

function WebpageFrame({ object }: { object: EmbeddedCanvasObject }) {
  const [isLoading, setIsLoading] = useState(true)
  const [hasTimedOut, setHasTimedOut] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const timeoutRef = useRef<number | null>(null)
  const host = getHostName(object.url)
  const faviconUrl = useMemo(() => {
    if (!object.url) return undefined
    try {
      return `${new URL(object.url).origin}/favicon.ico`
    } catch {
      return undefined
    }
  }, [object.url])

  useEffect(() => {
    if (timeoutRef.current) window.clearTimeout(timeoutRef.current)
    timeoutRef.current = window.setTimeout(() => {
      setHasTimedOut(true)
    }, 8000)

    return () => {
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current)
    }
  }, [object.url, reloadKey])

  if (!object.url) return <FileSummary object={object} />

  return (
    <div className="embedded-webpage">
      <div className="embedded-webpage-tools">
        {faviconUrl ? <img src={faviconUrl} alt="" aria-hidden="true" /> : null}
        <span>{host}</span>
        <button
          type="button"
          title="Refresh webpage"
          onClick={() => {
            setIsLoading(true)
            setHasTimedOut(false)
            setReloadKey((key) => key + 1)
          }}
        >
          <RefreshCw size={14} />
        </button>
        <a href={object.url} target="_blank" rel="noreferrer" title="Open in new tab">
          <ExternalLink size={14} />
        </a>
      </div>
      <iframe
        key={reloadKey}
        title={object.title}
        src={object.url}
        sandbox="allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts"
        onLoad={() => {
          if (timeoutRef.current) window.clearTimeout(timeoutRef.current)
          setIsLoading(false)
          setHasTimedOut(false)
        }}
      />
      {isLoading || hasTimedOut ? (
        <div className="embedded-frame-status">
          <strong>{hasTimedOut ? 'This site may block embedding' : 'Loading webpage'}</strong>
          <span>{hasTimedOut ? 'Some sites use X-Frame-Options or CSP rules that prevent iframe previews.' : host}</span>
        </div>
      ) : null}
    </div>
  )
}

function EmbeddedContent({ object }: { object: EmbeddedCanvasObject }) {
  if (object.kind === 'image' && object.dataUrl) {
    return <img className="embedded-image-preview" src={object.dataUrl} alt={object.title} draggable={false} />
  }

  if (object.kind === 'pdf' && object.dataUrl) {
    return <iframe className="embedded-pdf-preview" title={object.title} src={object.dataUrl} />
  }

  if (object.kind === 'webpage') {
    return <WebpageFrame object={object} />
  }

  if (isTextPreview(object)) {
    return <TextFilePreview object={object} />
  }

  return <FileSummary object={object} />
}

function EmbeddedWindow({ editor, object, zoom }: { editor: CanvasEditor; object: EmbeddedCanvasObject; zoom: number }) {
  const selectedEmbeddedObjectId = useAppStore((state) => state.selectedEmbeddedObjectId)
  const setSelectedEmbeddedObjectId = useAppStore((state) => state.setSelectedEmbeddedObjectId)
  const updateEmbeddedObject = useAppStore((state) => state.updateEmbeddedObject)
  const deleteEmbeddedObject = useAppStore((state) => state.deleteEmbeddedObject)
  const duplicateEmbeddedObject = useAppStore((state) => state.duplicateEmbeddedObject)
  const isSelected = selectedEmbeddedObjectId === object.id
  const screenPoint = editor.sceneToScreen({ x: object.x, y: object.y })

  const style = {
    left: screenPoint.x,
    top: screenPoint.y,
    width: object.w * zoom,
    height: object.h * zoom,
  }

  const beginDrag = useCallback((event: ReactPointerEvent, mode: DragState['mode']) => {
    event.preventDefault()
    event.stopPropagation()
    setSelectedEmbeddedObjectId(object.id)

    const drag: DragState = {
      id: object.id,
      mode,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: object.x,
      startY: object.y,
      startW: object.w,
      startH: object.h,
    }

    const handlePointerMove = (moveEvent: PointerEvent) => {
      const dx = (moveEvent.clientX - drag.startClientX) / zoom
      const dy = (moveEvent.clientY - drag.startClientY) / zoom

      if (drag.mode === 'move') {
        updateEmbeddedObject(drag.id, { x: drag.startX + dx, y: drag.startY + dy })
      } else {
        updateEmbeddedObject(drag.id, {
          w: Math.max(MIN_WIDTH, drag.startW + dx),
          h: Math.max(MIN_HEIGHT, drag.startH + dy),
        })
      }
    }

    const handlePointerUp = () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
  }, [object.h, object.id, object.w, object.x, object.y, setSelectedEmbeddedObjectId, updateEmbeddedObject, zoom])

  return (
    <article
      className={`embedded-window${isSelected ? ' is-selected' : ''}`}
      style={style}
      onPointerDown={(event) => {
        event.stopPropagation()
        setSelectedEmbeddedObjectId(object.id)
      }}
    >
      <header className="embedded-window-header" onPointerDown={(event) => beginDrag(event, 'move')}>
        <span>{object.kind === 'webpage' ? getHostName(object.url) || object.title : object.title}</span>
        <div>
          <button type="button" title="Duplicate" onPointerDown={(event) => event.stopPropagation()} onClick={() => duplicateEmbeddedObject(object.id)}>
            <Copy size={14} />
          </button>
          <button type="button" title="Delete" onPointerDown={(event) => event.stopPropagation()} onClick={() => deleteEmbeddedObject(object.id)}>
            <Trash2 size={14} />
          </button>
        </div>
      </header>
      <div className="embedded-window-body">
        <EmbeddedContent object={object} />
      </div>
      <button
        type="button"
        className="embedded-resize-handle"
        title="Resize"
        onPointerDown={(event) => beginDrag(event, 'resize')}
      />
    </article>
  )
}

function EmbeddedCanvasLayerComponent({ editor }: EmbeddedCanvasLayerProps) {
  const embeddedObjects = useAppStore((state) => state.embeddedObjects)
  const setSelectedEmbeddedObjectId = useAppStore((state) => state.setSelectedEmbeddedObjectId)
  const [, setViewportTick] = useState(0)
  const zoom = editor.getViewport().z

  useEffect(() => {
    const updateViewport = () => setViewportTick((tick) => tick + 1)

    const stopChanges = editor.api.onChange(updateViewport)
    const stopScroll = editor.api.onScrollChange(updateViewport)

    return () => {
      stopChanges()
      stopScroll()
    }
  }, [editor])

  return (
    <div className="embedded-canvas-layer" onPointerDown={() => setSelectedEmbeddedObjectId(null)}>
      {embeddedObjects.map((object) => (
        <EmbeddedWindow key={object.id} editor={editor} object={object} zoom={zoom} />
      ))}
    </div>
  )
}

export const EmbeddedCanvasLayer = memo(EmbeddedCanvasLayerComponent)
