import { Toaster } from 'react-hot-toast'
import { CanvasWorkspace } from './canvas/CanvasWorkspace'
import { GeneratedRenderer } from './components/GeneratedRenderer'
import { useAppStore } from './store/useAppStore'
import './App.css'

export default function App() {
  const isSidebarCollapsed = useAppStore((state) => state.isSidebarCollapsed)

  return (
    <main className={`app-shell${isSidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: '#17120e',
            color: '#f1e6d4',
            border: '1px solid #3a2a1d',
            fontFamily: "'DM Sans', sans-serif",
          },
        }}
      />
      <CanvasWorkspace />
      <GeneratedRenderer />
    </main>
  )
}
