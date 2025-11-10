import React, { useState } from 'react'
import OverviewPage from './OverviewPage'
import TelemetryExplorer from './TelemetryExplorer'
import './App.css'

type TabKey = 'overview' | 'telemetry'

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview')

  const tabButtonClass = (tab: TabKey) =>
    activeTab === tab ? 'nav-tab nav-tab--active' : 'nav-tab'

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
        <section className={activeTab === 'telemetry' ? 'tab-panel' : 'tab-panel tab-panel--hidden'}>
          <TelemetryExplorer />
        </section>
      </main>

      <footer className="app-footer">
        <span>Data sourced live from the Ergast Developer API.</span>
        <span>Telemetry explorer powered by the Formula1 repository datasets.</span>
      </footer>
    </div>
  )
}

export default App

