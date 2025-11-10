import { FC, Suspense, lazy, useEffect, useState } from 'react'
import OverviewPage from './OverviewPage'
import './App.css'

const TelemetryExplorer = lazy(() => import('./TelemetryExplorer'))

type TabKey = 'overview' | 'telemetry'

const LoadingPanel: FC<{ message: string }> = ({ message }) => (
  <div className="panel loading-panel">
    <div className="loading-spinner" aria-hidden />
    <p>{message}</p>
  </div>
)

const App: FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [hasMountedTelemetry, setHasMountedTelemetry] = useState<boolean>(false)

  useEffect(() => {
    if (activeTab === 'telemetry') setHasMountedTelemetry(true)
  }, [activeTab])

  const tabButtonClass = (tab: TabKey) =>
    activeTab === tab ? 'nav-tab nav-tab--active' : 'nav-tab'

  const shouldRenderTelemetry = activeTab === 'telemetry' || hasMountedTelemetry

  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="nav-brand">
          <span className="nav-brand__accent" aria-hidden />
          <span>Formula 1 Live Hub</span>
        </div>
        <nav className="nav-tabs">
          <button type="button" className={tabButtonClass('overview')} onClick={() => setActiveTab('overview')}>Overview</button>
          <button type="button" className={tabButtonClass('telemetry')} onClick={() => setActiveTab('telemetry')}>Telemetry</button>
        </nav>
      </header>

      <main className="app-main">
        <section className={activeTab === 'overview' ? 'tab-panel' : 'tab-panel tab-panel--hidden'}>
          <OverviewPage />
        </section>
        {shouldRenderTelemetry ? (
          <section className={activeTab === 'telemetry' ? 'tab-panel' : 'tab-panel tab-panel--hidden'}>
            <Suspense fallback={<LoadingPanel message="Loading telemetry workspace..." />}>
              <TelemetryExplorer />
            </Suspense>
          </section>
        ) : null}
      </main>

      <footer className="app-footer">
        <span>Data sourced live from the Ergast Developer API.</span>
        <span>Telemetry explorer powered by the Formula1 repository datasets.</span>
      </footer>
    </div>
  )
}

export default App

