import { useState } from 'react'
import { Anomalies } from './components/Anomalies'
import { Assistant } from './components/Assistant'
import { DateFields } from './components/Common'
import { Consumption } from './components/Consumption'
import { Forecast } from './components/Forecast'
import { toWindow, type DateSelection } from './dates'

const tabs = ['Consumption', 'Anomalies', 'Forecast', 'Assistant'] as const
type Tab = typeof tabs[number]

export default function App() {
  // State is the page's small in-browser memory. Switching tabs updates just
  // the selected panel; it does not ask the server for a whole new HTML page.
  const [tab, setTab] = useState<Tab>('Consumption')
  const [dates, setDates] = useState<DateSelection>({ from: '2009-06-01', through: '2009-06-07' })
  const window = toWindow(dates)

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
      
    <header className="site-header">
      <a className="brand" href="./" aria-label="GreenTrack home">
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <path d="M25 6C12 4 4 10 7 20c9 6 18 0 18-14Z" fill="currentColor" />
          <path d="m8 25 13-14" stroke="#f4f5ed" strokeWidth="2" />
        </svg>
        GreenTrack<span className="brand-dot">.</span>
      </a>
      
      <span className="header-caption">Energy, understood.</span>
      <span className="workspace-label">Household insights</span>
    </header>
    
    <main id="main-content">

      <div className="page-heading">
        <div>
          <p className="eyebrow">Your energy workspace</p>
          <h1>A clearer view of your energy.</h1>
          <p>Explore consumption, notice unusual patterns, and look ahead.</p>
        </div>
        
        <div className="household-pill">
          <span aria-hidden="true">⌂</span>
          <div>
            <small>Selected household</small>
            <strong>household-1</strong>
          </div>
        </div>
      </div>

      <div className="filter-bar">
        <DateFields label="Historical period (UTC)" value={dates} onChange={setDates} />

        <p>Demo history: June 1-7, 2009.<br /><span>UTC is a demo convention only.</span></p>
      </div>

      {!window && <div role="alert" className="notice error">Choose valid historical dates with From on or before Through.</div>}

      <nav className="tabs" aria-label="Energy views">
        {tabs.map((name, index) => <button key={name} aria-current={tab === name ? 'page' : undefined} onClick={() => setTab(name)}>
          <span className="tab-number" aria-hidden="true">0{index + 1}</span>{name}
          </button>)}
      
      </nav>
      
      <div className="tab-content">
        {tab === 'Consumption' && <Consumption window={window} />}
        {tab === 'Anomalies' && <Anomalies window={window} />}
        {tab === 'Forecast' && <Forecast window={window} />}
        {/* A changed window remounts the assistant, cancelling its request and
            clearing the conversation so old replies cannot acquire new dates. */}
        {tab === 'Assistant' && <Assistant key={JSON.stringify(window)} window={window} />}
      </div>

      <footer>
        <strong>GreenTrack</strong>
        <p>Synthetic energy demo · Historical dates, illustrative forecast, placeholder assistant.</p>
        <span>Built to make patterns visible.</span>
      </footer>
      
    </main>
  </div>
}
