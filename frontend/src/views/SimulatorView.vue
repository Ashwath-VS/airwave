<template>
  <div class="sim-layout">

    <!-- ── Header ──────────────────────────────────────────────── -->
    <header class="top-bar">
      <div class="brand">
        <span class="brand-icon">✈</span>
        AIRWAVE
        <span class="brand-sub">Fare Intelligence Engine</span>
      </div>

      <div class="macro-ticker" v-if="macro.vix">
        <span class="tick" :class="tickClass(macro.vix, 25, 35)">
          VIX <strong>{{ macro.vix }}</strong>
        </span>
        <span class="tick-sep">·</span>
        <span class="tick">
          WTI <strong>${{ macro.wti }}</strong>
        </span>
        <span class="tick-sep">·</span>
        <span class="tick">
          EUR <strong>{{ macro.eur }}</strong>
        </span>
        <span class="tick-sep">·</span>
        <span class="tick-source" :class="macro.source === 'live' ? 'live' : 'stale'">
          {{ macro.source }}
        </span>
      </div>

      <div class="header-actions">
        <a href="https://s-ashwath.netlify.app/traveltech" target="_blank" class="back-link">
          ← Portfolio
        </a>
      </div>
    </header>

    <!-- ── Body ────────────────────────────────────────────────── -->
    <main class="body">

      <!-- Left: Controls -->
      <aside class="controls">

        <!-- Route + Date -->
        <section class="ctrl-section">
          <div class="section-label">ROUTE</div>
          <div class="route-inputs">
            <div class="iata-field">
              <label>FROM</label>
              <input
                v-model="origin"
                maxlength="3"
                placeholder="LHR"
                @input="origin = origin.toUpperCase()"
                :class="{ error: originErr }"
              />
              <span v-if="originErr" class="field-err">3-letter IATA</span>
            </div>
            <span class="route-arrow">→</span>
            <div class="iata-field">
              <label>TO</label>
              <input
                v-model="destination"
                maxlength="3"
                placeholder="JFK"
                @input="destination = destination.toUpperCase()"
                :class="{ error: destErr }"
              />
              <span v-if="destErr" class="field-err">3-letter IATA</span>
            </div>
          </div>

          <!-- Departure date -->
          <div class="date-field">
            <label class="date-label">
              TRAVEL DATE
              <span class="date-hint">one-way · fares fetched for this date</span>
            </label>
            <input
              type="date"
              v-model="departureDate"
              :min="minDate"
              class="date-input"
            />
          </div>
        </section>

        <!-- Trigger -->
        <section class="ctrl-section">
          <div class="section-label">MACRO TRIGGER</div>
          <div class="trigger-grid">
            <button
              v-for="t in triggers"
              :key="t.id"
              class="trigger-btn"
              :class="{ active: selectedTrigger === t.id }"
              @click="selectedTrigger = t.id"
            >
              <span class="trigger-icon">{{ TRIGGER_ICONS[t.id] || '⚡' }}</span>
              <span class="trigger-label">{{ t.label }}</span>
            </button>
          </div>
        </section>

        <!-- Analysis Depth (was: SIM ROUNDS) -->
        <section class="ctrl-section depth-section">
          <div class="section-label">ANALYSIS DEPTH</div>
          <div class="rounds-control">
            <button class="rounds-btn" @click="rounds = Math.max(2, rounds - 1)">−</button>
            <span class="rounds-val">{{ rounds }}</span>
            <button class="rounds-btn" @click="rounds = Math.min(16, rounds + 1)">+</button>
            <span class="depth-badge" :class="depthClass">{{ depthLabel }}</span>
          </div>
          <div class="depth-desc">{{ depthDesc }}</div>
        </section>

        <!-- Live data preview (shown after seed loads or after simulation) -->
        <section class="ctrl-section" v-if="seed">
          <div class="section-label">LIVE MARKET DATA</div>
          <div class="seed-grid">
            <div class="seed-row">
              <span class="seed-key">FARE</span>
              <span class="seed-val acc">${{ seed.fare.current_price_usd }}</span>
              <span class="seed-src">{{ seed.fare.source }}</span>
            </div>
            <div class="seed-row">
              <span class="seed-key">DEMAND IDX</span>
              <span class="seed-val">{{ seed.demand.demand_index }}</span>
              <span class="seed-src">{{ seed.demand.source }}</span>
            </div>
            <div class="seed-row">
              <span class="seed-key">BASELINE</span>
              <span class="seed-val">${{ seed.history.baseline_price_usd }}</span>
              <span class="seed-src">{{ seed.history.source }}</span>
            </div>
            <div class="seed-row">
              <span class="seed-key">VIX / WTI</span>
              <span class="seed-val">{{ seed.macro.vix }} / ${{ seed.macro.wti_price }}</span>
              <span class="seed-src">{{ seed.macro.source }}</span>
            </div>
          </div>
        </section>

        <!-- Action buttons -->
        <div class="action-row">
          <button
            class="btn-primary"
            @click="doSimulate"
            :disabled="loading || !llmAvailable"
            :title="!llmAvailable ? 'LLM_API_KEY not configured' : ''"
          >
            {{ loading ? loadingLabel : 'PREDICT FARES' }}
          </button>
        </div>

        <div v-if="!llmAvailable" class="llm-warning">
          ⚠ LLM_API_KEY not set — add Gemini key to backend .env to run simulations.
          Cascade-only mode is still available.
        </div>

        <div v-if="errorMsg" class="error-box">{{ errorMsg }}</div>

      </aside>

      <!-- Right: Results -->
      <section class="results" :class="{ 'results-empty': !result && !cascadeResult }">

        <!-- Empty state -->
        <div v-if="!result && !cascadeResult && !loading" class="empty-state">
          <div class="empty-icon">✈</div>
          <div class="empty-title">Select a route and macro trigger</div>
          <div class="empty-desc">
            Pick a route, choose the market shock you want to model, then hit
            <strong>Predict Fares</strong> — AirWave fetches live prices and
            runs four AI airline agents through the scenario.
          </div>
          <div class="empty-routes">
            <span v-for="r in SAMPLE_ROUTES" :key="r" class="sample-route" @click="setRoute(r)">{{ r }}</span>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <div class="loading-label">{{ loadingLabel }}</div>
          <div class="loading-sub">{{ loadingSub }}</div>
        </div>

        <!-- Cascade-only result (fast, no LLM) -->
        <template v-if="cascadeResult && !result">
          <div class="result-block">
            <div class="block-header">
              <span class="block-title">P&amp;L CASCADE</span>
              <span class="block-tag">{{ cascadeResult.trigger_id }}</span>
            </div>
            <CascadeChart :impacts="cascadeResult.impacts" />
            <div class="cascade-note">
              Agent simulation requires LLM_API_KEY. Showing cascade model only.
            </div>
          </div>
        </template>

        <!-- Full simulation result -->
        <template v-if="result">

          <!-- Fare prediction card -->
          <div class="result-block fare-card">
            <div class="fare-route">{{ result.route }} · {{ displayDate }}</div>
            <div class="fare-row">
              <div class="fare-col">
                <div class="fare-lbl">TODAY'S FARE</div>
                <div class="fare-val">${{ result.seed_fare }}</div>
              </div>
              <div class="fare-arrow" :class="result.fare_delta >= 0 ? 'pos' : 'neg'">
                {{ result.fare_delta >= 0 ? '▲' : '▼' }}
              </div>
              <div class="fare-col">
                <div class="fare-lbl">PREDICTED IN {{ result.days_to_effect }}d</div>
                <div class="fare-val" :class="result.fare_delta >= 0 ? 'pos' : 'neg'">
                  ${{ result.predicted_fare }}
                </div>
              </div>
              <div class="fare-col right">
                <div class="fare-delta" :class="result.fare_delta >= 0 ? 'pos' : 'neg'">
                  {{ result.fare_delta >= 0 ? '+' : '' }}{{ result.fare_delta_pct }}%
                </div>
                <div class="fare-consensus">{{ result.agent_consensus.replace('_', ' ') }}</div>
                <div class="fare-conf">{{ (result.confidence * 100).toFixed(0) }}% confidence</div>
              </div>
            </div>
          </div>

          <!-- Cascade chart -->
          <div class="result-block">
            <div class="block-header">
              <span class="block-title">P&amp;L CASCADE — HOW THE SHOCK SPREADS</span>
              <span class="block-tag">{{ result.trigger_id }}</span>
            </div>
            <CascadeChart :impacts="result.cascade_impacts" />
          </div>

          <!-- Agent timeline -->
          <div class="result-block">
            <div class="block-header">
              <span class="block-title">HOW EACH MARKET PLAYER RESPONDED</span>
              <span class="block-tag">{{ result.agent_actions.length }} decisions</span>
            </div>
            <div class="timeline-legend">
              <span class="leg raise">▲ raise fares</span>
              <span class="leg drop">▼ drop fares</span>
              <span class="leg accel">⚡ book now</span>
              <span class="leg delay">⏸ delay booking</span>
              <span class="leg hold">— hold</span>
            </div>
            <div class="timeline">
              <div
                v-for="(a, i) in result.agent_actions"
                :key="i"
                class="timeline-row"
                :class="decisionClass(a.decision)"
              >
                <span class="tl-round">R{{ a.round }}</span>
                <span class="tl-agent">{{ a.agent_name.split(' ')[0] }}</span>
                <span class="tl-role">{{ shortRole(a.agent_id) }}</span>
                <span class="tl-decision">{{ friendlyDecision(a.decision) }}</span>
                <span class="tl-mag" :class="a.magnitude_pct >= 0 ? 'pos' : 'neg'">
                  {{ a.magnitude_pct >= 0 ? '+' : '' }}{{ a.magnitude_pct }}%
                </span>
                <span class="tl-reason">{{ a.reasoning }}</span>
              </div>
            </div>
          </div>

          <!-- Narrative report -->
          <div class="result-block">
            <div class="block-header">
              <span class="block-title">INTELLIGENCE BRIEF</span>
              <span class="block-tag">{{ result.simulation_id }}</span>
            </div>
            <div class="narrative" v-html="renderMarkdown(result.narrative)"></div>
          </div>

          <!-- Data sources -->
          <div class="result-block sources-block">
            <div class="block-header"><span class="block-title">DATA SOURCES</span></div>
            <div class="sources-grid">
              <span v-for="(v, k) in result.data_sources" :key="k" class="source-chip" :class="v">
                {{ k }}: {{ v }}
              </span>
            </div>
          </div>

        </template>

      </section>
    </main>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { getTriggers, fetchSeed, runCascade, runSimulate, getHealth } from '../api/airwave.js'
