<template>
  <div class="aw-root">

    <!-- ── Header ──────────────────────────────────────────────────── -->
    <header class="aw-header">
      <div class="aw-logo">
        <span class="aw-logo-mark">✦</span>
        <span class="aw-logo-name">AirWave</span>
        <span class="aw-logo-tag">Fare Intelligence</span>
      </div>
    </header>

    <main class="aw-main">

      <!-- Search card -->
      <section class="aw-search-card">

        <!-- Trip type toggle -->
        <div class="trip-toggle">
          <button :class="['trip-btn', tripType === 'one_way' && 'active']"
            @click="tripType = 'one_way'; returnDate = ''">One-way</button>
          <button :class="['trip-btn', tripType === 'round_trip' && 'active']"
            @click="tripType = 'round_trip'">Round-trip</button>
        </div>

        <!-- Search fields row -->
        <div class="search-row">
          <div class="search-field">
            <label class="field-label">From</label>
            <input v-model="origin" class="field-input code-input" placeholder="LHR"
              maxlength="3" @input="origin = origin.toUpperCase()" spellcheck="false" />
            <span v-if="originName" class="field-hint">{{ originName }}</span>
          </div>

          <button class="swap-btn" @click="swapRoutes" title="Swap">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"/>
            </svg>
          </button>

          <div class="search-field">
            <label class="field-label">To</label>
            <input v-model="destination" class="field-input code-input" placeholder="JFK"
              maxlength="3" @input="destination = destination.toUpperCase()" spellcheck="false" />
            <span v-if="destName" class="field-hint">{{ destName }}</span>
          </div>

          <div class="search-field">
            <label class="field-label">Depart</label>
            <input v-model="departureDate" class="field-input" type="date" :min="today" />
          </div>

          <div v-if="tripType === 'round_trip'" class="search-field">
            <label class="field-label">Return</label>
            <input v-model="returnDate" class="field-input" type="date" :min="departureDate || today" />
          </div>

          <div class="search-field">
            <label class="field-label">Cabin</label>
            <select v-model="cabinClass" class="field-input">
              <option :value="1">Economy</option>
              <option :value="2">Prem. Economy</option>
              <option :value="3">Business</option>
              <option :value="4">First</option>
            </select>
          </div>
        </div>

        <!-- Config row -->
        <div class="config-row">
          <div class="search-field">
            <label class="field-label">Market shock</label>
            <select v-model="triggerId" class="field-input trigger-select">
              <option v-for="t in triggers" :key="t.id" :value="t.id">{{ t.label }}</option>
            </select>
          </div>

          <div class="search-field">
            <label class="field-label">Analysis depth</label>
            <div class="depth-tabs">
              <button v-for="d in depths" :key="d.key"
                :class="['depth-tab', depth === d.key && 'active']"
                @click="depth = d.key">{{ d.label }}</button>
            </div>
          </div>

          <div style="margin-left:auto">
            <button class="predict-btn" :disabled="isLoading || !canPredict" @click="runSimulation">
              <span v-if="!isLoading">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"
                  style="margin-right:6px;vertical-align:-2px">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>Predict Fares
              </span>
              <span v-else class="btn-loading">
                <span class="spinner"></span>{{ loadingMsg }}
              </span>
            </button>
          </div>
        </div>
      </section>

      <!-- Error -->
      <div v-if="error" class="error-bar">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>{{ error }}
      </div>

      <!-- Results -->
      <transition name="fade-up">
        <div v-if="result" class="results-grid">

          <!-- LEFT: flight card + weather -->
          <div class="col-left">

            <!-- Flight card -->
            <div class="flight-card">
              <div class="fc-header">
                <div class="route-pill">
                  <span class="rc">{{ result.route.split(' → ')[0] }}</span>
                  <svg width="28" height="12" viewBox="0 0 40 14" fill="none" class="ra">
                    <path d="M0 7h34M28 1l6 6-6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    <circle cx="4" cy="7" r="2.5" fill="currentColor"/>
                  </svg>
                  <span class="rc">{{ result.route.split(' → ')[1] }}</span>
                </div>
                <span :class="['trip-badge', result.fare_details?.trip_type === 'round_trip' ? 'badge-rt' : 'badge-ow']">
                  {{ result.fare_details?.trip_type === 'round_trip' ? 'Round-trip' : 'One-way' }}
                </span>
              </div>

              <div class="fc-body">
                <!-- Airline -->
                <div class="airline-col">
                  <div class="logo-wrap">
                    <img v-if="result.fare_details?.airline_logo"
                      :src="result.fare_details.airline_logo"
                      :alt="result.fare_details.airline_name"
                      class="airline-logo"
                      @error="e => e.target.style.display='none'" />
                    <div v-else class="logo-placeholder">{{ airlineInitials }}</div>
                  </div>
                  <span class="airline-name">{{ result.fare_details?.airline_name || 'Best Available' }}</span>
                  <span v-if="result.fare_details?.flight_number" class="flt-no">
                    {{ result.fare_details.flight_number }}
                  </span>
                </div>

                <!-- Times -->
                <div class="times-col">
                  <div class="t-block">
                    <span class="t-time">{{ result.fare_details?.departure_time || '—' }}</span>
                    <span class="t-iata">{{ result.route.split(' → ')[0] }}</span>
                    <span class="t-apt">{{ trunc(result.fare_details?.origin_airport_name, 20) }}</span>
                    <span class="t-date">{{ fmtDate(result.fare_details?.departure_date) }}</span>
                  </div>
                  <div class="dur-col">
                    <div class="dur-line"></div>
                    <span class="dur-text">{{ fmtDur(result.fare_details?.duration_min) }}</span>
                    <span :class="['stops-pill', result.fare_details?.is_direct ? 'direct' : 'stops']">
                      {{ result.fare_details?.is_direct ? 'Nonstop'
                        : `${result.fare_details?.num_stops} stop${result.fare_details?.num_stops > 1 ? 's' : ''}` }}
                    </span>
                  </div>
                  <div class="t-block t-right">
                    <span class="t-time">{{ result.fare_details?.arrival_time || '—' }}<sup
                      v-if="result.fare_details?.arrives_next_day" class="nd">+1</sup></span>
                    <span class="t-iata">{{ result.route.split(' → ')[1] }}</span>
                    <span class="t-apt">{{ trunc(result.fare_details?.dest_airport_name, 20) }}</span>
                  </div>
                </div>

                <!-- Fare -->
                <div class="fare-col">
                  <span class="fare-lbl">Current fare</span>
                  <span class="fare-val">${{ result.seed_fare.toLocaleString() }}</span>
                  <span class="cabin-pill">{{ cabinLabel }}</span>
                </div>
              </div>
            </div>

            <!-- Weather card -->
            <div v-if="result.disruption" class="weather-card" :class="`risk-${result.disruption.delay_risk}`">
              <div class="wc-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
                </svg>
                Weather Disruption
                <span :class="['risk-pill', `rp-${result.disruption.delay_risk}`]">
                  {{ result.disruption.delay_risk.toUpperCase() }}
                </span>
              </div>

              <div class="wx-pair">
                <div class="wx-airport" v-for="wx in [result.disruption.origin_weather, result.disruption.dest_weather]" :key="wx.airport_code">
                  <span class="wx-em">{{ wx.weather_emoji }}</span>
                  <div class="wx-info">
                    <span class="wx-cd">{{ wx.airport_code }}</span>
                    <span class="wx-ds">{{ wx.weather_desc }}</span>
                    <div class="wx-stats">
                      <span>💨 {{ wx.wind_speed_kmh }}km/h</span>
                      <span>🌧 {{ wx.precipitation_prob }}%</span>
                      <span>👁 {{ wx.visibility_km }}km</span>
                    </div>
                  </div>
                  <div class="wx-ring">
                    <svg width="42" height="42" viewBox="0 0 42 42">
                      <circle cx="21" cy="21" r="17" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="4"/>
                      <circle cx="21" cy="21" r="17" fill="none" :stroke="riskColor(wx.risk_level)"
                        stroke-width="4" stroke-linecap="round"
                        :stroke-dasharray="`${wx.disruption_score * 1.068} 106.8`"
                        transform="rotate(-90 21 21)"/>
                    </svg>
                    <span class="wx-sc">{{ wx.disruption_score }}</span>
                  </div>
                </div>
              </div>

              <div class="wx-summary">
                <div class="ot-row">
                  <span class="ot-lbl">On-time probability</span>
                  <div class="ot-bar"><div class="ot-fill"
                    :style="{width:`${result.disruption.on_time_probability*100}%`, background:ontimeColor}"></div></div>
                  <span class="ot-pct">{{ Math.round(result.disruption.on_time_probability * 100) }}%</span>
                </div>
                <p class="wx-primary">⚠ {{ result.disruption.primary_risk_factor }}</p>
                <span class="wx-fc">Forecast confidence: {{ result.disruption.forecast_confidence?.toUpperCase() }}</span>
              </div>
            </div>

          </div>

          <!-- RIGHT: AI prediction -->
          <div class="col-right">

            <!-- Prediction strip -->
            <div class="pred-card" :class="`cs-${result.agent_consensus}`">
              <div class="pred-header">
                <span class="pred-lbl">AI Fare Prediction</span>
                <span class="sim-id">{{ result.simulation_id }}</span>
              </div>
              <div class="pred-body">
                <div class="pred-main">
                  <span class="pred-sublbl">Predicted fare</span>
                  <span class="pred-val">${{ result.predicted_fare.toLocaleString() }}</span>
                  <span :class="['delta-badge', result.fare_delta >= 0 ? 'du' : 'dd']">
                    {{ result.fare_delta >= 0 ? '▲' : '▼' }} {{ Math.abs(result.fare_delta_pct) }}%
                  </span>
                </div>
                <div class="pred-meta">
                  <div class="pm-row">
                    <span class="pm-lbl">Consensus</span>
                    <span class="pm-val">{{ consensusLabel }}</span>
                  </div>
                  <div class="pm-row">
                    <span class="pm-lbl">Confidence</span>
                    <div class="conf-bar"><div class="conf-fill"
                      :style="{width:`${result.confidence*100}%`}"></div></div>
                    <span class="pm-val">{{ Math.round(result.confidence*100) }}%</span>
                  </div>
                  <div class="pm-row">
                    <span class="pm-lbl">Days to effect</span>
                    <span class="pm-val">T+{{ result.days_to_effect }}d</span>
                  </div>
                  <div class="pm-row">
                    <span class="pm-lbl">Shock</span>
                    <span class="pm-val trigger-chip">{{ result.trigger_id.replace(/_/g,' ') }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Agent decisions -->
            <div class="agents-card">
              <div class="card-title">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
                Agent Decisions
              </div>
              <div class="agents-list">
                <div v-for="a in visibleActions" :key="`${a.round}-${a.agent_id}`" class="agent-row">
                  <div class="agent-av" :style="{background: agentColor(a.agent_id)}">{{ a.agent_name[0] }}</div>
                  <div class="agent-body">
                    <div class="agent-hdr">
                      <span class="a-name">{{ a.agent_name }}</span>
                      <span class="a-round">R{{ a.round }}</span>
                      <span :class="['dec-chip', `dc-${a.decision}`]">{{ a.decision.replace(/_/g,' ') }}</span>
                      <span :class="['a-mag', a.magnitude_pct >= 0 ? 'pos' : 'neg']">
                        {{ a.magnitude_pct >= 0 ? '+' : '' }}{{ a.magnitude_pct }}%
                      </span>
                    </div>
                    <p class="a-reason">{{ a.reasoning }}</p>
                  </div>
                </div>
              </div>
              <button v-if="result.agent_actions.length > 4" class="show-more"
                @click="showAll = !showAll">
                {{ showAll ? 'Show less' : `Show all ${result.agent_actions.length} moves` }}
              </button>
            </div>

            <!-- Narrative -->
            <div class="narrative-card">
              <div class="card-title">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
                Analysis Report
              </div>
              <p class="narrative">{{ result.narrative }}</p>
            </div>

            <!-- Cascade -->
            <div class="cascade-card">
              <div class="card-title">P&amp;L Cascade Impacts</div>
              <div class="cascade-list">
                <div v-for="(imp, key) in topCascade" :key="key" class="cascade-row">
                  <span class="c-node">{{ key.replace(/_/g,' ') }}</span>
                  <div class="c-bar-wrap">
                    <div class="c-bar-fill" :style="{
                      width: `${Math.min(100, Math.abs(imp.impact)*200)}%`,
                      background: imp.impact >= 0 ? 'var(--up)' : 'var(--down)'
                    }"></div>
                  </div>
                  <span :class="['c-val', imp.impact >= 0 ? 'pos' : 'neg']">
                    {{ imp.impact >= 0 ? '+' : '' }}{{ (imp.impact*100).toFixed(0) }}%
                  </span>
                  <span class="c-days">T+{{ imp.days_to_effect }}d</span>
                </div>
              </div>
            </div>

            <!-- Sources -->
            <div class="sources-row">
              <span v-for="(src, key) in result.data_sources" :key="key"
                :class="['src-chip', src === 'synthetic' ? 'cs' : 'cl']">
                {{ key }}: {{ src }}
              </span>
            </div>

          </div>
        </div>
      </transition>

      <!-- Empty state -->
      <div v-if="!result && !isLoading" class="empty-state">
        <div class="empty-icon">✦</div>
        <h2 class="empty-h">Predict how fares will move</h2>
        <p class="empty-p">Enter a route, choose a market shock, and four AI agents simulate the airline pricing response in real time.</p>
        <div class="example-row">
          <button v-for="ex in examples" :key="ex.label" class="example-chip" @click="applyExample(ex)">
            {{ ex.label }}
          </button>
        </div>
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getTriggers, runSimulate } from '@/api/airwave.js'

