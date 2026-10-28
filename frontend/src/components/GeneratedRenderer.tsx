import { ArrowRight, CheckCircle2, ChevronLeft, ChevronRight, Columns3, ExternalLink, Gauge, ListChecks, Table2, TrendingUp } from 'lucide-react'
import { motion } from 'framer-motion'
import { useRenderCounter } from '../canvas/performanceInstrumentation'
import { useAppStore } from '../store/useAppStore'
import type { GeneratedComponent } from '../types'

const bars = [42, 68, 55, 83, 61, 74, 92]

function ComponentPanel({ component, index }: { component: GeneratedComponent; index: number }) {
  if (component.type === 'metric') {
    return (
      <article className="preview-card metric-card">
        <div>
          <span>{component.title}</span>
          <strong>{component.value ?? `${80 + index}%`}</strong>
        </div>
        <Gauge size={24} />
        <p>{component.detail ?? 'Generated KPI'}</p>
      </article>
    )
  }

  if (component.type === 'chart') {
    return (
      <article className="preview-card wide-card">
        <header>
          <div>
            <span>Chart</span>
            <h3>{component.title}</h3>
          </div>
          <TrendingUp size={20} />
        </header>
        <div className="chart-bars">
          {bars.map((height, barIndex) => (
            <span key={barIndex} style={{ height: `${height}%` }} />
          ))}
        </div>
      </article>
    )
  }

  if (component.type === 'table') {
    const columns = component.columns ?? ['Name', 'Status', 'Score']
    const rows = component.rows ?? []
    return (
      <article className="preview-card wide-card">
        <header>
          <div>
            <span>Table</span>
            <h3>{component.title}</h3>
          </div>
          <Table2 size={20} />
        </header>
        <div className="generated-table">
          <div className="table-row table-head" style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr)` }}>
            {columns.map((column) => (
              <span key={column}>{column}</span>
            ))}
          </div>
          {rows.map((row, rowIndex) => (
            <div className="table-row" style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr)` }} key={rowIndex}>
              {columns.map((column) => (
                <span key={column}>{String(row[column] ?? '-')}</span>
              ))}
            </div>
          ))}
        </div>
      </article>
    )
  }

  if (component.type === 'kanban') {
    return (
      <article className="preview-card wide-card">
        <header>
          <div>
            <span>Board</span>
            <h3>{component.title}</h3>
          </div>
          <Columns3 size={20} />
        </header>
        <div className="kanban-row">
          {(component.items ?? ['Intake', 'Build', 'Review']).map((item) => (
            <section key={item}>
              <strong>{item}</strong>
              <p>{component.detail ?? 'Generated lane'}</p>
            </section>
          ))}
        </div>
      </article>
    )
  }

  if (component.type === 'workflow' || component.type === 'timeline') {
    return (
      <article className="preview-card wide-card">
        <header>
          <div>
            <span>{component.type === 'workflow' ? 'Workflow' : 'Timeline'}</span>
            <h3>{component.title}</h3>
          </div>
          <ListChecks size={20} />
        </header>
        <ol className="workflow-list">
          {(component.items ?? ['Capture', 'Generate', 'Refine']).map((item) => (
            <li key={item}>
              <CheckCircle2 size={17} />
              <span>{item}</span>
              <ArrowRight size={15} />
            </li>
          ))}
        </ol>
      </article>
    )
  }

  if (component.type === 'button') {
    return (
      <article className="preview-card control-card">
        <span>Action</span>
        <button type="button">{component.label ?? component.title}</button>
      </article>
    )
  }

  if (component.type === 'input') {
    return (
      <article className="preview-card control-card">
        <span>{component.title}</span>
        <input placeholder={component.label ?? 'Type here'} />
      </article>
    )
  }

  return (
    <article className="preview-card note-card">
      <span>{component.type}</span>
      <h3>{component.title}</h3>
      <p>{component.detail}</p>
      <ul>
        {(component.items ?? []).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </article>
  )
}

export function GeneratedRenderer() {
  useRenderCounter('GeneratedRenderer')

  const generatedUI = useAppStore((state) => state.generatedUI)
  const lastShapeCount = useAppStore((state) => state.lastShapeCount)
  const status = useAppStore((state) => state.status)
  const isSidebarCollapsed = useAppStore((state) => state.isSidebarCollapsed)
  const setSidebarCollapsed = useAppStore((state) => state.setSidebarCollapsed)
  const projectId = useAppStore((state) => state.projectId)
  const projectUrl = useAppStore((state) => state.projectUrl)
  const agentActivity = useAppStore((state) => state.agentActivity)
  const setProjectId = useAppStore((state) => state.setProjectId)

  return (
    <aside className="generated-panel" aria-label="Generated interface preview">
      <button
        type="button"
        className="sidebar-toggle"
        title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-label={isSidebarCollapsed ? 'Expand generated preview sidebar' : 'Collapse generated preview sidebar'}
        aria-expanded={!isSidebarCollapsed}
        onClick={() => setSidebarCollapsed(!isSidebarCollapsed)}
      >
        {isSidebarCollapsed ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
      </button>
      <div className="panel-header">
        <div>
          <span>{projectId ? `Active project · ${projectId}` : 'Live generated interface'}</span>
          <h2>{generatedUI?.title ?? 'Draw a layout, then click generate'}</h2>
        </div>
        <div className="source-pill">{generatedUI?.source ?? 'ready'}</div>
      </div>
      <p className="panel-summary">
        {generatedUI?.summary ?? 'Sketch rectangles, labels, arrows, tables, or workflows. The preview renders as a functioning browser UI.'}
      </p>
      <div className="panel-meta">
        <span>{status}</span>
        <span>{lastShapeCount} shapes</span>
      </div>
      <section className="project-control" aria-label="Project workspace">
        <label htmlFor="project-id">Project ID</label>
        <div>
          <input
            id="project-id"
            value={projectId}
            onChange={(event) => setProjectId(event.target.value.toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 6))}
            placeholder="new project"
            maxLength={6}
            spellCheck={false}
          />
          {projectUrl ? (
            <a href={projectUrl} target="_blank" rel="noreferrer" title="Open published project">
              <ExternalLink size={16} />
            </a>
          ) : null}
        </div>
        <p>Leave empty to initialize one project. Enter an existing six-character code to edit only that project.</p>
      </section>
      {agentActivity.length ? (
        <section className="agent-activity" aria-label="Coding agent activity">
          <span>Agent activity</span>
          <ol>
            {agentActivity.map((entry, index) => <li key={`${entry}-${index}`}>{entry}</li>)}
          </ol>
        </section>
      ) : null}
      <motion.div className="preview-grid" layout>
        {(generatedUI?.components ?? []).map((component, index) => (
          <motion.div
            key={component.id}
            layout
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.03 }}
          >
            <ComponentPanel component={component} index={index} />
          </motion.div>
        ))}
      </motion.div>
    </aside>
  )
}