import CascadeChart from '../components/CascadeChart.vue'

// ── Constants ─────────────────────────────────────────────────
const TRIGGER_ICONS = {
  FUEL_SPIKE:        '⛽',
  DEMAND_COLLAPSE:   '📉',
  CAPACITY_DUMP:     '✈',
  ROUTE_CANCELLATION:'🚫',
  EXCHANGE_RATE:     '💱',
  DISRUPTION_EVENT:  '⚠',
}

const SAMPLE_ROUTES = ['LHR→JFK', 'JFK→LAX', 'DXB→SIN', 'CDG→LHR', 'SYD→SIN']

// ── Helpers: date defaults ─────────────────────────────────────
function nextFriday () {
  const d = new Date()
  const day = d.getDay()
  const daysUntilFriday = (5 - day + 7) % 7 || 7
  d.setDate(d.getDate() + daysUntilFriday)
  return d.toISOString().split('T')[0]   // YYYY-MM-DD
}

function todayStr () {
  return new Date().toISOString().split('T')[0]
}

// ── State ──────────────────────────────────────────────────────
const origin          = ref('LHR')
const destination     = ref('JFK')
const departureDate   = ref(nextFriday())
const selectedTrigger = ref('FUEL_SPIKE')
const rounds          = ref(4)
const triggers        = ref([])
const seed            = ref(null)
const result          = ref(null)
const cascadeResult   = ref(null)
const loading         = ref(false)
const errorMsg        = ref('')
const llmAvailable    = ref(true)
const loadingLabel    = ref('')
const loadingSub      = ref('')
const originErr       = ref(false)
const destErr         = ref(false)
const minDate         = todayStr()