const origin = ref('LHR')
const destination = ref('JFK')
const tripType = ref('one_way')
const departureDate = ref('')
const returnDate = ref('')
const cabinClass = ref(1)
const triggerId = ref('FUEL_SPIKE')
const depth = ref('standard')
const triggers = ref([])
const result = ref(null)
const error = ref('')
const isLoading = ref(false)
const showAll = ref(false)
const today = new Date().toISOString().split('T')[0]

const depths = [
  { key: 'fast', label: 'Fast', rounds: 2 },
  { key: 'standard', label: 'Standard', rounds: 5 },
  { key: 'deep', label: 'Deep', rounds: 8 },
  { key: 'exhaustive', label: 'Exhaustive', rounds: 12 },
]

const examples = [
  { label: 'LHR → JFK  Fuel Spike', origin: 'LHR', destination: 'JFK', trigger: 'FUEL_SPIKE' },
  { label: 'DXB → SIN  Demand Collapse', origin: 'DXB', destination: 'SIN', trigger: 'DEMAND_COLLAPSE' },
  { label: 'CDG → NRT  Exchange Rate', origin: 'CDG', destination: 'NRT', trigger: 'EXCHANGE_RATE' },
  { label: 'LAX → ORD  Disruption', origin: 'LAX', destination: 'ORD', trigger: 'DISRUPTION_EVENT' },
]

