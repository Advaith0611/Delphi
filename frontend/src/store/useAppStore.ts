import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { EmbeddedCanvasObject, GeneratedUI } from '../types'

interface AppState {
  generatedUI: GeneratedUI | null
  embeddedObjects: EmbeddedCanvasObject[]
  selectedEmbeddedObjectId: string | null
  isSidebarCollapsed: boolean
  prompt: string
  selectedOnly: boolean
  lastShapeCount: number
  isGenerating: boolean
  status: string
  projectId: string
  projectUrl: string
  agentActivity: string[]
  setGeneratedUI: (ui: GeneratedUI | null) => void
  addEmbeddedObject: (object: EmbeddedCanvasObject) => void
  updateEmbeddedObject: (id: string, patch: Partial<EmbeddedCanvasObject>) => void
  deleteEmbeddedObject: (id: string) => void
  duplicateEmbeddedObject: (id: string) => void
  setSelectedEmbeddedObjectId: (id: string | null) => void
  setSidebarCollapsed: (isCollapsed: boolean) => void
  setPrompt: (prompt: string) => void
  setSelectedOnly: (selectedOnly: boolean) => void
  setLastShapeCount: (count: number) => void
  setIsGenerating: (isGenerating: boolean) => void
  setStatus: (status: string) => void
  setProjectId: (projectId: string) => void
  setProjectUrl: (projectUrl: string) => void
  setAgentActivity: (activity: string[]) => void
}

function createEmbeddedObjectId() {
  return `embed-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      generatedUI: null,
      embeddedObjects: [],
      selectedEmbeddedObjectId: null,
      isSidebarCollapsed: false,
      prompt: '',
      selectedOnly: false,
      lastShapeCount: 0,
      isGenerating: false,
      status: 'Ready',
      projectId: '',
      projectUrl: '',
      agentActivity: [],
      setGeneratedUI: (generatedUI) => set({ generatedUI }),
      addEmbeddedObject: (object) =>
        set((state) => ({
          embeddedObjects: [...state.embeddedObjects, object],
          selectedEmbeddedObjectId: object.id,
        })),
      updateEmbeddedObject: (id, patch) =>
        set((state) => ({
          embeddedObjects: state.embeddedObjects.map((object) => (object.id === id ? { ...object, ...patch } : object)),
        })),
      deleteEmbeddedObject: (id) =>
        set((state) => ({
          embeddedObjects: state.embeddedObjects.filter((object) => object.id !== id),
          selectedEmbeddedObjectId: state.selectedEmbeddedObjectId === id ? null : state.selectedEmbeddedObjectId,
        })),
      duplicateEmbeddedObject: (id) =>
        set((state) => {
          const source = state.embeddedObjects.find((object) => object.id === id)
          if (!source) return state

          const duplicate = {
            ...source,
            id: createEmbeddedObjectId(),
            x: source.x + 32,
            y: source.y + 32,
            title: `${source.title} copy`,
            createdAt: new Date().toISOString(),
          }

          return {
            embeddedObjects: [...state.embeddedObjects, duplicate],
            selectedEmbeddedObjectId: duplicate.id,
          }
        }),
      setSelectedEmbeddedObjectId: (selectedEmbeddedObjectId) => set({ selectedEmbeddedObjectId }),
      setSidebarCollapsed: (isSidebarCollapsed) => set({ isSidebarCollapsed }),
      setPrompt: (prompt) => set({ prompt }),
      setSelectedOnly: (selectedOnly) => set({ selectedOnly }),
      setLastShapeCount: (lastShapeCount) => set({ lastShapeCount }),
      setIsGenerating: (isGenerating) => set({ isGenerating }),
      setStatus: (status) => set({ status }),
      setProjectId: (projectId) => set({ projectId }),
      setProjectUrl: (projectUrl) => set({ projectUrl }),
      setAgentActivity: (agentActivity) => set({ agentActivity }),
    }),
    {
      name: 'pythios-app-state',
      partialize: (state) => ({
        embeddedObjects: state.embeddedObjects,
        isSidebarCollapsed: state.isSidebarCollapsed,
        projectId: state.projectId,
        projectUrl: state.projectUrl,
      }),
    },
  ),
)