const macro = reactive({ vix: '', wti: '', eur: '', source: '' })

// ── Analysis depth labels ──────────────────────────────────────
const depthLabel = computed(() => {
  if (rounds.value <= 3)  return 'FAST'
  if (rounds.value <= 7)  return 'STANDARD'
  if (rounds.value <= 11) return 'DEEP'
  return 'EXHAUSTIVE'
})

const depthClass = computed(() => {
  if (rounds.value <= 3)  return 'depth-fast'
  if (rounds.value <= 7)  return 'depth-std'
  if (rounds.value <= 11) return 'depth-deep'
  return 'depth-max'
})

const depthDesc = computed(() => {
  if (rounds.value <= 3)
    return `${rounds.value} rounds · agents make initial moves, limited back-and-forth`
  if (rounds.value <= 7)
    return `${rounds.value} rounds · agents react and counter-react, price converges`
  if (rounds.value <= 11)
    return `${rounds.value} rounds · full market equilibration, higher accuracy`
  return `${rounds.value} rounds · maximum agent negotiation — slower but most precise`
})

// Formatted date shown in results
const displayDate = computed(() => {
  if (!departureDate.value) return ''
  const d = new Date(departureDate.value + 'T12:00:00')
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
})

// ── Init ──────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const [trData, health] = await Promise.all([getTriggers(), getHealth()])
    triggers.value = trData.data || []
    llmAvailable.value = health.llm !== false

    if (health.macro_snapshot) {
      Object.assign(macro, health.macro_snapshot)
    }
  } catch (e) {
    console.warn('Init error', e)
  }
})

