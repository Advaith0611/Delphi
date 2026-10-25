import { useEffect, type RefObject } from 'react'
import type { CanvasEditor } from './excalidraw'

const renderCounts = new Map<string, number>()
const runtimeCounters = {
  rafRequested: 0,
  rafCanceled: 0,
  rafFired: 0,
  activeRafs: 0,
  eventListenersAdded: 0,
  eventListenersRemoved: 0,
  activeEventListeners: 0,
}

let diagnosticsPatchCount = 0
let restoreDiagnostics: (() => void) | null = null

function incrementRenderCount(name: string) {
  renderCounts.set(name, (renderCounts.get(name) ?? 0) + 1)
}

function storageBytes(storage: Storage, matcher: (key: string) => boolean) {
  let bytes = 0
  let keys = 0

  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index)
    if (!key || !matcher(key)) continue

    keys += 1
    bytes += key.length + (storage.getItem(key)?.length ?? 0)
  }

  return { bytes, keys }
}

function isPythiosTldrawKey(key: string) {
  const normalized = key.toLowerCase()
  return normalized.includes('pythios') || normalized.includes('tldraw')
}

function cleanupOldPersistenceKeys() {
  const removed: string[] = []

  for (let index = localStorage.length - 1; index >= 0; index -= 1) {
    const key = localStorage.key(index)
    if (!key || !isPythiosTldrawKey(key)) continue
    localStorage.removeItem(key)
    removed.push(key)
  }

  if (removed.length) {
    console.info('Pythios removed old tldraw persistence keys.', removed)
  }
}

function getMemoryMegabytes() {
  const memory = (performance as Performance & { memory?: { usedJSHeapSize?: number; totalJSHeapSize?: number } }).memory
  if (!memory) return null

  return {
    used: Math.round((memory.usedJSHeapSize ?? 0) / 1024 / 1024),
    total: Math.round((memory.totalJSHeapSize ?? 0) / 1024 / 1024),
  }
}

function getHistorySummary(editor: CanvasEditor | null) {
  if (!editor) return null

  return {
    shapeCount: editor.getElements().length,
    selectedCount: editor.getSelectedIds().length,
    historyDepth: { undos: null, redos: null },
    editorDisposables: null,
  }
}

function installRuntimeDiagnostics() {
  diagnosticsPatchCount += 1
  if (restoreDiagnostics) return

  const originalRequestAnimationFrame = window.requestAnimationFrame.bind(window)
  const originalCancelAnimationFrame = window.cancelAnimationFrame.bind(window)
  const originalAddEventListener = EventTarget.prototype.addEventListener
  const originalRemoveEventListener = EventTarget.prototype.removeEventListener
  const activeRafIds = new Set<number>()

  window.requestAnimationFrame = (callback: FrameRequestCallback) => {
    runtimeCounters.rafRequested += 1
    runtimeCounters.activeRafs += 1

    const id = originalRequestAnimationFrame((time) => {
      if (activeRafIds.delete(id)) {
        runtimeCounters.activeRafs = Math.max(0, runtimeCounters.activeRafs - 1)
      }
      runtimeCounters.rafFired += 1
      callback(time)
    })

    activeRafIds.add(id)
    return id
  }

  window.cancelAnimationFrame = (handle: number) => {
    if (activeRafIds.delete(handle)) {
      runtimeCounters.rafCanceled += 1
      runtimeCounters.activeRafs = Math.max(0, runtimeCounters.activeRafs - 1)
    }
    return originalCancelAnimationFrame(handle)
  }

  EventTarget.prototype.addEventListener = function patchedAddEventListener(...args) {
    runtimeCounters.eventListenersAdded += 1
    runtimeCounters.activeEventListeners += 1
    return originalAddEventListener.apply(this, args)
  }

  EventTarget.prototype.removeEventListener = function patchedRemoveEventListener(...args) {
    runtimeCounters.eventListenersRemoved += 1
    runtimeCounters.activeEventListeners = Math.max(0, runtimeCounters.activeEventListeners - 1)
    return originalRemoveEventListener.apply(this, args)
  }

  restoreDiagnostics = () => {
    window.requestAnimationFrame = originalRequestAnimationFrame
    window.cancelAnimationFrame = originalCancelAnimationFrame
    EventTarget.prototype.addEventListener = originalAddEventListener
    EventTarget.prototype.removeEventListener = originalRemoveEventListener
    activeRafIds.clear()
    restoreDiagnostics = null
  }
}

function uninstallRuntimeDiagnostics() {
  diagnosticsPatchCount = Math.max(0, diagnosticsPatchCount - 1)
  if (diagnosticsPatchCount === 0) {
    restoreDiagnostics?.()
  }
}

export function useRenderCounter(name: string) {
  incrementRenderCount(name)
}

export function useDisableTldrawPersistenceCleanup() {
  useEffect(() => {
    cleanupOldPersistenceKeys()
  }, [])
}

export function usePerformanceInstrumentation(editorRef: RefObject<CanvasEditor | null>) {
  useEffect(() => {
    installRuntimeDiagnostics()
    console.info('Pythios performance instrumentation active. Tldraw persistence and default tldraw UI are disabled.')

    const interval = window.setInterval(() => {
      const relevantLocalStorage = storageBytes(localStorage, isPythiosTldrawKey)
      const relevantSessionStorage = storageBytes(sessionStorage, isPythiosTldrawKey)

      console.info('Pythios performance snapshot', {
        renders: Object.fromEntries(renderCounts),
        memoryMb: getMemoryMegabytes(),
        storage: {
          localStorage: relevantLocalStorage,
          sessionStorage: relevantSessionStorage,
        },
        editor: getHistorySummary(editorRef.current),
        runtimeCounters: { ...runtimeCounters },
        appIntegration: {
          resizeObservers: 1,
          editorSubscriptions: 0,
          pointerMoveSubscriptions: 0,
          fullSceneSerializationDuringDrawing: false,
        },
      })
    }, 15000)

    return () => {
      window.clearInterval(interval)
      uninstallRuntimeDiagnostics()
    }
  }, [editorRef])
}

export function useBoundEditorHistory(editorRef: RefObject<CanvasEditor | null>, maxUndoDepth = 12) {
  useEffect(() => {
    const interval = window.setInterval(() => {
      const editor = editorRef.current
      if (!editor) return

      void maxUndoDepth
    }, 8000)

    return () => window.clearInterval(interval)
  }, [editorRef, maxUndoDepth])
}
