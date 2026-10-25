import { convertToExcalidrawElements } from '@excalidraw/excalidraw'
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types'

export type ExcalidrawElement = ReturnType<ExcalidrawImperativeAPI['getSceneElements']>[number]

export class CanvasEditor {
  readonly api: ExcalidrawImperativeAPI
  private container: HTMLElement

  constructor(api: ExcalidrawImperativeAPI, container: HTMLElement) {
    this.api = api
    this.container = container
  }

  getElements() {
    return this.api.getSceneElements()
  }

  getSelectedIds() {
    return Object.entries(this.api.getAppState().selectedElementIds)
      .filter(([, selected]) => selected)
      .map(([id]) => id)
  }

  getViewport() {
    const state = this.api.getAppState()
    const rect = this.container.getBoundingClientRect()
    return {
      x: state.scrollX,
      y: state.scrollY,
      z: state.zoom.value,
      screenBounds: { x: 0, y: 0, w: rect.width, h: rect.height },
    }
  }

  screenToScene(point: { x: number; y: number }) {
    const state = this.api.getAppState()
    return {
      x: (point.x - state.scrollX) / state.zoom.value,
      y: (point.y - state.scrollY) / state.zoom.value,
    }
  }

  sceneToScreen(point: { x: number; y: number }) {
    const state = this.api.getAppState()
    return {
      x: point.x * state.zoom.value + state.scrollX,
      y: point.y * state.zoom.value + state.scrollY,
    }
  }

  getViewportSceneBounds() {
    const viewport = this.getViewport()
    const topLeft = this.screenToScene({ x: 0, y: 0 })
    const bottomRight = this.screenToScene({ x: viewport.screenBounds.w, y: viewport.screenBounds.h })
    return { x: topLeft.x, y: topLeft.y, w: bottomRight.x - topLeft.x, h: bottomRight.y - topLeft.y }
  }

  getViewportCenterScene() {
    const { screenBounds } = this.getViewport()
    return this.screenToScene({ x: screenBounds.w / 2, y: screenBounds.h / 2 })
  }

  createElements(skeletons: Parameters<typeof convertToExcalidrawElements>[0]) {
    const elements = convertToExcalidrawElements(skeletons, { regenerateIds: false })
    this.api.updateScene({ elements: [...this.getElements(), ...elements] })
    return elements
  }

  updateElements(update: (element: ExcalidrawElement) => ExcalidrawElement) {
    this.api.updateScene({ elements: this.getElements().map(update) })
  }

  removeElements(ids: string[]) {
    const toRemove = new Set(ids)
    this.api.updateScene({ elements: this.getElements().filter((element) => !toRemove.has(element.id)) })
  }

  select(ids: string[]) {
    this.api.updateScene({ appState: { selectedElementIds: Object.fromEntries(ids.map((id) => [id, true])) } })
  }
}