// ── Validation ─────────────────────────────────────────────────
function validate () {
  originErr.value = !origin.value || origin.value.length !== 3
  destErr.value   = !destination.value || destination.value.length !== 3
  return !originErr.value && !destErr.value && selectedTrigger.value
}

// ── Main action: fetch live data, then run simulation ──────────
async function doSimulate () {
  if (!validate()) return
  errorMsg.value = ''
  result.value = null
  cascadeResult.value = null
  seed.value = null
  loading.value = true

  try {
    // Phase 1: fetch live market data
    loadingLabel.value = 'Fetching live market data...'
    loadingSub.value = 'Google Flights · OpenSky · Yahoo Finance · FX Rates'

    const seedResp = await fetchSeed({
      origin: origin.value,
      destination: destination.value,
      trigger_id: selectedTrigger.value,
      departure_date: departureDate.value,
    })

    if (seedResp.success) {
      seed.value = seedResp.data
      if (seedResp.data.macro) {
        macro.vix    = seedResp.data.macro.vix
        macro.wti    = seedResp.data.macro.wti_price?.toFixed(2)
        macro.eur    = seedResp.data.macro.usd_eur?.toFixed(4)
        macro.source = seedResp.data.macro.source
      }
    }

    // Phase 2: run agent simulation
    loadingLabel.value = 'Running AI simulation...'
    loadingSub.value = `${rounds.value} rounds · 4 agents · Riley Chen · Marcus Webb · Priya Sharma · Sam Park`

    const simResp = await runSimulate({
      origin: origin.value,
      destination: destination.value,
      trigger_id: selectedTrigger.value,
      rounds: rounds.value,
      departure_date: departureDate.value,
    })

    if (simResp.success) {
      result.value = simResp.data
    } else {
      errorMsg.value = simResp.error || 'Simulation failed'
      if (simResp.error?.includes('LLM_API_KEY')) {
        llmAvailable.value = false
        await doCascade()
      }
    }
  } catch (e) {
    errorMsg.value = e.response?.data?.error || e.message
    if (errorMsg.value?.includes('LLM_API_KEY')) {
      llmAvailable.value = false
      await doCascade()
    }
  } finally {
    loading.value = false
    loadingLabel.value = ''
    loadingSub.value = ''
  }
}

async function doCascade () {
  try {
    const r = await runCascade({ trigger_id: selectedTrigger.value })
    if (r.success) cascadeResult.value = r.data
  } catch {}
}

// ── Helpers ───────────────────────────────────────────────────
function setRoute (str) {
  const parts = str.split('→')
  origin.value = parts[0]
  destination.value = parts[1]
}

function tickClass (val, warn, critical) {
  const n = parseFloat(val)
  if (n >= critical) return 'crisis'
  if (n >= warn) return 'stressed'
  return ''
}

function decisionClass (d) {
  if (d === 'raise_fares')        return 'dec-raise'
  if (d === 'drop_fares')         return 'dec-drop'
  if (d === 'delay_booking')      return 'dec-delay'
  if (d === 'shift_carrier')      return 'dec-shift'
  if (d === 'accelerate_booking') return 'dec-accel'
  return 'dec-hold'
}

function friendlyDecision (d) {
  const map = {
    raise_fares:        'Raised fares',
    hold_fares:         'Held fares',
    drop_fares:         'Dropped fares',
    delay_booking:      'Delayed booking',
    accelerate_booking: 'Booked now',
    shift_carrier:      'Switched carrier',
  }
  return map[d] || d.replace(/_/g, ' ')
}

