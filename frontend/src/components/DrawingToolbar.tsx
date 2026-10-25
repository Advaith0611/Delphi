import { ArrowRight, Circle, Eraser, Hand, Minus, MousePointer2, Pencil, RectangleHorizontal, Type } from 'lucide-react'
import { memo, useEffect, useRef, useState } from 'react'
import type { CanvasEditor } from '../canvas/excalidraw'

type CanvasTool = 'selection' | 'hand' | 'freedraw' | 'rectangle' | 'ellipse' | 'arrow' | 'line' | 'text' | 'eraser'

const tools: Array<{ type: CanvasTool; label: string; Icon: typeof Pencil }> = [
  { type: 'selection', label: 'Select', Icon: MousePointer2 },
  { type: 'hand', label: 'Pan', Icon: Hand },
  { type: 'freedraw', label: 'Draw', Icon: Pencil },
  { type: 'rectangle', label: 'Rectangle', Icon: RectangleHorizontal },
  { type: 'ellipse', label: 'Circle', Icon: Circle },
  { type: 'arrow', label: 'Arrow', Icon: ArrowRight },
  { type: 'line', label: 'Line', Icon: Minus },
  { type: 'text', label: 'Text', Icon: Type },
  { type: 'eraser', label: 'Eraser', Icon: Eraser },
]

function DrawingToolbarComponent({ editor }: { editor: CanvasEditor }) {
  const [activeTool, setActiveTool] = useState<CanvasTool>('selection')
  const [tooltip, setTooltip] = useState<{ label: string; x: number; y: number } | null>(null)
  const tooltipTimerRef = useRef<number | null>(null)

  const clearTooltip = () => {
    if (tooltipTimerRef.current !== null) window.clearTimeout(tooltipTimerRef.current)
    tooltipTimerRef.current = null
    setTooltip(null)
  }

  useEffect(() => {
    const stop = editor.api.onChange((_, appState) => {
      const tool = appState.activeTool.type
      if (tools.some((item) => item.type === tool)) setActiveTool(tool as CanvasTool)
    })
    return () => {
      stop()
      if (tooltipTimerRef.current !== null) window.clearTimeout(tooltipTimerRef.current)
    }
  }, [editor])

  return (
    <nav className="drawing-toolbar" aria-label="Drawing tools">
      {tools.map(({ type, label, Icon }) => (
        <button
          key={type}
          type="button"
          title={label}
          aria-label={label}
          aria-pressed={activeTool === type}
          className={activeTool === type ? 'is-active' : ''}
          onPointerEnter={(event) => {
            const { clientX: x, clientY: y } = event
            tooltipTimerRef.current = window.setTimeout(() => setTooltip({ label, x, y }), 2000)
          }}
          onPointerMove={(event) => {
            setTooltip((current) => current?.label === label ? { ...current, x: event.clientX, y: event.clientY } : current)
          }}
          onPointerLeave={clearTooltip}
          onBlur={clearTooltip}
          onClick={() => {
            editor.api.setActiveTool({ type })
            setActiveTool(type)
          }}
        >
          <Icon size={18} />
        </button>
      ))}
      {tooltip ? <span className="drawing-toolbar-tooltip" style={{ left: tooltip.x + 12, top: tooltip.y + 16 }}>{tooltip.label}</span> : null}
    </nav>
  )
}

export const DrawingToolbar = memo(DrawingToolbarComponent)