const airportNames = {
  LHR:'London Heathrow',LGW:'London Gatwick',JFK:'New York JFK',LAX:'Los Angeles',
  ORD:"Chicago O'Hare",ATL:'Atlanta',DFW:'Dallas/Fort Worth',SFO:'San Francisco',
  BOS:'Boston Logan',MIA:'Miami',EWR:'Newark',FRA:'Frankfurt',MUC:'Munich',
  CDG:'Paris CDG',AMS:'Amsterdam',ZRH:'Zurich',BRU:'Brussels',FCO:'Rome Fiumicino',
  MAD:'Madrid Barajas',BCN:'Barcelona',LIS:'Lisbon',ATH:'Athens',DXB:'Dubai',
  AUH:'Abu Dhabi',HKG:'Hong Kong',SIN:'Singapore Changi',NRT:'Tokyo Narita',
  HND:'Tokyo Haneda',ICN:'Seoul Incheon',PEK:'Beijing Capital',PVG:'Shanghai Pudong',
  BOM:'Mumbai',DEL:'Delhi IGI',SYD:'Sydney',MEL:'Melbourne',
  YYZ:'Toronto Pearson',YVR:'Vancouver',
}

const loadingMsgs = [
  'Fetching live fares…','Checking weather…','Running cascade model…',
  'Riley Chen: LCC strategy…','Marcus Webb: hedge position…',
  'Priya Sharma: corporate policy…','Sam Park: price elasticity…',
  'Synthesising prediction…',
]
const loadingMsg = ref(loadingMsgs[0])
let _lt = null