function shortRole (id) {
  const m = {
    lcc_rm:           'LCC RM',
    legacy_rm:        'LEGACY',
    corporate_buyer:  'CORP',
    leisure_traveler: 'LEISURE',
  }
  return m[id] || id
}

function renderMarkdown (md) {
  if (!md) return ''
  return md
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm,  '<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>')
}
</script>

<style scoped>
/* ── Layout ──────────────────────────────────────────────────── */
.sim-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ── Header ──────────────────────────────────────────────────── */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(10, 10, 10, 0.95);
  backdrop-filter: blur(8px);
  position: relative;
  z-index: 10;
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-weight: 800;
  font-size: 15px;
  letter-spacing: 2px;
  color: var(--acc);
}
.brand-icon { font-size: 13px; }
.brand-sub  { font-size: 10px; font-weight: 400; letter-spacing: 1px; color: var(--txt-dim); margin-left: 4px; }

.macro-ticker {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: var(--txt-dim);
}
.tick strong { color: var(--txt); font-weight: 600; }
.tick.stressed strong { color: var(--warn); }
.tick.crisis strong   { color: var(--neg); }
.tick-sep { color: var(--border-2); }
.tick-source { font-size: 9px; letter-spacing: 1px; padding: 1px 5px; border-radius: 2px; }
.tick-source.live  { color: var(--pos); border: 1px solid rgba(0,230,118,0.3); }
.tick-source.stale { color: var(--warn); border: 1px solid var(--warn-dim); }

.header-actions { display: flex; align-items: center; }
.back-link {
  font-size: 11px;
  color: var(--txt-dim);
  text-decoration: none;
  letter-spacing: 0.5px;
  transition: color 0.2s;
}
.back-link:hover { color: var(--acc); }

/* ── Controls (left panel) ───────────────────────────────────── */
.controls {
  width: 300px;
  min-width: 280px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
  padding: 0 0 24px;
}

.ctrl-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.section-label {
  font-size: 9px;
  letter-spacing: 2px;
  color: var(--txt-dim);
  margin-bottom: 10px;
  font-weight: 600;
}

/* Route inputs */
.route-inputs {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  margin-bottom: 12px;
}
.iata-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.iata-field label {
  font-size: 9px;
  letter-spacing: 1.5px;
  color: var(--txt-dim);
}
.iata-field input {
  background: var(--surface-2);
  border: 1px solid var(--border-2);
  color: var(--txt);
  padding: 8px 10px;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
  border-radius: var(--radius);
  text-transform: uppercase;
  width: 100%;
  outline: none;
  transition: border-color 0.2s;
}
.iata-field input:focus { border-color: var(--acc); }
.iata-field input.error { border-color: var(--neg); }
.field-err { font-size: 9px; color: var(--neg); }
.route-arrow { color: var(--txt-dim); font-size: 14px; padding-bottom: 10px; }

/* Date field */
.date-field { display: flex; flex-direction: column; gap: 4px; }
.date-label {
  font-size: 9px;
  letter-spacing: 1.5px;
  color: var(--txt-dim);
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.date-hint { font-size: 8.5px; color: var(--txt-faint); letter-spacing: 0.5px; text-transform: none; }
.date-input {
  background: var(--surface-2);
  border: 1px solid var(--border-2);
  color: var(--txt);
  padding: 7px 10px;
  font-size: 12px;
  font-family: var(--mono);
  letter-spacing: 0.5px;
  border-radius: var(--radius);
  width: 100%;
  outline: none;
  transition: border-color 0.2s;
  color-scheme: dark;
}
.date-input:focus { border-color: var(--acc); }

/* Trigger grid */
.trigger-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.trigger-btn {
  background: var(--surface-2);
  border: 1px solid var(--border-2);
  color: var(--txt-dim);
  padding: 8px 6px;
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-family: var(--mono);
  letter-spacing: 0.5px;
  transition: all 0.15s;
  cursor: pointer;
}
.trigger-btn:hover { color: var(--txt); }
.trigger-btn.active {
  border-color: var(--acc);
  color: var(--acc);
  background: var(--acc-dim);
}
.trigger-icon { font-size: 15px; }
.trigger-label { font-size: 9px; letter-spacing: 0.5px; text-align: center; }

/* Analysis depth */
.depth-section { padding-bottom: 14px; }
.rounds-control { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.rounds-btn {
  width: 26px; height: 26px;
  background: var(--surface-2);
  border: 1px solid var(--border-2);
  color: var(--txt);
  border-radius: var(--radius);
  font-size: 14px;
  display: flex; align-items: center; justify-content: center;
  transition: border-color 0.15s;
  cursor: pointer;
}
.rounds-btn:hover { border-color: var(--acc); color: var(--acc); }
.rounds-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--acc);
  min-width: 24px;
  text-align: center;
}
.depth-badge {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1.5px;
  padding: 2px 8px;
  border-radius: 2px;
  margin-left: 4px;
}
.depth-fast { color: var(--pos); background: rgba(0,230,118,0.12); border: 1px solid rgba(0,230,118,0.3); }
.depth-std  { color: var(--acc); background: var(--acc-dim); border: 1px solid rgba(0,172,193,0.3); }
.depth-deep { color: var(--warn); background: rgba(255,145,0,0.1); border: 1px solid rgba(255,145,0,0.3); }
.depth-max  { color: var(--neg); background: rgba(255,59,48,0.1); border: 1px solid rgba(255,59,48,0.3); }
.depth-desc { font-size: 10px; color: var(--txt-faint); line-height: 1.5; }

