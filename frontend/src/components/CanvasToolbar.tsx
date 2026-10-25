import {
  Bot,
  Braces,
  FileUp,
  Globe2,
  ImagePlus,
  Sparkles,
  X,
} from 'lucide-react'
import { memo, useCallback, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { generateInterface } from '../ai/api'
import { applyCanvasActions, getCanvasState } from '../canvas/aiCanvasBridge'
import { getSerializableShapes } from '../canvas/shapes'
import { captureCanvasVisualContext } from '../canvas/visualContext'
import { useAppStore } from '../store/useAppStore'
import { useRenderCounter } from '../canvas/performanceInstrumentation'
import type { CanvasEditor } from '../canvas/excalidraw'
import type { EmbeddedCanvasObject, EmbeddedCanvasObjectKind } from '../types'

interface CanvasToolbarProps {
  editor: CanvasEditor
}

function createEmbeddedObjectId() {
  return `embed-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

function fileKind(file: File): EmbeddedCanvasObjectKind {
  if (file.type.startsWith('image/')) return 'image'
  if (file.type === 'application/pdf') return 'pdf'
  return 'file'
}

function normalizeUrl(value: string) {
  const trimmed = value.trim()
  if (!trimmed) return null
  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`

  try {
    return new URL(withProtocol).toString()
  } catch {
    return null
  }
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

function CanvasToolbarComponent({ editor }: CanvasToolbarProps) {
  useRenderCounter('CanvasToolbar')

  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const imageInputRef = useRef<HTMLInputElement | null>(null)
  const [isWebDialogOpen, setIsWebDialogOpen] = useState(false)
  const [webUrl, setWebUrl] = useState('')
  const prompt = useAppStore((state) => state.prompt)
  const selectedOnly = useAppStore((state) => state.selectedOnly)
  const isGenerating = useAppStore((state) => state.isGenerating)
  const addEmbeddedObject = useAppStore((state) => state.addEmbeddedObject)
  const setGeneratedUI = useAppStore((state) => state.setGeneratedUI)
  const setIsGenerating = useAppStore((state) => state.setIsGenerating)
  const setLastShapeCount = useAppStore((state) => state.setLastShapeCount)
  const setPrompt = useAppStore((state) => state.setPrompt)
  const setStatus = useAppStore((state) => state.setStatus)

  const getDropPoint = useCallback(() => {
    const center = editor.getViewportCenterScene()
    return { x: center.x - 180, y: center.y - 120 }
  }, [editor])

  const addFiles = useCallback(async (files: FileList | null) => {
    if (!files?.length) return

    const point = getDropPoint()

    try {
      const objects = await Promise.all(
        Array.from(files).map(async (file, index): Promise<EmbeddedCanvasObject> => {
          const kind = fileKind(file)
          const dataUrl = await readFileAsDataUrl(file)

          return {
            id: createEmbeddedObjectId(),
            kind,
            x: point.x + index * 28,
            y: point.y + index * 28,
            w: kind === 'image' ? 360 : 420,
            h: kind === 'image' ? 260 : 300,
            title: file.name,
            mimeType: file.type || 'Unknown type',
            size: file.size,
            dataUrl,
            createdAt: new Date().toISOString(),
          }
        }),
      )

      objects.forEach(addEmbeddedObject)
      toast.success(objects.length === 1 ? 'File embedded' : `${objects.length} files embedded`)
    } catch (error) {
      console.error(error)
      toast.error('Could not embed file')
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }, [addEmbeddedObject, getDropPoint])

  const addWebpage = useCallback(() => {
    const url = normalizeUrl(webUrl)
    if (!url) {
      toast.error('Enter a valid URL')
      return
    }

    const point = getDropPoint()
    addEmbeddedObject({
      id: createEmbeddedObjectId(),
      kind: 'webpage',
      x: point.x,
      y: point.y,
      w: 560,
      h: 380,
      title: new URL(url).hostname.replace(/^www\./, ''),
      url,
      createdAt: new Date().toISOString(),
    })
    setWebUrl('')
    setIsWebDialogOpen(false)
    toast.success('Webpage embedded')
  }, [addEmbeddedObject, getDropPoint, webUrl])

  const generate = useCallback(async () => {
    const shapes = getSerializableShapes(editor, selectedOnly)
    const canvasState = getCanvasState(editor)
    const trimmedPrompt = prompt.trim()
    setLastShapeCount(shapes.length)
    setIsGenerating(true)
    setStatus(trimmedPrompt ? `Drawing: ${trimmedPrompt}` : 'Drawing from default prompt')

    try {
      const visualContext = await captureCanvasVisualContext(editor)
      const response = await generateInterface({ shapes, canvasState, visualContext, prompt: trimmedPrompt, selectedOnly })
      const actions = response.actionBatch.actions
      const result = applyCanvasActions(editor, actions)
      const appliedCount = result.results.filter((actionResult) => actionResult.ok).length

      if (response.generatedUI) {
        setGeneratedUI(response.generatedUI)
      }

      const usedLocalFallback = response.generatedUI?.source === 'local'
      setStatus(
        usedLocalFallback
          ? 'Local fallback ran; connect the AI backend for canvas actions'
          : `AI Core ran: ${appliedCount}/${actions.length} action${actions.length === 1 ? '' : 's'} applied`,
      )
      toast.success(usedLocalFallback ? 'Local fallback generated the preview' : actions.length ? 'AI Core actions applied' : 'AI Core ran')
    } catch (error) {
      console.error(error)
      const message = errorMessage(error)
      setStatus(`Generation failed: ${message}`)
      toast.error(`Generation failed: ${message}`)
    } finally {
      setIsGenerating(false)
    }
  }, [editor, prompt, selectedOnly, setGeneratedUI, setIsGenerating, setLastShapeCount, setStatus])

  return (
    <div className="canvas-toolbar" aria-label="Spatial tools">
      <a className="toolbar-brand" href="https://pythios.xyz" aria-label="Back to Pythios home" title="Back to pythios.xyz">
        <img src="/logo.png" alt="Pythios" />
        <span>Pythios</span>
      </a>
      <span className="toolbar-divider" />
      <input
        ref={fileInputRef}
        type="file"
        hidden
        multiple
        accept=".pdf,.txt,.md,.markdown,.csv,.json,.ts,.tsx,.js,.jsx,.py,.html,.css"
        onChange={(event) => void addFiles(event.target.files)}
      />
      <input
        ref={imageInputRef}
        type="file"
        hidden
        multiple
        accept="image/*"
        onChange={(event) => void addFiles(event.target.files)}
      />
      <button type="button" onClick={() => fileInputRef.current?.click()} title="Upload file">
        <FileUp size={18} />
      </button>
      <button type="button" onClick={() => imageInputRef.current?.click()} title="Upload image">
        <ImagePlus size={18} />
      </button>
      <button type="button" onClick={() => setIsWebDialogOpen(true)} title="Embed webpage">
        <Globe2 size={18} />
      </button>
      <span className="toolbar-divider" />
      <input
        className="prompt-input"
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey && !isGenerating) {
            event.preventDefault()
            void generate()
          }
        }}
        placeholder="Draw a tree, sun, flowchart..."
        aria-label="Drawing prompt"
      />
      <span className="toolbar-divider" />
      <button type="button" onClick={generate} className="generate-button" disabled={isGenerating} title="Generate interface">
        {isGenerating ? <Braces size={18} /> : <Sparkles size={18} />}
        <span>{isGenerating ? 'Generating' : 'Generate'}</span>
      </button>
      <div className="ai-badge" title="Backend with local fallback">
        <Bot size={16} />
        AI
      </div>
      {isWebDialogOpen ? (
        <form
          className="web-embed-popover"
          onSubmit={(event) => {
            event.preventDefault()
            addWebpage()
          }}
        >
          <button type="button" className="popover-close" title="Close" onClick={() => setIsWebDialogOpen(false)}>
            <X size={15} />
          </button>
          <label htmlFor="web-embed-url">Webpage URL</label>
          <div>
            <input
              id="web-embed-url"
              value={webUrl}
              onChange={(event) => setWebUrl(event.target.value)}
              placeholder="https://example.com"
              autoFocus
            />
            <button type="submit">
              <Globe2 size={15} />
              <span>Add</span>
            </button>
          </div>
          <p>Sites with X-Frame-Options or restrictive CSP will show an embed warning.</p>
        </form>
      ) : null}
    </div>
  )
}

export const CanvasToolbar = memo(CanvasToolbarComponent)