const originName = computed(() => airportNames[origin.value] || '')
const destName = computed(() => airportNames[destination.value] || '')
const canPredict = computed(() => origin.value.length === 3 && destination.value.length === 3 && triggerId.value)
const cabinLabel = computed(() => ({1:'Economy',2:'Prem. Economy',3:'Business',4:'First'})[cabinClass.value] || 'Economy')
const airlineInitials = computed(() => {
  const n = result.value?.fare_details?.airline_name || ''
  return n.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase() || 'AA'
})
const consensusLabel = computed(() => ({
  strong_raise:'⬆ Strong raise', moderate_raise:'↗ Moderate raise',
  hold:'→ Hold', moderate_drop:'↘ Moderate drop', strong_drop:'⬇ Strong drop',
})[result.value?.agent_consensus] || result.value?.agent_consensus || '')

const ontimeColor = computed(() => {
  const p = result.value?.disruption?.on_time_probability || 1
  if (p >= 0.8) return '#22c55e'
  if (p >= 0.6) return '#f59e0b'
  if (p >= 0.4) return '#f97316'
  return '#ef4444'
})

const visibleActions = computed(() =>
  showAll.value ? result.value?.agent_actions || []
  : (result.value?.agent_actions || []).slice(0, 4)
)

const topCascade = computed(() => {
  if (!result.value?.cascade_impacts) return {}
  const e = Object.entries(result.value.cascade_impacts)
  e.sort((a,b) => Math.abs(b[1].impact) - Math.abs(a[1].impact))
  return Object.fromEntries(e.slice(0,6))
})

onMounted(async () => {
  try { const r = await getTriggers(); if (r.success) triggers.value = r.data } catch {}
})

function swapRoutes() { [origin.value, destination.value] = [destination.value, origin.value] }
function applyExample(ex) { origin.value=ex.origin; destination.value=ex.destination; triggerId.value=ex.trigger }
function fmtDate(d) {
  if (!d) return ''
  try { return new Date(d+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}) }
  catch { return d }
}
function fmtDur(m) { if (!m) return ''; return `${Math.floor(m/60)}h ${m%60}m` }
function trunc(s, n) { if (!s) return ''; return s.length > n ? s.slice(0,n-1)+'…' : s }
function riskColor(lvl) { return {low:'#22c55e',moderate:'#f59e0b',high:'#f97316',severe:'#ef4444'}[lvl]||'#6b7280' }
function agentColor(id) { return {lcc_rm:'#6366f1',legacy_rm:'#0ea5e9',corporate_buyer:'#8b5cf6',leisure_traveler:'#10b981'}[id]||'#6b7280' }