/* Seed grid */
.seed-grid { display: flex; flex-direction: column; gap: 6px; }
.seed-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.seed-key { color: var(--txt-dim); min-width: 80px; font-size: 9px; letter-spacing: 1px; }
.seed-val { color: var(--txt); flex: 1; font-weight: 600; }
.seed-val.acc { color: var(--acc); }
.seed-src { font-size: 9px; padding: 1px 5px; border-radius: 2px; color: var(--pos); border: 1px solid rgba(0,230,118,0.25); }

/* Action row */
.action-row {
  padding: 16px 20px 0;
  display: flex;
  gap: 8px;
}
.btn-primary {
  flex: 1;
  padding: 11px 0;
  border-radius: var(--radius);
  font-size: 11px;
  font-family: var(--mono);
  font-weight: 700;
  letter-spacing: 1px;
  border: 1px solid var(--acc);
  background: var(--acc);
  color: #000;
  transition: all 0.15s;
  white-space: nowrap;
  cursor: pointer;
}
.btn-primary:hover:not(:disabled) { background: #00cdd9; border-color: #00cdd9; }
.btn-primary:disabled { opacity: 0.35; cursor: not-allowed; }

.llm-warning {
  margin: 10px 20px 0;
  font-size: 10px;
  color: var(--warn);
  border: 1px solid var(--warn-dim);
  padding: 8px 10px;
  border-radius: var(--radius);
  line-height: 1.4;
}
.error-box {
  margin: 10px 20px 0;
  font-size: 11px;
  color: var(--neg);
  border: 1px solid rgba(255,59,48,0.3);
  padding: 8px 10px;
  border-radius: var(--radius);
}

/* ── Results panel ───────────────────────────────────────────── */
.results {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  gap: 12px;
  color: var(--txt-dim);
  padding: 40px;
}
.empty-icon  { font-size: 40px; opacity: 0.2; }
.empty-title { font-size: 14px; font-weight: 600; color: var(--txt); }
.empty-desc  { font-size: 12px; max-width: 300px; line-height: 1.65; }
.empty-desc strong { color: var(--acc); }
.empty-routes { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 8px; }
.sample-route {
  font-size: 11px;
  color: var(--acc);
  border: 1px solid var(--acc-dim);
  padding: 4px 10px;
  border-radius: 2px;
  cursor: pointer;
  transition: background 0.15s;
}
.sample-route:hover { background: var(--acc-dim); }

/* Loading state */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 14px;
  color: var(--txt-dim);
}
.spinner {
  width: 36px; height: 36px;
  border: 2px solid var(--border-2);
  border-top-color: var(--acc);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-label { font-size: 13px; font-weight: 600; color: var(--txt); letter-spacing: 0.5px; }
.loading-sub   { font-size: 10px; color: var(--txt-dim); text-align: center; max-width: 280px; line-height: 1.5; }

/* Result blocks */
.result-block {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
}
.block-title { font-size: 9px; letter-spacing: 2px; font-weight: 700; color: var(--txt-dim); }
.block-tag {
  font-size: 9px;
  padding: 2px 8px;
  background: var(--surface-2);
  border-radius: 2px;
  color: var(--acc);
  letter-spacing: 1px;
}

/* Fare card */
.fare-card { padding: 0; }
.fare-route { padding: 12px 16px 0; font-size: 12px; color: var(--txt-dim); letter-spacing: 1px; }
.fare-row {
  display: flex;
  align-items: center;
  padding: 12px 16px 16px;
  gap: 16px;
}
.fare-col { display: flex; flex-direction: column; gap: 2px; }
.fare-col.right { margin-left: auto; text-align: right; }
.fare-lbl { font-size: 9px; letter-spacing: 1.5px; color: var(--txt-dim); }
.fare-val { font-size: 28px; font-weight: 800; color: var(--txt); }
.fare-val.pos { color: var(--pos); }
.fare-val.neg { color: var(--neg); }
.fare-arrow { font-size: 20px; color: var(--txt-dim); }
.fare-arrow.pos { color: var(--pos); }
.fare-arrow.neg { color: var(--neg); }
.fare-delta { font-size: 24px; font-weight: 800; }
.fare-delta.pos { color: var(--pos); }
.fare-delta.neg { color: var(--neg); }
.fare-consensus { font-size: 11px; color: var(--acc); text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }
.fare-conf { font-size: 10px; color: var(--txt-dim); }

/* CascadeChart padding */
.result-block :deep(.cascade-chart) { padding: 12px 16px 8px; }
.cascade-note { padding: 8px 16px 12px; font-size: 10px; color: var(--warn); }

/* Timeline legend */
.timeline-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
}
.leg { font-size: 9px; letter-spacing: 0.5px; color: var(--txt-faint); }
.leg.raise { color: var(--pos); }
.leg.drop  { color: var(--neg); }
.leg.accel { color: var(--acc); }
.leg.delay { color: var(--warn); }

