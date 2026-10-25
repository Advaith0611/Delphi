import { Excalidraw } from '@excalidraw/excalidraw'
import '@excalidraw/excalidraw/index.css'
import { memo, useCallback, useRef, useState } from 'react'
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types'
import { CanvasHints } from '../components/CanvasHints'
import { CanvasToolbar } from '../components/CanvasToolbar'
import { DrawingToolbar } from '../components/DrawingToolbar'
import { EmbeddedCanvasLayer } from './EmbeddedCanvasLayer'
import { CanvasEditor } from './excalidraw'
import { useCanvasSizeGuard } from './useCanvasSizeGuard'

function CanvasWorkspaceComponent() {
  const containerRef = useRef<HTMLElement | null>(null)
  const [editor, setEditor] = useState<CanvasEditor | null>(null)

  useCanvasSizeGuard(containerRef)

  const handleApi = useCallback((api: ExcalidrawImperativeAPI) => {
    if (containerRef.current) setEditor(new CanvasEditor(api, containerRef.current))
  }, [])

  return (
    <section className="canvas-stage" ref={containerRef}>
      <div className="excalidraw-viewport">
        <Excalidraw
          excalidrawAPI={handleApi}
          initialData={{ appState: { viewBackgroundColor: '#f7efe3' } }}
          UIOptions={{ canvasActions: { loadScene: false, saveToActiveFile: false, export: false } }}
        />
      </div>
      {editor ? (
        <div className="canvas-overlays">
          <EmbeddedCanvasLayer editor={editor} />
          <CanvasToolbar editor={editor} />
          <DrawingToolbar editor={editor} />
          <CanvasHints />
        </div>
      ) : null}
    </section>
  )
}

export const CanvasWorkspace = memo(CanvasWorkspaceComponent)