async function runSimulation() {
  if (!canPredict.value || isLoading.value) return
  error.value = ''; result.value = null; isLoading.value = true
  let i = 0; loadingMsg.value = loadingMsgs[0]
  _lt = setInterval(() => { i=(i+1)%loadingMsgs.length; loadingMsg.value=loadingMsgs[i] }, 3500)
  const rounds = {fast:2,standard:5,deep:8,exhaustive:12}[depth.value]
  try {
    const res = await runSimulate({
      origin: origin.value, destination: destination.value,
      trigger_id: triggerId.value,
      departure_date: departureDate.value || undefined,
      return_date: returnDate.value || undefined,
      trip_type: tripType.value, cabin_class: cabinClass.value, rounds,
    })
    if (res.success) result.value = res.data
    else error.value = res.error || 'Simulation failed'
  } catch (e) { error.value = e.message || 'Network error' }
  finally { isLoading.value = false; clearInterval(_lt) }
}
</script>

<style scoped>
.aw-root {
  --bg: #07080d; --sf: #0f1117; --sf2: #161b27;
  --bd: rgba(255,255,255,0.07); --bdh: rgba(255,255,255,0.14);
  --ink: #e8eaf0; --ink2: #8b93a8; --ink3: #565e72;
  --ac: #4f8ef7; --acg: rgba(79,142,247,0.15);
  --up: #ef4444; --down: #22c55e; --hold: #f59e0b;
  --r: 12px; --rs: 8px;
  min-height: 100vh; background: var(--bg); color: var(--ink);
  font-family: 'Inter', system-ui, sans-serif; font-size: 14px; line-height: 1.5;
}

/* Header */
.aw-header { padding: 18px 32px; border-bottom: 1px solid var(--bd); display:flex; align-items:center; }
.aw-logo { display:flex; align-items:center; gap:10px; }
.aw-logo-mark { font-size:20px; color:var(--ac); }
.aw-logo-name { font-size:18px; font-weight:700; letter-spacing:-0.4px; }
.aw-logo-tag { font-size:11px; color:var(--ink3); background:var(--sf2); border:1px solid var(--bd);
  padding:2px 8px; border-radius:20px; letter-spacing:.5px; text-transform:uppercase; }

/* Main */
.aw-main { max-width:1200px; margin:0 auto; padding:28px 20px 64px; }

/* Search card */
.aw-search-card { background:var(--sf); border:1px solid var(--bd); border-radius:var(--r); padding:22px; margin-bottom:20px; }

.trip-toggle { display:flex; gap:4px; margin-bottom:18px; }
.trip-btn { padding:6px 16px; border-radius:20px; border:1px solid var(--bd); background:transparent;
  color:var(--ink2); font-size:13px; cursor:pointer; transition:all .15s; font-family:inherit; }
.trip-btn:hover { border-color:var(--bdh); color:var(--ink); }
.trip-btn.active { background:var(--acg); border-color:var(--ac); color:var(--ac); }

.search-row { display:flex; align-items:flex-end; gap:10px; flex-wrap:wrap; }
.search-field { display:flex; flex-direction:column; gap:4px; }
.field-label { font-size:11px; color:var(--ink3); letter-spacing:.6px; text-transform:uppercase; font-weight:500; }
.field-input { background:var(--sf2); border:1px solid var(--bd); border-radius:var(--rs); color:var(--ink);
  padding:10px 12px; font-size:14px; font-family:inherit; outline:none; transition:border-color .15s; }
.field-input:focus { border-color:var(--ac); }
.field-input option { background:var(--sf2); }
.code-input { font-size:22px; font-weight:700; letter-spacing:2px; text-align:center; padding:10px 8px; width:76px; }
.field-hint { font-size:11px; color:var(--ink3); white-space:nowrap; }
.swap-btn { background:var(--sf2); border:1px solid var(--bd); border-radius:50%; width:36px; height:36px;
  display:flex; align-items:center; justify-content:center; cursor:pointer; color:var(--ink2);
  flex-shrink:0; margin-bottom:4px; transition:all .15s; }
.swap-btn:hover { border-color:var(--ac); color:var(--ac); }
.trigger-select { min-width:200px; }

.config-row { display:flex; align-items:flex-end; gap:14px; margin-top:18px; flex-wrap:wrap; }
.depth-tabs { display:flex; gap:2px; background:var(--sf2); border:1px solid var(--bd); border-radius:var(--rs); padding:3px; }
.depth-tab { padding:6px 13px; border-radius:6px; border:none; background:transparent; color:var(--ink2);
  font-size:12px; font-family:inherit; cursor:pointer; transition:all .15s; }