/* Agent timeline */
.timeline { display: flex; flex-direction: column; }
.timeline-row {
  display: grid;
  grid-template-columns: 26px 60px 54px 110px 46px 1fr;
  gap: 6px;
  align-items: center;
  padding: 6px 16px;
  border-bottom: 1px solid var(--border);
  font-size: 10px;
}
.timeline-row:last-child { border-bottom: none; }
.timeline-row.dec-raise  { border-left: 2px solid var(--pos); }
.timeline-row.dec-drop   { border-left: 2px solid var(--neg); }
.timeline-row.dec-delay  { border-left: 2px solid var(--warn); }
.timeline-row.dec-shift  { border-left: 2px solid var(--warn); }
.timeline-row.dec-accel  { border-left: 2px solid var(--acc); }
.timeline-row.dec-hold   { border-left: 2px solid var(--border-2); }

.tl-round  { color: var(--txt-dim); font-size: 9px; }
.tl-agent  { color: var(--txt); font-weight: 600; }
.tl-role   { color: var(--txt-dim); font-size: 9px; letter-spacing: 0.5px; }
.tl-decision { color: var(--txt); }
.tl-mag    { font-weight: 700; font-size: 11px; }
.tl-mag.pos { color: var(--pos); }
.tl-mag.neg { color: var(--neg); }
.tl-reason { color: var(--txt-dim); font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Narrative */
.narrative {
  padding: 16px;
  line-height: 1.7;
  font-size: 12px;
  color: var(--txt-dim);
}
.narrative :deep(h3) {
  font-size: 11px;
  letter-spacing: 1.5px;
  color: var(--acc);
  margin: 14px 0 6px;
  font-weight: 700;
}
.narrative :deep(p) { margin-bottom: 8px; }
.narrative :deep(strong) { color: var(--txt); font-weight: 600; }

/* Sources */
.sources-block { padding: 12px 16px; }
.sources-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.source-chip {
  font-size: 9px;
  padding: 2px 8px;
  border-radius: 2px;
  letter-spacing: 0.5px;
}
.source-chip.serpapi, .source-chip.live, .source-chip.opensky {
  color: var(--pos);
  border: 1px solid rgba(0, 230, 118, 0.25);
}
.source-chip.synthetic, .source-chip.partial {
  color: var(--txt-dim);
  border: 1px solid var(--border-2);
}

/* Responsive */
@media (max-width: 700px) {
  .controls { width: 100%; min-width: unset; }
  .body { flex-direction: column; }
  .macro-ticker { display: none; }
  .results { padding: 12px; }
  .timeline-row { grid-template-columns: 26px 56px 48px 1fr; }
  .tl-mag, .tl-reason { display: none; }
}
</style>