.depth-tab:hover { color:var(--ink); }
.depth-tab.active { background:var(--ac); color:#fff; }

.predict-btn { padding:11px 26px; background:var(--ac); border:none; border-radius:var(--rs);
  color:#fff; font-size:14px; font-weight:600; font-family:inherit; cursor:pointer;
  display:flex; align-items:center; gap:4px; transition:opacity .15s, transform .1s; white-space:nowrap; }
.predict-btn:hover:not(:disabled) { opacity:.9; transform:translateY(-1px); }
.predict-btn:disabled { opacity:.45; cursor:not-allowed; transform:none; }
.btn-loading { display:flex; align-items:center; gap:8px; }
.spinner { width:13px; height:13px; border:2px solid rgba(255,255,255,.3); border-top-color:#fff;
  border-radius:50%; animation:spin .8s linear infinite; flex-shrink:0; }
@keyframes spin { to { transform:rotate(360deg); } }

/* Error */
.error-bar { background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.25); border-radius:var(--rs);
  padding:11px 14px; color:#fca5a5; display:flex; align-items:center; gap:8px; margin-bottom:20px; }

/* Results */
.results-grid { display:grid; grid-template-columns:400px 1fr; gap:18px; align-items:start; }
@media (max-width:860px) { .results-grid { grid-template-columns:1fr; } }
.col-left { display:flex; flex-direction:column; gap:14px; }
.col-right { display:flex; flex-direction:column; gap:12px; }

/* Flight card */
.flight-card { background:var(--sf); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.fc-header { padding:12px 16px; border-bottom:1px solid var(--bd); display:flex; align-items:center; justify-content:space-between; }
.route-pill { display:flex; align-items:center; gap:10px; }
.rc { font-size:18px; font-weight:700; letter-spacing:1px; }
.ra { color:var(--ink3); }
.trip-badge { font-size:11px; padding:3px 10px; border-radius:20px; font-weight:500; }
.badge-ow { background:rgba(79,142,247,.12); color:#93bbfc; border:1px solid rgba(79,142,247,.2); }
.badge-rt { background:rgba(139,92,246,.12); color:#c4b5fd; border:1px solid rgba(139,92,246,.2); }

.fc-body { padding:18px 16px; display:flex; align-items:center; gap:14px; }
.airline-col { display:flex; flex-direction:column; align-items:center; gap:5px; min-width:68px; }
.logo-wrap { width:50px; height:50px; background:#fff; border-radius:9px; display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0; }
.airline-logo { width:42px; height:42px; object-fit:contain; }
.logo-placeholder { width:100%; height:100%; background:var(--sf2); border-radius:9px; display:flex; align-items:center; justify-content:center; font-size:15px; font-weight:700; color:var(--ac); }
.airline-name { font-size:11px; color:var(--ink2); text-align:center; line-height:1.3; }
.flt-no { font-size:11px; color:var(--ink3); }

.times-col { flex:1; display:flex; align-items:center; gap:6px; }
.t-block { display:flex; flex-direction:column; gap:2px; min-width:68px; }
.t-block.t-right { align-items:flex-end; }
.t-time { font-size:22px; font-weight:700; letter-spacing:-.5px; font-variant-numeric:tabular-nums; }
.nd { font-size:11px; color:var(--hold); font-weight:600; }
.t-iata { font-size:12px; font-weight:600; color:var(--ac); }
.t-apt { font-size:11px; color:var(--ink3); line-height:1.3; }
.t-date { font-size:11px; color:var(--ink3); }
.dur-col { flex:1; display:flex; flex-direction:column; align-items:center; gap:4px; }
.dur-line { display:block; height:1px; width:100%; background:var(--bdh); }
.dur-text { font-size:11px; color:var(--ink3); }
.stops-pill { font-size:11px; padding:2px 8px; border-radius:20px; }
.stops-pill.direct { background:rgba(34,197,94,.12); color:#86efac; border:1px solid rgba(34,197,94,.2); }
.stops-pill.stops { background:rgba(249,115,22,.12); color:#fdba74; border:1px solid rgba(249,115,22,.2); }

.fare-col { display:flex; flex-direction:column; align-items:flex-end; gap:4px; min-width:86px; }
.fare-lbl { font-size:11px; color:var(--ink3); }
.fare-val { font-size:26px; font-weight:700; letter-spacing:-.5px; font-variant-numeric:tabular-nums; }
.cabin-pill { font-size:11px; color:var(--ink3); background:var(--sf2); border:1px solid var(--bd); padding:2px 8px; border-radius:20px; }

/* Weather card */
.weather-card { background:var(--sf); border:1px solid var(--bd); border-radius:var(--r); padding:16px; }
.weather-card.risk-severe { border-color:rgba(239,68,68,.3); }
.weather-card.risk-high { border-color:rgba(249,115,22,.3); }
.weather-card.risk-moderate { border-color:rgba(245,158,11,.3); }
.wc-title { font-size:11px; font-weight:600; color:var(--ink2); display:flex; align-items:center; gap:6px;
  margin-bottom:14px; text-transform:uppercase; letter-spacing:.5px; }
.risk-pill { margin-left:auto; font-size:11px; padding:2px 8px; border-radius:20px; font-weight:700; letter-spacing:.5px; }
.rp-low { background:rgba(34,197,94,.12); color:#86efac; border:1px solid rgba(34,197,94,.2); }
.rp-moderate { background:rgba(245,158,11,.12); color:#fcd34d; border:1px solid rgba(245,158,11,.2); }
.rp-high { background:rgba(249,115,22,.12); color:#fdba74; border:1px solid rgba(249,115,22,.2); }
.rp-severe { background:rgba(239,68,68,.12); color:#fca5a5; border:1px solid rgba(239,68,68,.2); }

.wx-pair { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px; }
.wx-airport { background:var(--sf2); border:1px solid var(--bd); border-radius:var(--rs); padding:10px;
  display:flex; align-items:flex-start; gap:8px; }
.wx-em { font-size:24px; flex-shrink:0; }
.wx-info { flex:1; }
.wx-cd { font-size:13px; font-weight:700; display:block; }
.wx-ds { font-size:11px; color:var(--ink2); display:block; margin-bottom:5px; }
.wx-stats { display:flex; flex-wrap:wrap; gap:5px; font-size:11px; color:var(--ink3); }
.wx-ring { position:relative; flex-shrink:0; }
.wx-sc { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); font-size:11px; font-weight:700; }

.wx-summary { padding-top:12px; border-top:1px solid var(--bd); }
.ot-row { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.ot-lbl { font-size:12px; color:var(--ink2); white-space:nowrap; }
.ot-bar { flex:1; height:5px; background:var(--sf2); border-radius:3px; overflow:hidden; }
.ot-fill { height:100%; border-radius:3px; transition:width .6s ease; }
.ot-pct { font-size:13px; font-weight:600; min-width:34px; text-align:right; }
.wx-primary { font-size:12px; color:var(--ink2); margin:0 0 5px; }
.wx-fc { font-size:11px; color:var(--ink3); }

/* Prediction card */
.pred-card { background:var(--sf); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.pred-card.cs-strong_raise { border-color:rgba(239,68,68,.35); }
.pred-card.cs-moderate_raise { border-color:rgba(249,115,22,.3); }
.pred-card.cs-hold { border-color:rgba(245,158,11,.3); }
.pred-card.cs-moderate_drop,.pred-card.cs-strong_drop { border-color:rgba(34,197,94,.3); }
.pred-header { padding:11px 16px; border-bottom:1px solid var(--bd); display:flex; align-items:center;
  justify-content:space-between; background:var(--sf2); }
.pred-lbl { font-size:11px; font-weight:600; letter-spacing:.5px; text-transform:uppercase; color:var(--ink2); }
.sim-id { font-size:11px; color:var(--ink3); font-family:monospace; }
.pred-body { padding:18px 16px; display:flex; gap:18px; align-items:flex-start; }
.pred-main { display:flex; flex-direction:column; gap:6px; min-width:140px; }
.pred-sublbl { font-size:11px; color:var(--ink3); }
.pred-val { font-size:34px; font-weight:700; letter-spacing:-1px; font-variant-numeric:tabular-nums; }
.delta-badge { display:inline-flex; align-items:center; gap:4px; font-size:13px; font-weight:700;
  padding:3px 10px; border-radius:20px; align-self:flex-start; }
.du { background:rgba(239,68,68,.12); color:#fca5a5; border:1px solid rgba(239,68,68,.2); }
.dd { background:rgba(34,197,94,.12); color:#86efac; border:1px solid rgba(34,197,94,.2); }
.pred-meta { flex:1; display:flex; flex-direction:column; gap:9px; }
.pm-row { display:flex; align-items:center; gap:10px; }
.pm-lbl { font-size:11px; color:var(--ink3); width:90px; flex-shrink:0; }
.pm-val { font-size:13px; font-weight:500; }
.conf-bar { flex:1; height:4px; background:var(--sf2); border-radius:2px; overflow:hidden; }
.conf-fill { height:100%; background:var(--ac); border-radius:2px; transition:width .6s ease; }
.trigger-chip { font-size:11px; background:var(--acg); color:var(--ac); border:1px solid rgba(79,142,247,.2);
  padding:2px 8px; border-radius:20px; text-transform:uppercase; letter-spacing:.5px; }

/* Agents */
.agents-card,.narrative-card,.cascade-card { background:var(--sf); border:1px solid var(--bd); border-radius:var(--r); padding:16px; }
.card-title { font-size:11px; font-weight:600; color:var(--ink2); text-transform:uppercase; letter-spacing:.5px;
  display:flex; align-items:center; gap:6px; margin-bottom:12px; }
.agents-list { display:flex; flex-direction:column; gap:9px; }
.agent-row { display:flex; gap:10px; align-items:flex-start; }
.agent-av { width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:12px; font-weight:700; color:#fff; flex-shrink:0; margin-top:2px; }
.agent-body { flex:1; }
.agent-hdr { display:flex; align-items:center; gap:7px; flex-wrap:wrap; margin-bottom:3px; }
.a-name { font-size:13px; font-weight:600; }
.a-round { font-size:11px; color:var(--ink3); background:var(--sf2); padding:1px 5px; border-radius:4px; }
.dec-chip { font-size:11px; padding:2px 7px; border-radius:20px; text-transform:capitalize; }
.dc-raise_fares { background:rgba(239,68,68,.12); color:#fca5a5; border:1px solid rgba(239,68,68,.2); }
.dc-hold_fares { background:rgba(245,158,11,.12); color:#fcd34d; border:1px solid rgba(245,158,11,.2); }
.dc-drop_fares { background:rgba(34,197,94,.12); color:#86efac; border:1px solid rgba(34,197,94,.2); }
.dc-delay_booking { background:rgba(139,92,246,.12); color:#c4b5fd; border:1px solid rgba(139,92,246,.2); }
.dc-accelerate_booking { background:rgba(14,165,233,.12); color:#7dd3fc; border:1px solid rgba(14,165,233,.2); }
.dc-shift_carrier { background:rgba(107,114,128,.12); color:#d1d5db; border:1px solid rgba(107,114,128,.2); }
.a-mag { font-size:12px; font-weight:700; margin-left:auto; }
.a-mag.pos { color:#fca5a5; } .a-mag.neg { color:#86efac; }
.a-reason { font-size:12px; color:var(--ink2); line-height:1.5; margin:0; }
.show-more { margin-top:10px; background:transparent; border:1px solid var(--bd); color:var(--ink2);
  font-size:12px; font-family:inherit; padding:6px 12px; border-radius:var(--rs); cursor:pointer;
  width:100%; transition:all .15s; }
.show-more:hover { border-color:var(--ac); color:var(--ac); }

/* Narrative */
.narrative { font-size:13px; color:var(--ink2); line-height:1.7; margin:0; }

/* Cascade */
.cascade-list { display:flex; flex-direction:column; gap:7px; }
.cascade-row { display:flex; align-items:center; gap:9px; }
.c-node { font-size:12px; color:var(--ink2); width:130px; flex-shrink:0; text-transform:capitalize; }
.c-bar-wrap { flex:1; height:4px; background:var(--sf2); border-radius:2px; overflow:hidden; }
.c-bar-fill { height:100%; border-radius:2px; transition:width .6s ease; }
.c-val { font-size:12px; font-weight:600; width:36px; text-align:right; }
.c-val.pos { color:#fca5a5; } .c-val.neg { color:#86efac; }
.c-days { font-size:11px; color:var(--ink3); width:32px; }

/* Sources */
.sources-row { display:flex; gap:6px; flex-wrap:wrap; }
.src-chip { font-size:11px; padding:3px 9px; border-radius:20px; }
.cl { background:rgba(34,197,94,.1); color:#86efac; border:1px solid rgba(34,197,94,.2); }
.cs { background:rgba(107,114,128,.1); color:#d1d5db; border:1px solid rgba(107,114,128,.2); }

/* Empty */
.empty-state { text-align:center; padding:70px 20px; }
.empty-icon { font-size:38px; color:var(--ac); margin-bottom:18px; }
.empty-h { font-size:22px; font-weight:700; margin:0 0 10px; letter-spacing:-.4px; }
.empty-p { color:var(--ink2); max-width:440px; margin:0 auto 24px; line-height:1.6; }
.example-row { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; }
.example-chip { padding:8px 16px; background:var(--sf); border:1px solid var(--bd); border-radius:20px;
  color:var(--ink2); font-size:13px; font-family:inherit; cursor:pointer; transition:all .15s; }
.example-chip:hover { border-color:var(--ac); color:var(--ac); background:var(--acg); }

/* Transitions */
.fade-up-enter-active { transition:opacity .4s ease, transform .4s ease; }
.fade-up-enter-from { opacity:0; transform:translateY(14px); }
@media (prefers-reduced-motion:reduce) {
  .fade-up-enter-active { transition:opacity .2s; }
  .fade-up-enter-from { transform:none; }
}

input[type="date"]::-webkit-calendar-picker-indicator { filter:invert(0.6); cursor:pointer; }
</style>
