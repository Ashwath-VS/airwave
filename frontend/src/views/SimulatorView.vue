<template>
  <div class="aw">

    <!-- ── Nav ──────────────────────────────────────────────────────── -->
    <nav class="aw-nav">
      <div class="aw-nav-inner">
        <!-- Brand -->
        <div class="aw-brand">
          <div class="aw-brand-stack">
            <span class="aw-brand-name">MIROFISH</span>
            <span class="aw-brand-product">AIRWAVE</span>
          </div>
          <span class="aw-brand-div">·</span>
          <span class="aw-brand-sub">FARE SCENARIO INTELLIGENCE</span>
        </div>

        <!-- Status -->
        <div class="nav-pills">
          <span class="nav-pill"><span class="mf-sq">◇</span> 8 market agents</span>
          <span class="nav-pill nav-pill-live">
            <span class="live-dot"></span>
            LIVE DATA
          </span>
          <button v-if="simHistory.length" class="nav-pill nav-pill-hist" @click="showHistory=true">
            ▷ HISTORY ({{ simHistory.length }})
          </button>
          <button class="nav-pill nav-pill-method" @click="showMethodology=true" title="How AirWave works">? METHOD</button>
          <span class="nav-byline">BY S·ASHWATH</span>
        </div>
      </div>
    </nav>

    <main class="aw-main">

      <!-- ── Search card ──────────────────────────────────────────── -->
      <section class="aw-search">

        <!-- Trip type -->
        <div class="trip-row">
          <button :class="['tt-btn', tripType==='one_way' && 'tt-active']"
            @click="tripType='one_way'; returnDate=''">One-way</button>
          <button :class="['tt-btn', tripType==='round_trip' && 'tt-active']"
            @click="tripType='round_trip'">Round-trip</button>
        </div>

        <!-- Route + dates + cabin -->
        <div class="fields-row">
          <div class="field-group">
            <label class="fl">From</label>
            <input v-model="origin" class="fi fi-code" placeholder="LHR"
              maxlength="3"
              @input="origin=origin.replace(/[^A-Za-z]/g,'').toUpperCase()"
              spellcheck="false"
              :class="showValidation && origin.length===3 && !originName ? 'fi-warn' : ''" />
            <span v-if="originName" class="fhint">{{ originName }}</span>
            <span v-else-if="origin.length===3" class="fhint fhint-warn">Unrecognised IATA — verify</span>
          </div>

          <button class="swap-btn" @click="swapRoutes" title="Swap">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"/>
            </svg>
          </button>

          <div class="field-group">
            <label class="fl">To</label>
            <input v-model="destination" class="fi fi-code" placeholder="JFK"
              maxlength="3"
              @input="destination=destination.replace(/[^A-Za-z]/g,'').toUpperCase()"
              spellcheck="false"
              :class="showValidation && destination.length===3 && !destName ? 'fi-warn' : ''" />
            <span v-if="destName" class="fhint">{{ destName }}</span>
            <span v-else-if="destination.length===3" class="fhint fhint-warn">Unrecognised IATA — verify</span>
          </div>

          <div class="field-group">
            <label class="fl">Travel window</label>
            <div class="horizon-tabs">
              <button v-for="h in horizons" :key="h.key"
                :class="['hz-btn', horizon===h.key && 'hz-active']"
                @click="setHorizon(h.key)">{{ h.label }}</button>
            </div>
            <input v-if="horizon==='custom'" v-model="departureDate"
              class="fi fi-horizon-custom" type="date" :min="today"
              :class="showValidation && !departureDate ? 'fi-err' : ''" />
            <span v-else class="fhint">≈ {{ horizonDateLabel }}</span>
            <span v-if="showValidation && !departureDate" class="fhint fhint-err">Required</span>
          </div>

          <div v-if="tripType==='round_trip'" class="field-group">
            <label class="fl">Return <span class="fl-req">*</span></label>
            <input v-model="returnDate" class="fi" type="date" :min="departureDate||today"
              :class="showValidation && !returnDate ? 'fi-err' : ''" />
            <span v-if="showValidation && !returnDate" class="fhint fhint-err">Required</span>
          </div>

          <div class="field-group">
            <label class="fl">Cabin</label>
            <select v-model="cabinClass" class="fi">
              <option :value="1">Economy</option>
              <option :value="2">Prem. Economy</option>
              <option :value="3">Business</option>
              <option :value="4">First</option>
            </select>
          </div>
        </div>

        <!-- Market shocks multi-select -->
        <div class="shock-section">
          <div class="shock-label-row">
            <span class="shock-label">Market shock to model</span>
            <span class="shock-hint">Pick the event — agents reason under these conditions. Select multiple to stack shocks. Hover any trigger for data source and methodology.</span>
          </div>
          <div class="shock-pills">
            <div v-for="t in triggers" :key="t.id" class="shock-pill-wrap"
              @mouseenter="hoveredTrigger=t.id" @mouseleave="hoveredTrigger=null">
              <button :class="['shock-pill', selectedShocks.includes(t.id) && 'shock-active']"
                @click="toggleShock(t.id)">
                <span class="sp-icon">{{ t.icon }}</span>
                {{ t.label }}
                <span v-if="selectedShocks.includes(t.id)" class="sp-check">✓</span>
              </button>
              <!-- Per-pill tooltip -->
              <Transition name="sbt-fade">
                <div v-if="hoveredTrigger===t.id" class="sp-tooltip">
                  <div class="spt-head">
                    <span class="spt-icon">{{ t.icon }}</span>
                    <span class="spt-label">{{ t.label }}</span>
                  </div>
                  <p class="spt-explain">{{ t.explain }}</p>
                  <div class="spt-source">
                    <span class="spt-src-badge">📡 Data source</span>
                    <span class="spt-src-text">{{ triggerSources[t.id] }}</span>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
          <span v-if="selectedShocks.length===0" class="shock-warn">Select at least one scenario</span>
        </div>

        <!-- Compare toggle -->
        <div class="cmp-toggle-row">
          <button :class="['cmp-toggle-btn', compareMode && 'cmp-toggle-active']"
            @click="compareMode=!compareMode; if(!compareMode){result2=null; selectedShocks2=[]}; if(compareMode && selectedShocks2.length===0){ const fallback = triggers.find(t=>t.id!=='NEWS_FEED' && !selectedShocks.includes(t.id)); if(fallback) selectedShocks2=[fallback.id] }">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="18"/><rect x="14" y="3" width="7" height="18"/>
            </svg>
            {{ compareMode ? 'Exit comparison mode' : '+ Compare two scenarios' }}
          </button>
          <span v-if="compareMode" class="cmp-toggle-hint">Scenario A uses the shock above · pick Scenario B below</span>
        </div>

        <!-- Scenario B shocks (compare mode) -->
        <div v-if="compareMode" class="shock-section shock-section-b">
          <div class="shock-label-row">
            <span class="shock-label">
              <span class="scn-badge scn-b">B</span>
              Scenario B shocks
            </span>
            <span class="shock-hint">Select one or more shocks to compare against Scenario A</span>
          </div>
          <div class="shock-pills">
            <div v-for="t in triggers" :key="`b-${t.id}`" class="shock-pill-wrap"
              @mouseenter="hoveredTrigger2=t.id" @mouseleave="hoveredTrigger2=null">
              <button :class="['shock-pill', 'shock-pill-b', selectedShocks2.includes(t.id) && 'shock-active-b']"
                @click="toggleShock2(t.id)">
                <span class="sp-icon">{{ t.icon }}</span>
                {{ t.label }}
                <span v-if="selectedShocks2.includes(t.id)" class="sp-check">✓</span>
              </button>
              <Transition name="sbt-fade">
                <div v-if="hoveredTrigger2===t.id" class="sp-tooltip">
                  <div class="spt-head">
                    <span class="spt-icon">{{ t.icon }}</span>
                    <span class="spt-label">{{ t.label }}</span>
                  </div>
                  <p class="spt-explain">{{ t.explain }}</p>
                </div>
              </Transition>
            </div>
          </div>
          <span v-if="compareMode && selectedShocks2.length===0" class="shock-warn">Select at least one Scenario B shock</span>
          <span v-if="sameShocksWarning" class="shock-warn shock-warn-dupe">
            ⚠ Scenario A and B have the same shocks — select different triggers to get a meaningful comparison
          </span>
        </div>

        <!-- News Feed panel — always below all shock sections so Scenario B NEWS_FEED is reachable -->
        <div v-if="selectedShocks.includes('NEWS_FEED') || selectedShocks2.includes('NEWS_FEED')" class="news-panel">
          <div class="news-panel-hd">
            <span class="news-hd-icon">📰</span>
            <div>
              <div class="news-hd-title">
                Select news events to inject as agent context
                <span v-if="newsLoading" class="news-loading-badge">fetching<span class="btn-cursor">_</span></span>
              </div>
              <div class="news-hd-sub">
                {{ newsFetchedRoute
                  ? `🏛 Geopolitical · 🌪 Weather · ✈️ Aviation — ${origin} &amp; ${destination} geography`
                  : 'Enter a valid route above to load relevant headlines' }}
                <span v-if="selectedNews.length > 0"> · <strong>{{ selectedNews.length }} selected</strong> — agents will reason against these headlines</span>
              </div>
            </div>
            <div v-if="newsFetchedRoute" class="news-hd-actions">
              <button class="news-action-btn"
                @click="selectedNews = selectedNews.length === newsItems.length ? [] : newsItems.map((_,i)=>i)">
                {{ selectedNews.length === newsItems.length ? 'Clear all' : 'Select all' }}
              </button>
              <button class="news-refresh-btn" @click="newsFetchedRoute=''; newsItems=[]; selectedNews=[]; fetchNewsForRoute()" title="Refresh">↺</button>
            </div>
          </div>

          <!-- Error state -->
          <div v-if="newsError" class="news-error">⚠ {{ newsError }}</div>

          <!-- Loading skeleton -->
          <div v-else-if="newsLoading" class="news-skeleton-list">
            <div v-for="i in 6" :key="i" class="news-skeleton-item">
              <div class="nsk-line nsk-title"></div>
              <div class="nsk-line nsk-meta"></div>
            </div>
          </div>

          <!-- News items -->
          <div v-else-if="newsItems.length > 0" class="news-items-list">
            <div v-for="(item, idx) in newsItems" :key="idx"
              :class="['news-item', selectedNews.includes(idx) && 'news-item-sel']"
              @click="toggleNewsItem(idx)">
              <div class="ni-check">
                <span v-if="selectedNews.includes(idx)" class="ni-checked">✓</span>
                <span v-else class="ni-unchecked"></span>
              </div>
              <div class="ni-body">
                <div class="ni-title">{{ item.title }}</div>
                <div class="ni-meta">
                  <span v-if="item.category_icon" class="ni-cat-icon" :title="item.category_label">{{ item.category_icon }}</span>
                  <span v-if="item.category_label" :class="['ni-cat', `ni-cat-${item.category}`]">{{ item.category_label }}</span>
                  <span v-if="item.geo" :class="['ni-geo', item.geo==='origin'?'ni-geo-o':'ni-geo-d']">
                    {{ item.geo === 'origin' ? origin : destination }}
                  </span>
                  <span class="ni-source">{{ item.source }}</span>
                  <span v-if="item.date" class="ni-date">{{ item.date }}</span>
                </div>
                <p v-if="item.snippet && selectedNews.includes(idx)" class="ni-snippet">{{ item.snippet }}</p>
              </div>
            </div>
          </div>

          <!-- Empty state -->
          <div v-else-if="!newsLoading && newsFetchedRoute" class="news-empty">
            No headlines found for this route geography. The NEWS_FEED cascade impact will still apply.
          </div>
        </div>

        <!-- Depth + predict button -->
        <div class="action-row">
          <div class="field-group">
            <label class="fl">Analysis depth</label>
            <div class="depth-tabs">
              <button v-for="d in depths" :key="d.key"
                :class="['dt-btn', depth===d.key && 'dt-active']"
                @click="depth=d.key">
                {{ d.label }}
                <span class="dt-hint">{{ d.hint }}</span>
              </button>
            </div>
          </div>

          <button class="predict-btn" :disabled="isLoading || sameShocksWarning" @click="handlePredict">
            <template v-if="!isLoading">
              {{ compareMode ? 'RUN COMPARISON' : 'RUN SCENARIO' }}
              <span class="btn-arrow">→</span>
            </template>
            <template v-else>
              <span class="btn-running">RUNNING<span class="btn-cursor">_</span></span>
              <span class="btn-arrow">→</span>
            </template>
          </button>
        </div>
      </section>

      <!-- ── Error ──────────────────────────────────────────────────── -->
      <div v-if="error" class="aw-error">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <strong>Could not complete simulation</strong>
          <p>{{ error }}</p>
        </div>
        <button class="err-close" @click="error=''">✕</button>
      </div>

      <!-- ── Loading panel ──────────────────────────────────────────── -->
      <div v-if="isLoading" class="aw-loading">
        <div class="lp-terminal">
          <div class="lp-term-header">
            <span class="lp-term-dot lp-td-r"></span>
            <span class="lp-term-dot lp-td-y"></span>
            <span class="lp-term-dot lp-td-g"></span>
            <span class="lp-term-title">airwave — scenario engine</span>
          </div>
          <div class="lp-term-body">
            <p class="lp-cmd">$ airwave simulate --route {{ origin }}-{{ destination }} --mode {{ depth }}<span class="lp-cursor">_</span></p>
            <p class="lp-log">› Seeding live market data...</p>
            <p class="lp-log lp-log-active">› {{ loadingMsg }}<span class="lp-cursor">_</span></p>
            <p class="lp-eta-line">ETA {{ depthEta }} · eight agents running · keep this tab open</p>
          </div>
        </div>
      </div>

      <!-- ── Results ────────────────────────────────────────────────── -->
      <!-- Single-scenario view: only shows when NOT in a completed comparison -->
      <div v-if="result && !(compareMode && result2)" class="aw-results">

        <!-- Synthetic data warning -->
        <div v-if="result.data_sources?.fare === 'synthetic' || result.data_sources?.demand === 'synthetic'"
          class="aw-synthetic-warn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <div>
            <strong>{{ result.data_sources?.fare === 'synthetic' ? 'No live pricing found for this route' : 'Route demand estimated' }}</strong>
            <p v-if="result.data_sources?.fare === 'synthetic'">
              Fare data is estimated from a statistical baseline — not a real ticket price. The scenario modelling is indicative only. For actionable intelligence, use a major airline route with NDC distribution.
            </p>
            <p v-else>
              Live flight frequency data (OpenSky) is unavailable for this route pair — demand index is estimated. Fare seed and agent reasoning remain live-anchored. Results are directionally valid but treat demand-driven signals with caution.
            </p>
          </div>
        </div>

        <!-- Prediction header band -->
        <div class="pred-band" :class="`cs-${result.agent_consensus}`">
          <div class="pb-left">
            <span class="pb-route">{{ result.route }}</span>
            <span class="pb-sim">{{ result.simulation_id }}</span>
          </div>
          <div class="pb-center">
            <div class="pb-fares">
              <div class="pb-fare-item">
                <span class="pb-fare-lbl">Live fare · {{ result.fare_details?.trip_type==='round_trip' ? 'round-trip' : 'one-way' }}</span>
                <span class="pb-fare-val">${{ result.seed_fare.toLocaleString() }}</span>
              </div>
              <div class="pb-arrow" :class="result.fare_delta>=0?'arr-up':'arr-dn'">
                <svg width="28" height="12" viewBox="0 0 40 14" fill="none">
                  <path d="M0 7h32M26 1l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </div>
              <div class="pb-fare-item">
                <span class="pb-fare-lbl">Simulated forecast</span>
                <span class="pb-fare-val pb-pred">${{ result.predicted_fare.toLocaleString() }}</span>
              </div>
            </div>
          </div>
          <div class="pb-right">
            <span :class="['delta-chip', result.fare_delta>=0?'dc-up':'dc-dn']">
              {{ result.fare_delta>=0?'▲':'▼' }} {{ Math.abs(result.fare_delta_pct) }}%
            </span>
            <span class="consensus-lbl">{{ consensusLabel }}</span>
            <div class="conf-bar-wrap">
              <span class="conf-bar-lbl">Confidence</span>
              <div class="conf-bar"><div class="conf-fill" :style="{width:`${result.confidence*100}%`}"></div></div>
              <span class="conf-pct">{{ Math.round(result.confidence*100) }}%</span>
            </div>
          </div>
        </div>

        <!-- Shock explain banner -->
        <div v-if="shockBannerItems.length" class="shock-banner">
          <div class="sb-header">
            <span class="sb-bulb">💡</span>
            <span class="sb-title" v-if="shockBannerItems.length===1">
              {{ shockBannerItems[0].icon }} {{ shockBannerItems[0].label }}
            </span>
            <span class="sb-title" v-else>
              {{ shockBannerItems.length }} market shocks selected
            </span>
          </div>
          <!-- Single trigger: show explanation inline -->
          <p v-if="shockBannerItems.length===1" class="sb-explain">
            {{ shockBannerItems[0].explain }}
          </p>
          <!-- Multiple triggers: chips with hover tooltips -->
          <div v-else class="sb-chips">
            <div v-for="item in shockBannerItems" :key="item.id"
              class="sb-chip"
              @mouseenter="hoveredShock=item.id"
              @mouseleave="hoveredShock=null">
              <span class="sb-chip-icon">{{ item.icon }}</span>
              <span class="sb-chip-label">{{ item.label }}</span>
              <Transition name="sbt-fade">
                <div v-if="hoveredShock===item.id" class="sb-tooltip">
                  {{ item.explain }}
                </div>
              </Transition>
            </div>
          </div>
        </div>

        <div class="results-body">

          <!-- LEFT column -->
          <div class="col-l">

            <!-- Flight card -->
            <div class="flight-card">
              <div class="fc-top">
                <div class="fc-route">
                  <span class="fc-code">{{ result.route.split(' → ')[0] }}</span>
                  <svg width="30" height="12" viewBox="0 0 40 14" fill="none" class="fc-arrow">
                    <path d="M0 7h34M28 1l6 6-6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    <circle cx="4" cy="7" r="2.5" fill="currentColor"/>
                  </svg>
                  <span class="fc-code">{{ result.route.split(' → ')[1] }}</span>
                </div>
                <span :class="['trip-badge', result.fare_details?.trip_type==='round_trip'?'tb-rt':'tb-ow']">
                  {{ result.fare_details?.trip_type==='round_trip'?'Round-trip':'One-way' }}
                </span>
              </div>

              <div class="fc-body">
                <!-- Airline -->
                <div class="airline-col">
                  <div class="logo-box">
                    <img v-if="result.fare_details?.airline_logo && !logoFailed"
                      :src="result.fare_details.airline_logo"
                      :alt="result.fare_details.airline_name"
                      class="al-img"
                      @error="logoFailed=true" />
                    <div v-else class="al-fallback">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--ink3)" stroke-width="1.5">
                        <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21 4 19.5 2.5c-1.5-1.5-3.5-1.5-5 0L11 6 2.8 4.2c-.5-.1-.9.1-1.1.5L.3 8.3c-.3.6-.1 1.3.5 1.5L9 12l-3.5 3.5c-.5.5-.5 1.5 0 2s1.5.5 2 0L11 14l3.2 8.2c.2.6.9.8 1.5.5l3.6-1.4c.4-.2.6-.6.5-1.1Z"/>
                      </svg>
                    </div>
                  </div>
                  <span class="al-name">{{ result.fare_details?.airline_name||'Best Available' }}</span>
                  <span v-if="result.fare_details?.flight_number" class="al-fno">{{ result.fare_details.flight_number }}</span>
                </div>

                <!-- Times & duration -->
                <div class="times-col">
                  <div class="t-blk">
                    <span class="t-time">{{ result.fare_details?.departure_time||'—' }}</span>
                    <span class="t-iata t-ac">{{ result.route.split(' → ')[0] }}</span>
                    <span class="t-apt">{{ trunc(result.fare_details?.origin_airport_name,22) }}</span>
                    <span class="t-date">{{ fmtDate(result.fare_details?.departure_date) }}</span>
                  </div>
                  <div class="dur-blk">
                    <span class="dur-line"></span>
                    <span class="dur-txt">{{ fmtDur(result.fare_details?.duration_min) }}</span>
                    <span :class="['stops-pill', result.fare_details?.is_direct?'sp-direct':'sp-stops']">
                      {{ result.fare_details?.is_direct?'Nonstop':`${result.fare_details?.num_stops} stop${result.fare_details?.num_stops>1?'s':''}` }}
                    </span>
                  </div>
                  <div class="t-blk t-right">
                    <span class="t-time">
                      {{ result.fare_details?.arrival_time||'—' }}
                      <sup v-if="result.fare_details?.arrives_next_day" class="nd">+1</sup>
                    </span>
                    <span class="t-iata t-ac">{{ result.route.split(' → ')[1] }}</span>
                    <span class="t-apt">{{ trunc(result.fare_details?.dest_airport_name,22) }}</span>
                  </div>
                </div>

                <!-- Fare + cabin -->
                <div class="fare-blk">
                  <span class="fare-lbl">{{ result.fare_details?.trip_type==='round_trip' ? 'Round-trip fare' : 'One-way fare' }}</span>
                  <span class="fare-val">${{ result.seed_fare.toLocaleString() }}</span>
                  <span class="cabin-pill">{{ cabinLabel }}</span>
                </div>
              </div>
            </div>

            <!-- Historical Baseline (Travelpayouts / estimated) -->
            <!-- hide when source is 'synthetic' — means both Travelpayouts and live fare failed -->
            <div v-if="result.history && result.history.source !== 'synthetic'" class="hist-baseline">
              <div class="hb-header">
                <span class="hb-icon">📅</span>
                <span class="hb-title">Historical Baseline</span>
                <span v-if="result.history.source === 'travelpayouts'" class="hb-src hb-live">Travelpayouts live</span>
                <span v-else-if="result.history.source === 'estimated'" class="hb-src hb-est"
                  title="Estimated from live fare — connect Travelpayouts for real historical data">
                  Estimated
                </span>
              </div>
              <div class="hb-metrics">
                <div class="hb-metric">
                  <span class="hb-lbl">Avg baseline fare</span>
                  <span class="hb-val">${{ Math.round(result.history.baseline_price_usd).toLocaleString() }}</span>
                </div>
                <div class="hb-metric">
                  <span class="hb-lbl">Monthly avg</span>
                  <span class="hb-val">${{ Math.round(result.history.month_avg).toLocaleString() }}</span>
                </div>
                <div class="hb-metric">
                  <span class="hb-lbl">Fare vs monthly avg</span>
                  <span :class="['hb-trend', result.history.price_trend>=0?'hbt-up':'hbt-dn']">
                    {{ result.history.price_trend >= 0 ? '▲' : '▼' }}
                    {{ Math.abs(Math.round(result.history.price_trend * 100)) }}%
                    {{ result.history.price_trend >= 0 ? 'above' : 'below' }} avg
                  </span>
                </div>
                <div class="hb-metric">
                  <span class="hb-lbl">Today vs baseline</span>
                  <span :class="['hb-trend', result.seed_fare > result.history.baseline_price_usd ? 'hbt-up' : 'hbt-dn']">
                    {{ result.seed_fare > result.history.baseline_price_usd ? '▲' : '▼' }}
                    {{ Math.abs(Math.round((result.seed_fare / result.history.baseline_price_usd - 1) * 100)) }}%
                    {{ result.seed_fare > result.history.baseline_price_usd ? 'above' : 'below' }} baseline
                  </span>
                </div>
              </div>
              <p v-if="result.history.source === 'estimated'" class="hb-note">
                ⓘ Baseline estimated from live fare range. Connect Travelpayouts API for real 12-month historical data.
              </p>
            </div>

            <!-- Alternative flights -->
            <div v-if="result.available_flights?.length>1" class="alt-flights">
              <p class="alt-title">Other flights on this route <span class="alt-title-hint">Hover for details</span></p>
              <div v-for="(f,i) in result.available_flights.slice(1,4)" :key="i"
                class="alt-row"
                @mouseenter="hoveredAlt=i"
                @mouseleave="hoveredAlt=null">
                <!-- Hover tooltip card -->
                <Transition name="tooltip-fade">
                  <div v-if="hoveredAlt===i" class="alt-tooltip">
                    <div class="at-header">
                      <div class="at-logo-box">
                        <img v-if="f.airline_logo" :src="f.airline_logo" :alt="f.airline_name"
                          class="at-logo" @error="e=>e.target.style.display='none'" />
                        <span v-else class="at-logo-fb">✈</span>
                      </div>
                      <div class="at-airline-info">
                        <span class="at-name">{{ f.airline_name||'Airline' }}</span>
                        <span v-if="f.flight_number" class="at-fnum">{{ f.flight_number }}</span>
                      </div>
                    </div>
                    <div class="at-times-row">
                      <div class="at-time-blk">
                        <span class="at-t">{{ f.departure_time }}</span>
                        <span class="at-ap">{{ f.origin || result.route.split(' → ')[0] }}</span>
                      </div>
                      <div class="at-mid">
                        <div class="at-line"></div>
                        <span class="at-dur-lbl">{{ fmtDur(f.duration_min) }}</span>
                        <span :class="['at-stops', f.is_direct?'sp-direct':'sp-stops']">
                          {{ f.is_direct ? 'Nonstop' : `${f.num_stops} stop${f.num_stops>1?'s':''}` }}
                        </span>
                      </div>
                      <div class="at-time-blk at-right">
                        <span class="at-t">{{ f.arrival_time }}</span>
                        <span class="at-ap">{{ f.destination || result.route.split(' → ')[1] }}</span>
                      </div>
                    </div>
                    <div class="at-footer">
                      <div>
                        <span class="at-price">${{ f.price_usd?.toLocaleString() }}</span>
                        <span class="at-cabin">{{ cabinLabel }}</span>
                      </div>
                      <span class="at-note">Current market price · not the AI prediction</span>
                    </div>
                  </div>
                </Transition>
                <!-- Row summary -->
                <div class="alt-logo-wrap">
                  <img v-if="f.airline_logo" :src="f.airline_logo" :alt="f.airline_name"
                    class="alt-logo" @error="e=>e.target.style.display='none'" />
                  <span v-else class="alt-logo-fb">✈</span>
                </div>
                <span class="alt-airline">{{ f.airline_name||'Airline' }}</span>
                <span class="alt-times">{{ f.departure_time }} → {{ f.arrival_time }}</span>
                <span class="alt-dur">{{ fmtDur(f.duration_min) }}</span>
                <span :class="['alt-stops', f.is_direct?'sp-direct':'sp-stops']">{{ f.is_direct?'Nonstop':`${f.num_stops} stop` }}</span>
                <span class="alt-price">${{ f.price_usd?.toLocaleString() }}</span>
                <span class="alt-hover-hint">›</span>
              </div>
            </div>

            <!-- Weather card -->
            <div v-if="result.disruption" class="weather-card" :class="`wr-${result.disruption.delay_risk}`">
              <div class="wc-head">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
                </svg>
                Weather Disruption
                <span :class="['risk-pill', `rp-${result.disruption.delay_risk}`]">
                  {{ result.disruption.delay_risk.toUpperCase() }} RISK
                </span>
              </div>
              <div class="wx-pair">
                <div v-for="wx in [result.disruption.origin_weather, result.disruption.dest_weather]"
                  :key="wx.airport_code" class="wx-item">
                  <span class="wx-em">{{ wx.weather_emoji }}</span>
                  <div class="wx-info">
                    <span class="wx-code">{{ wx.airport_code }}</span>
                    <span class="wx-desc">{{ wx.weather_desc }}</span>
                    <div class="wx-stats">
                      <span>💨 {{ wx.wind_speed_kmh }}km/h</span>
                      <span>🌧 {{ wx.precipitation_prob }}%</span>
                      <span>👁 {{ wx.visibility_km }}km</span>
                    </div>
                  </div>
                  <div class="wx-ring">
                    <svg width="44" height="44" viewBox="0 0 44 44">
                      <circle cx="22" cy="22" r="18" fill="none" stroke="rgba(0,0,0,0.1)" stroke-width="4"/>
                      <circle cx="22" cy="22" r="18" fill="none" :stroke="riskColor(wx.risk_level)"
                        stroke-width="4" stroke-linecap="round"
                        :stroke-dasharray="`${wx.disruption_score*1.131} 113.1`"
                        transform="rotate(-90 22 22)"/>
                    </svg>
                    <span class="wx-sc">{{ wx.disruption_score }}</span>
                  </div>
                </div>
              </div>
              <div class="ot-row">
                <span class="ot-lbl">On-time probability</span>
                <div class="ot-track"><div class="ot-fill" :style="{width:`${result.disruption.on_time_probability*100}%`,background:ontimeColor}"></div></div>
                <span class="ot-pct" :style="{color:ontimeColor}">{{ Math.round(result.disruption.on_time_probability*100) }}%</span>
              </div>
              <p class="wx-primary">{{ result.disruption.primary_risk_factor }}</p>
            </div>

          </div>

          <!-- RIGHT column -->
          <div class="col-r">

            <!-- Agent decisions -->
            <div class="agents-card">
              <div class="card-hd">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
                Market agent decisions
                <span class="mf-card-tag">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                  </svg>
                  MiroFish
                </span>
              </div>
              <div class="agents-list">
                <div v-for="a in visibleActions" :key="`${a.round}-${a.agent_id}`"
                  class="agent-row"
                  @mouseenter="hoveredAgent=`${a.round}-${a.agent_id}`"
                  @mouseleave="hoveredAgent=null">
                  <div class="ag-av" :style="{background:agentColor(a.agent_id)}">{{ a.agent_name[0] }}</div>
                  <div class="ag-body">
                    <div class="ag-hdr">
                      <span class="ag-name">{{ a.agent_name }}</span>
                      <span v-if="agentProfiles[a.agent_id]" class="ag-role-tag">{{ agentProfiles[a.agent_id].tag }}</span>
                      <span class="ag-round">R{{ a.round }}</span>
                      <span :class="['dec-chip', `dc-${a.decision}`]">{{ a.decision.replace(/_/g,' ') }}</span>
                      <span :class="['ag-mag', a.magnitude_pct>=0?'mag-up':'mag-dn']">
                        {{ a.magnitude_pct>=0?'+':'' }}{{ a.magnitude_pct }}%
                      </span>
                    </div>
                    <p class="ag-reason">{{ a.reasoning }}</p>
                    <Transition name="ag-expand">
                      <div v-if="hoveredAgent===`${a.round}-${a.agent_id}` && agentProfiles[a.agent_id]"
                        class="ag-profile">
                        <div class="agp-who">{{ agentProfiles[a.agent_id].who }}</div>
                        <p class="agp-desc">{{ agentProfiles[a.agent_id].simulates }}</p>
                        <div class="agp-signals">
                          <span v-for="s in agentProfiles[a.agent_id].signals" :key="s" class="agp-sig">
                            <span class="agp-sig-dot">◆</span>{{ s }}
                          </span>
                        </div>
                        <div v-if="agentProfiles[a.agent_id].hedge !== null || agentProfiles[a.agent_id].share !== null"
                          class="agp-meta">
                          <span v-if="agentProfiles[a.agent_id].hedge !== null" class="agp-meta-item">
                            Fuel hedge <strong>{{ agentProfiles[a.agent_id].hedge }}</strong>
                          </span>
                          <span v-if="agentProfiles[a.agent_id].share !== null" class="agp-meta-item">
                            Market share <strong>{{ agentProfiles[a.agent_id].share }}</strong>
                          </span>
                        </div>
                      </div>
                    </Transition>
                  </div>
                </div>
              </div>
              <button v-if="result.agent_actions.length>4" class="show-more-btn" @click="showAll=!showAll">
                {{ showAll?'Show less':`Show all ${result.agent_actions.length} agent moves` }}
              </button>
            </div>

            <!-- P&L Cascade — plain English -->
            <div class="cascade-card">
              <div class="card-hd">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
                P&amp;L shock cascade
                <span class="card-hd-note">deterministic · BFS model · no LLM</span>
              </div>
              <p class="cascade-intro">Traces how the shock moves through airline P&amp;L — from fuel cost through capacity, yield management, and competitor response. Runs independently of the agent simulation.</p>
              <div class="cascade-grid">
                <div v-for="(imp, key) in topCascade" :key="key" class="cn-card"
                  :class="{expanded: expandedNodes.has(key)}" @click="toggleNode(key)">
                  <div class="cn-main">
                    <span class="cn-icon">{{ imp.plain_icon||'📊' }}</span>
                    <div class="cn-info">
                      <div class="cn-top-row">
                        <span class="cn-label">{{ imp.plain_label||key }}</span>
                        <span :class="['cn-sev', severityClass(imp.impact)]">{{ severityLabel(imp.impact) }}</span>
                      </div>
                      <div class="cn-bar-row">
                        <div class="cn-bar">
                          <div class="cn-fill" :style="{
                            width:`${Math.min(100,Math.abs(imp.impact)*160)}%`,
                            background: imp.impact>=0?'#ef4444':'#10b981'
                          }"></div>
                        </div>
                        <span class="cn-timeline">~{{ imp.days_to_effect }}d</span>
                      </div>
                    </div>
                    <svg class="cn-chevron" :class="{rotated: expandedNodes.has(key)}"
                      width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="6 9 12 15 18 9"/>
                    </svg>
                  </div>
                  <div v-if="expandedNodes.has(key)" class="cn-expand">
                    <p class="cn-interpret">{{ impactInterpret(imp) }}</p>
                    <p v-if="imp.plain_what" class="cn-what">
                      <span class="cn-what-icon">💡</span> {{ imp.plain_what }}
                    </p>
                    <div class="cn-meta-row">
                      <span class="cn-meta-item">⏱ Effect in ~{{ imp.days_to_effect }} day{{ imp.days_to_effect===1?'':'s' }}</span>
                      <span class="cn-meta-item cn-conf-badge" :class="imp.confidence>=0.8?'cb-high':imp.confidence>=0.6?'cb-med':'cb-low'">
                        {{ imp.confidence>=0.8?'High':imp.confidence>=0.6?'Moderate':'Lower' }} confidence · {{ Math.round(imp.confidence*100) }}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Narrative -->
            <div class="narrative-card">
              <div class="card-hd">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                Fare Intelligence Brief
              </div>
              <div class="narrative-body">
                <template v-for="(section, idx) in narrativeSections" :key="idx">
                  <!-- Watch List renders as bullets -->
                  <div v-if="section.isWatchList" class="nr-section nr-watchlist">
                    <div class="nr-heading">
                      <span class="nr-icon">◈</span>{{ section.title }}
                    </div>
                    <ul class="nr-bullets">
                      <li v-for="(item, i) in section.bullets" :key="i" class="nr-bullet">
                        <span class="nr-bullet-dot">→</span>{{ item }}
                      </li>
                    </ul>
                  </div>
                  <!-- Regular sections -->
                  <div v-else class="nr-section">
                    <div class="nr-heading">
                      <span class="nr-icon">{{ sectionIcon(section.title) }}</span>{{ section.title }}
                    </div>
                    <p class="nr-body">{{ section.body }}</p>
                  </div>
                </template>
                <!-- Fallback: raw text if no ## sections found -->
                <p v-if="narrativeSections.length === 0" class="nr-raw">{{ result.narrative }}</p>
              </div>
            </div>

            <!-- Data sources -->
            <div class="sources-card">
              <span class="sources-label">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
                Live data sources
              </span>
              <div class="sources-row">
                <span v-for="(src, key) in result.data_sources" :key="key"
                  :class="['src-chip', src==='synthetic'?'src-syn':'src-live']">
                  {{ sourceLabel(key, src) }}
                </span>
              </div>
            </div>

          </div>
        </div>

        <!-- Export bar -->
        <div class="export-bar">
          <span class="export-label">{{ exportLabel }}</span>
          <div class="export-actions">
            <button class="exp-btn" @click="copyReport(result, null)" :class="copied==='text'&&'exp-btn-done'">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
              {{ copied === 'text' ? '✓ Copied' : 'Copy report' }}
            </button>
            <button class="exp-btn" @click="downloadJson(result, null)" :class="copied==='json'&&'exp-btn-done'">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              {{ copied === 'json' ? '✓ Saved' : 'Download JSON' }}
            </button>
            <button class="exp-btn" @click="exportPdf(result, null)">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
              Export PDF
            </button>
          </div>
        </div>
      </div>

      <!-- ── Comparison results ────────────────────────────────────── -->
      <!--
        This panel REPLACES the single-result view when both scenarios are ready.
        It contains exactly 4 sections:
          1. Prediction header (A vs B fare deltas)
          2. Financial cascade comparison (deterministic BFS, run independently per trigger)
          3. Agent decisions (8 agents simulated independently for each scenario)
          4. AI Analysis reports (2 independent LLM analyses, one per scenario)
      -->
      <div v-if="compareMode && result && result2" class="cmp-results">

        <!-- ── 1. Prediction header ─────────────────────────────── -->
        <div class="cmp-header">
          <div class="cmp-route-line">
            <span class="cmp-route-code">{{ result.route }}</span>
            <span class="cmp-divider">·</span>
            <span class="cmp-cabin-lbl">{{ cabinLabel }}</span>
            <span class="cmp-divider">·</span>
            <span class="cmp-date-lbl">{{ horizon !== 'custom' ? horizon + '-day window' : fmtDate(departureDate) }}</span>
            <span class="cmp-divider">·</span>
            <span class="cmp-mode-tag">COMPARISON MODE</span>
          </div>
          <div class="cmp-banner">
            <div class="cmp-half cmp-a">
              <div class="cmp-scn-badge-wrap">
                <span class="scn-badge scn-a">A</span>
                <span class="cmp-scn-shocks">{{ result.trigger_ids?.map(id => (triggers.find(t=>t.id===id)?.icon||'') + ' ' + (triggers.find(t=>t.id===id)?.label||id)).join(' + ') }}</span>
              </div>
              <div class="cmp-fare-line">
                <span class="cmp-base">${{ result.seed_fare.toLocaleString() }}</span>
                <svg width="24" height="10" viewBox="0 0 32 10" fill="none" style="flex-shrink:0">
                  <path d="M0 5h26M20 1l6 4-6 4" :stroke="result.fare_delta>=0?'#dc2626':'#16a34a'" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
                <span class="cmp-predicted" :class="result.fare_delta>=0?'cmp-up':'cmp-dn'">${{ result.predicted_fare.toLocaleString() }}</span>
                <span :class="['cmp-pct', result.fare_delta>=0?'cmp-up':'cmp-dn']">{{ result.fare_delta>=0?'▲':'▼' }} {{ Math.abs(result.fare_delta_pct) }}%</span>
              </div>
              <div class="cmp-meta-row">
                <span class="cmp-conf">{{ Math.round(result.confidence*100) }}% confidence</span>
                <span class="cmp-cons">{{ consensusLabel }}</span>
              </div>
            </div>
            <div class="cmp-vs">VS</div>
            <div class="cmp-half cmp-b">
              <div class="cmp-scn-badge-wrap">
                <span class="scn-badge scn-b">B</span>
                <span class="cmp-scn-shocks">{{ result2.trigger_ids?.map(id => (triggers.find(t=>t.id===id)?.icon||'') + ' ' + (triggers.find(t=>t.id===id)?.label||id)).join(' + ') }}</span>
              </div>
              <div class="cmp-fare-line">
                <span class="cmp-base">${{ result2.seed_fare.toLocaleString() }}</span>
                <svg width="24" height="10" viewBox="0 0 32 10" fill="none" style="flex-shrink:0">
                  <path d="M0 5h26M20 1l6 4-6 4" :stroke="result2.fare_delta>=0?'#dc2626':'#16a34a'" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
                <span class="cmp-predicted" :class="result2.fare_delta>=0?'cmp-up':'cmp-dn'">${{ result2.predicted_fare.toLocaleString() }}</span>
                <span :class="['cmp-pct', result2.fare_delta>=0?'cmp-up':'cmp-dn']">{{ result2.fare_delta>=0?'▲':'▼' }} {{ Math.abs(result2.fare_delta_pct) }}%</span>
              </div>
              <div class="cmp-meta-row">
                <span class="cmp-conf">{{ Math.round(result2.confidence*100) }}% confidence</span>
                <span class="cmp-cons">{{ consensusLabel2 }}</span>
              </div>
            </div>
          </div>
          <div class="cmp-delta-bar">
            <template v-if="Math.abs(result.fare_delta - result2.fare_delta) < 0.01">
              <span class="cdb-draw-chip">SIMILAR IMPACT</span>
              <span class="cdb-val">Both shocks predict comparable fare movement on this route. The route sensitivity outweighs the trigger difference.</span>
            </template>
            <template v-else>
              <span :class="['cdb-winner-chip', result.fare_delta > result2.fare_delta ? 'cdb-w-a' : 'cdb-w-b']">
                {{ result.fare_delta > result2.fare_delta ? 'SCENARIO A RISKIER' : 'SCENARIO B RISKIER' }}
              </span>
              <div class="cdb-verdict">
                <span class="cdb-verdict-num">${{ Math.round(Math.abs(result.predicted_fare - result2.predicted_fare)) }}</span>
                <span class="cdb-verdict-txt">
                  fare difference —
                  {{ result.fare_delta > result2.fare_delta
                    ? `${result.trigger_ids?.map(id=>triggers.find(t=>t.id===id)?.label||id).join(' + ')} drives a steeper price impact. Book earlier or hedge against this shock first.`
                    : `${result2.trigger_ids?.map(id=>triggers.find(t=>t.id===id)?.label||id).join(' + ')} drives a steeper price impact. Book earlier or hedge against this shock first.`
                  }}
                </span>
              </div>
            </template>
          </div>
        </div>

        <!-- ── 2. Financial cascade comparison ─────────────────── -->
        <div class="cmp-section-card">
          <div class="card-hd">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            P&amp;L cascade comparison
            <span class="card-hd-note">deterministic · BFS model · no LLM · independent per scenario</span>
          </div>
          <p class="cmp-section-intro">
            Each shock triggers its own path through airline P&amp;L — fuel cost, seat capacity, yield management, competitor response. Rows marked "differs" show where the choice of shock changes the financial impact.
          </p>
          <div class="cmp-cascade-grid">
            <div class="cmp-cas-row cmp-cas-hdr">
              <span class="cmp-cas-node">P&amp;L Node</span>
              <span class="cmp-cas-val">
                <span class="scn-badge scn-a" style="font-size:9px;padding:1px 5px;width:auto;height:auto">A</span>
                {{ result.trigger_ids?.map(id=>triggers.find(t=>t.id===id)?.label||id).join('+') }}
              </span>
              <span class="cmp-cas-val">
                <span class="scn-badge scn-b" style="font-size:9px;padding:1px 5px;width:auto;height:auto">B</span>
                {{ result2.trigger_ids?.map(id=>triggers.find(t=>t.id===id)?.label||id).join('+') }}
              </span>
            </div>
            <div v-for="key in mergedCascadeKeys" :key="key" class="cmp-cas-row"
              :class="cascadeRowDiverges(key) ? 'cas-row-diff' : ''">
              <span class="cmp-cas-node">
                {{ result.cascade_impacts[key]?.plain_icon || result2.cascade_impacts[key]?.plain_icon || '📊' }}
                {{ result.cascade_impacts[key]?.plain_label || result2.cascade_impacts[key]?.plain_label || key }}
                <span v-if="cascadeRowDiverges(key)" class="cas-diff-tag">differs</span>
              </span>
              <span class="cmp-cas-val" :class="result.cascade_impacts[key] ? (result.cascade_impacts[key].impact>=0?'cas-up':'cas-dn') : 'cas-na'">
                {{ result.cascade_impacts[key] ? severityLabel(result.cascade_impacts[key].impact) : '—' }}
              </span>
              <span class="cmp-cas-val" :class="result2.cascade_impacts[key] ? (result2.cascade_impacts[key].impact>=0?'cas-up':'cas-dn') : 'cas-na'">
                {{ result2.cascade_impacts[key] ? severityLabel(result2.cascade_impacts[key].impact) : '—' }}
              </span>
            </div>
          </div>
        </div>

        <!-- ── 3. Agent decisions side by side ──────────────────── -->
        <div class="cmp-section-card">
          <div class="card-hd">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            Agent decisions by scenario
            <span class="card-hd-note">8 market agents · simulated independently per scenario</span>
          </div>
          <div class="cmp-agents-cols">
            <!-- Scenario A agents -->
            <div class="cmp-agents-col">
              <div class="cmp-nar-hdr">
                <span class="scn-badge scn-a">A</span>
                {{ result.trigger_ids?.map(id=>triggers.find(t=>t.id===id)?.label||id).join(' + ') }}
              </div>
              <div class="agents-list">
                <div v-for="a in (result.agent_actions||[]).slice(0,5)" :key="`a-${a.round}-${a.agent_id}`"
                  class="agent-row agent-row-cmp"
                  @mouseenter="hoveredAgentA=`${a.round}-${a.agent_id}`"
                  @mouseleave="hoveredAgentA=null">
                  <div class="ag-av" :style="{background:agentColor(a.agent_id)}">{{ a.agent_name[0] }}</div>
                  <div class="ag-body">
                    <div class="ag-hdr">
                      <span class="ag-name">{{ a.agent_name }}</span>
                      <span v-if="agentProfiles[a.agent_id]" class="ag-role-tag">{{ agentProfiles[a.agent_id].tag }}</span>
                      <span class="ag-round">R{{ a.round }}</span>
                      <span :class="['dec-chip', `dc-${a.decision}`]">{{ a.decision.replace(/_/g,' ') }}</span>
                      <span :class="['ag-mag', a.magnitude_pct>=0?'mag-up':'mag-dn']">{{ a.magnitude_pct>=0?'+':'' }}{{ a.magnitude_pct }}%</span>
                    </div>
                    <p class="ag-reason">{{ trunc(a.reasoning, 120) }}</p>
                    <Transition name="ag-expand">
                      <div v-if="hoveredAgentA===`${a.round}-${a.agent_id}` && agentProfiles[a.agent_id]" class="ag-profile">
                        <div class="agp-who">{{ agentProfiles[a.agent_id].who }}</div>
                        <p class="agp-desc">{{ agentProfiles[a.agent_id].simulates }}</p>
                        <div class="agp-signals">
                          <span v-for="s in agentProfiles[a.agent_id].signals" :key="s" class="agp-sig">
                            <span class="agp-sig-dot">◆</span>{{ s }}
                          </span>
                        </div>
                        <div v-if="agentProfiles[a.agent_id].hedge !== null || agentProfiles[a.agent_id].share !== null" class="agp-meta">
                          <span v-if="agentProfiles[a.agent_id].hedge !== null" class="agp-meta-item">Fuel hedge <strong>{{ agentProfiles[a.agent_id].hedge }}</strong></span>
                          <span v-if="agentProfiles[a.agent_id].share !== null" class="agp-meta-item">Market share <strong>{{ agentProfiles[a.agent_id].share }}</strong></span>
                        </div>
                      </div>
                    </Transition>
                  </div>
                </div>
              </div>
            </div>
            <!-- Scenario B agents -->
            <div class="cmp-agents-col">
              <div class="cmp-nar-hdr">
                <span class="scn-badge scn-b">B</span>
                {{ result2.trigger_ids?.map(id=>triggers.find(t=>t.id===id)?.label||id).join(' + ') }}
              </div>
              <div class="agents-list">
                <div v-for="a in (result2.agent_actions||[]).slice(0,5)" :key="`b-${a.round}-${a.agent_id}`"
                  class="agent-row agent-row-cmp"
                  @mouseenter="hoveredAgentB=`${a.round}-${a.agent_id}`"
                  @mouseleave="hoveredAgentB=null">
                  <div class="ag-av" :style="{background:agentColor(a.agent_id)}">{{ a.agent_name[0] }}</div>
                  <div class="ag-body">
                    <div class="ag-hdr">
                      <span class="ag-name">{{ a.agent_name }}</span>
                      <span v-if="agentProfiles[a.agent_id]" class="ag-role-tag">{{ agentProfiles[a.agent_id].tag }}</span>
                      <span class="ag-round">R{{ a.round }}</span>
                      <span :class="['dec-chip', `dc-${a.decision}`]">{{ a.decision.replace(/_/g,' ') }}</span>
                      <span :class="['ag-mag', a.magnitude_pct>=0?'mag-up':'mag-dn']">{{ a.magnitude_pct>=0?'+':'' }}{{ a.magnitude_pct }}%</span>
                    </div>
                    <p class="ag-reason">{{ trunc(a.reasoning, 120) }}</p>
                    <Transition name="ag-expand">
                      <div v-if="hoveredAgentB===`${a.round}-${a.agent_id}` && agentProfiles[a.agent_id]" class="ag-profile">
                        <div class="agp-who">{{ agentProfiles[a.agent_id].who }}</div>
                        <p class="agp-desc">{{ agentProfiles[a.agent_id].simulates }}</p>
                        <div class="agp-signals">
                          <span v-for="s in agentProfiles[a.agent_id].signals" :key="s" class="agp-sig">
                            <span class="agp-sig-dot">◆</span>{{ s }}
                          </span>
                        </div>
                        <div v-if="agentProfiles[a.agent_id].hedge !== null || agentProfiles[a.agent_id].share !== null" class="agp-meta">
                          <span v-if="agentProfiles[a.agent_id].hedge !== null" class="agp-meta-item">Fuel hedge <strong>{{ agentProfiles[a.agent_id].hedge }}</strong></span>
                          <span v-if="agentProfiles[a.agent_id].share !== null" class="agp-meta-item">Market share <strong>{{ agentProfiles[a.agent_id].share }}</strong></span>
                        </div>
                      </div>
                    </Transition>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── 4. AI Analysis reports side by side ──────────────── -->
        <div class="cmp-section-card">
          <div class="card-hd">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            Fare Intelligence Briefs
            <span class="card-hd-note">2 independent briefs · each written for its own trigger, route, and predicted delta</span>
          </div>
          <div class="cmp-narratives">
            <div class="cmp-nar-col">
              <div class="cmp-nar-hdr">
                <span class="scn-badge scn-a">A</span>
                {{ result.trigger_ids?.map(id=>triggers.find(t=>t.id===id)?.label||id).join(' + ') }}
                <span class="cmp-nar-fare">→ ${{ result.predicted_fare.toLocaleString() }}</span>
              </div>
              <div class="narrative-body cmp-nar-body">
                <template v-for="(section, idx) in narrativeSections" :key="`a-${idx}`">
                  <div v-if="section.isWatchList" class="nr-section nr-watchlist">
                    <div class="nr-heading"><span class="nr-icon">◈</span>{{ section.title }}</div>
                    <ul class="nr-bullets">
                      <li v-for="(item, i) in section.bullets" :key="i" class="nr-bullet">
                        <span class="nr-bullet-dot">→</span>{{ item }}
                      </li>
                    </ul>
                  </div>
                  <div v-else class="nr-section">
                    <div class="nr-heading"><span class="nr-icon">{{ sectionIcon(section.title) }}</span>{{ section.title }}</div>
                    <p class="nr-body">{{ section.body }}</p>
                  </div>
                </template>
              </div>
            </div>
            <div class="cmp-nar-col">
              <div class="cmp-nar-hdr">
                <span class="scn-badge scn-b">B</span>
                {{ result2.trigger_ids?.map(id=>triggers.find(t=>t.id===id)?.label||id).join(' + ') }}
                <span class="cmp-nar-fare">→ ${{ result2.predicted_fare.toLocaleString() }}</span>
              </div>
              <div class="narrative-body cmp-nar-body">
                <template v-for="(section, idx) in narrativeSections2" :key="`b-${idx}`">
                  <div v-if="section.isWatchList" class="nr-section nr-watchlist">
                    <div class="nr-heading"><span class="nr-icon">◈</span>{{ section.title }}</div>
                    <ul class="nr-bullets">
                      <li v-for="(item, i) in section.bullets" :key="i" class="nr-bullet">
                        <span class="nr-bullet-dot">→</span>{{ item }}
                      </li>
                    </ul>
                  </div>
                  <div v-else class="nr-section">
                    <div class="nr-heading"><span class="nr-icon">{{ sectionIcon(section.title) }}</span>{{ section.title }}</div>
                    <p class="nr-body">{{ section.body }}</p>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- Export bar (comparison mode) -->
        <div class="export-bar">
          <span class="export-label">{{ exportLabelCompare }}</span>
          <div class="export-actions">
            <button class="exp-btn" @click="copyReport(result, result2)" :class="copied==='text'&&'exp-btn-done'">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
              {{ copied === 'text' ? '✓ Copied' : 'Copy report' }}
            </button>
            <button class="exp-btn" @click="downloadJson(result, result2)" :class="copied==='json'&&'exp-btn-done'">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              {{ copied === 'json' ? '✓ Saved' : 'Download JSON' }}
            </button>
            <button class="exp-btn" @click="exportPdf(result, result2)">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
              Export PDF
            </button>
          </div>
        </div>

      </div>

      <!-- ── Empty state / pitch ───────────────────────────────────── -->
      <div v-if="!result && !isLoading" class="aw-empty">
        <div class="empty-hero">
          <p class="empty-eyebrow">◇ &nbsp;AIRWAVE SCENARIO INTELLIGENCE</p>
          <h2 class="empty-h">Stop booking blind.</h2>
          <p class="empty-sub">When a macro shock hits — fuel spike, strike, geopolitical crisis — traditional fare tools show you where prices <em>were</em>. AirWave simulates how the four competing forces that set your ticket price respond, and tells you what fares will look like before you need to act.</p>
        </div>

        <div class="empty-pillars">
          <div class="empty-pillar">
            <span class="ep-num">01</span>
            <span class="ep-title">Event-driven, not statistical</span>
            <p class="ep-desc">Model a specific shock — fuel spike, labour strike, FX move. Get the market response for that event on that route. Not a generic forecast.</p>
          </div>
          <div class="empty-pillar">
            <span class="ep-num">02</span>
            <span class="ep-title">Four adversarial agents</span>
            <p class="ep-desc">LCC revenue manager, legacy carrier, corporate buyer, leisure traveller — each with real pricing psychology, hedge ratios, and booking windows — argue about your fare.</p>
          </div>
          <div class="empty-pillar">
            <span class="ep-num">03</span>
            <span class="ep-title">Live-seeded, not hypothetical</span>
            <p class="ep-desc">Anchored to real NDC fares, OpenSky demand, Open-Meteo weather, and live macro data. Agents reason against the actual market, not a textbook scenario.</p>
          </div>
        </div>

        <div class="empty-examples">
          <span class="empty-ex-lbl">Try a scenario</span>
          <div class="example-row">
            <button v-for="ex in examples" :key="ex.label" class="ex-chip" @click="applyExample(ex)">
              {{ ex.label }}
            </button>
          </div>
        </div>
      </div>

    </main>

    <!-- ── Simulation history drawer ────────────────────────────── -->
    <Teleport to="body">
      <Transition name="hist-fade">
        <div v-if="showHistory" class="hist-backdrop" @click.self="showHistory=false">
          <div class="hist-drawer">
            <div class="hist-hd">
              <span class="hist-title">Simulation History</span>
              <div class="hist-hd-actions">
                <button v-if="simHistory.length" class="hist-clear" @click="clearHistory">Clear all</button>
                <button class="hist-close" @click="showHistory=false">✕</button>
              </div>
            </div>
            <div v-if="!simHistory.length" class="hist-empty">No simulations yet — run a scenario to record it here.</div>
            <div v-else class="hist-list">
              <div v-for="entry in simHistory" :key="entry.id" class="hist-entry" @click="recallHistory(entry)">
                <div class="he-top">
                  <span class="he-route">{{ entry.route }}</span>
                  <span :class="['he-delta', entry.fareDelta>=0?'he-up':'he-dn']">
                    {{ entry.fareDelta>=0?'▲':'▼' }} {{ Math.abs(entry.fareDeltaPct) }}%
                  </span>
                </div>
                <div class="he-shocks">{{ entry.shocksA }}{{ entry.shocksB ? ' vs ' + entry.shocksB : '' }}</div>
                <div class="he-meta">
                  <span class="he-fare">${{ entry.seedFare?.toLocaleString() }} → ${{ entry.predictedFare?.toLocaleString() }}</span>
                  <span class="he-ts">{{ new Date(entry.ts).toLocaleDateString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ── Methodology panel ─────────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="meth-fade">
        <div v-if="showMethodology" class="meth-backdrop" @click.self="showMethodology=false">
          <div class="meth-panel">

            <!-- Header -->
            <div class="meth-hd">
              <div class="meth-hd-left">
                <span class="meth-eyebrow">AIRWAVE</span>
                <span class="meth-title">Methodology</span>
              </div>
              <button class="meth-close" @click="showMethodology=false">✕</button>
            </div>

            <!-- Tabs -->
            <div class="meth-tabs">
              <button :class="['meth-tab', methodTab==='pipeline'&&'meth-tab-active']" @click="methodTab='pipeline'">How it works</button>
              <button :class="['meth-tab', methodTab==='agents'&&'meth-tab-active']" @click="methodTab='agents'">Market agents</button>
              <button :class="['meth-tab', methodTab==='data'&&'meth-tab-active']" @click="methodTab='data'">Data sources</button>
            </div>

            <!-- Body -->
            <div class="meth-body">

              <!-- ── Tab: Pipeline ─────────────────────────────── -->
              <div v-if="methodTab==='pipeline'" class="meth-pipeline">
                <p class="meth-intro">AirWave produces a fare prediction in four deterministic stages. No black box — every number is traceable to a data source or agent decision.</p>

                <div class="pip-steps">
                  <div class="pip-step">
                    <div class="pip-num">01</div>
                    <div class="pip-content">
                      <div class="pip-label">Live Data Ingestion</div>
                      <p class="pip-desc">Real-time fares via Duffel NDC, route departure frequency via OpenSky Network, weather via Open-Meteo, FX rates and crude oil price via Yahoo Finance, and headline context via Google News RSS — all pulled fresh on each simulation. Where a live source is unavailable, synthetic fallback data is generated and clearly labeled.</p>
                      <div class="pip-badges">
                        <span class="pip-badge">Duffel NDC</span>
                        <span class="pip-badge">OpenSky</span>
                        <span class="pip-badge">Open-Meteo</span>
                        <span class="pip-badge">Yahoo Finance</span>
                        <span class="pip-badge">Google News</span>
                      </div>
                    </div>
                  </div>

                  <div class="pip-connector"></div>

                  <div class="pip-step">
                    <div class="pip-num">02</div>
                    <div class="pip-content">
                      <div class="pip-label">Shock Cascade Engine</div>
                      <p class="pip-desc">A deterministic breadth-first model maps the selected market trigger across six downstream P&amp;L nodes: fuel cost, crew utilization, maintenance, slot fees, hedging position, and passenger yield. This produces the quantified shock inputs each agent receives — and is fully auditable in the cascade panel below the results.</p>
                      <div class="pip-badges">
                        <span class="pip-badge pip-badge-det">Deterministic BFS — no LLM</span>
                      </div>
                    </div>
                  </div>

                  <div class="pip-connector"></div>

                  <div class="pip-step">
                    <div class="pip-num">03</div>
                    <div class="pip-content">
                      <div class="pip-label">Multi-Agent Reasoning</div>
                      <p class="pip-desc">Eight independent market participants — LCC revenue managers, legacy carriers, corporate buyers, leisure travelers, OTAs, premium boutiques, ULCCs, and miles optimizers — each receive the same live seed data and shock cascade output, then produce a fare vote and confidence score based on their individual behavioral profiles and hedging positions.</p>
                      <div class="pip-badges">
                        <span class="pip-badge">8 agents</span>
                        <span class="pip-badge">Independent reasoning</span>
                        <span class="pip-badge">Gemini 2.0 Flash</span>
                      </div>
                    </div>
                  </div>

                  <div class="pip-connector"></div>

                  <div class="pip-step">
                    <div class="pip-num">04</div>
                    <div class="pip-content">
                      <div class="pip-label">Consensus Forecast</div>
                      <p class="pip-desc">Agent votes are weighted by real-world market share — Legacy carriers 42%, LCCs 28%, ULCCs 12%, Premium Boutique 7%, plus demand-side agents — and averaged into a predicted fare with a ±prediction band. The band reflects disagreement between agents: wider spread means higher uncertainty.</p>
                      <div class="pip-badges">
                        <span class="pip-badge">Share-weighted consensus</span>
                        <span class="pip-badge">±Prediction band</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="pip-disclaimer">
                  <strong>Important:</strong> AirWave is a scenario intelligence tool, not a booking engine. Predicted fares are model outputs for strategic planning — not guarantees of actual market prices. Confidence scores reflect agent agreement, not actuarial precision.
                </div>
              </div>

              <!-- ── Tab: Agents ────────────────────────────────── -->
              <div v-if="methodTab==='agents'" class="meth-agents">
                <p class="meth-intro">Eight market participants reason independently under each scenario. Each has a fixed behavioral profile, fuel hedge position, and market share weight that determines how they vote on fare movement.</p>
                <div class="agt-grid">
                  <div v-for="(profile, key) in agentProfiles" :key="key" class="agt-card">
                    <div class="agt-card-hd">
                      <span class="agt-tag">{{ profile.tag }}</span>
                      <div class="agt-meta" v-if="profile.hedge !== null">
                        <span class="agt-meta-item" title="Fuel hedge ratio"><span class="agt-meta-icon">⛽</span> {{ profile.hedge }} hedged</span>
                        <span class="agt-meta-sep">·</span>
                        <span class="agt-meta-item" title="Market share"><span class="agt-meta-icon">◈</span> {{ profile.share }} share</span>
                      </div>
                    </div>
                    <p class="agt-who">{{ profile.who }}</p>
                    <p class="agt-sim">{{ profile.simulates }}</p>
                    <div class="agt-signals">
                      <span v-for="sig in profile.signals" :key="sig" class="agt-signal">{{ sig }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- ── Tab: Data sources ──────────────────────────── -->
              <div v-if="methodTab==='data'" class="meth-data">
                <p class="meth-intro">Every simulation pulls live data from six sources. When a source is unavailable or the route has no historical data, the fallback is labeled "synthetic" in the results.</p>
                <div class="ds-list">
                  <div class="ds-item">
                    <div class="ds-item-hd">
                      <span class="ds-name">Duffel NDC API</span>
                      <span class="ds-badge ds-badge-live">LIVE</span>
                    </div>
                    <p class="ds-desc">Real-time airfare offers via airline New Distribution Capability connections. Provides the seed fare that anchors every prediction. Falls back to synthetic pricing when no route offers are returned.</p>
                    <div class="ds-used-for">Used for: Seed fare · Trip type detection</div>
                  </div>
                  <div class="ds-item">
                    <div class="ds-item-hd">
                      <span class="ds-name">OpenSky Network</span>
                      <span class="ds-badge ds-badge-live">LIVE</span>
                    </div>
                    <p class="ds-desc">Open-source flight tracking network providing live departure frequency for the route pair. Used as a demand proxy — higher departure frequency signals stronger competitive pressure on fares.</p>
                    <div class="ds-used-for">Used for: Demand signal · Capacity Dump trigger · Disruption Event trigger</div>
                  </div>
                  <div class="ds-item">
                    <div class="ds-item-hd">
                      <span class="ds-name">Open-Meteo</span>
                      <span class="ds-badge ds-badge-live">LIVE</span>
                    </div>
                    <p class="ds-desc">Free meteorological API providing current weather conditions at origin and destination airports. Windspeed and precipitation feed into the Disruption Event cascade model.</p>
                    <div class="ds-used-for">Used for: Disruption Event trigger · Agent weather context</div>
                  </div>
                  <div class="ds-item">
                    <div class="ds-item-hd">
                      <span class="ds-name">Yahoo Finance / WTI Crude</span>
                      <span class="ds-badge ds-badge-live">LIVE</span>
                    </div>
                    <p class="ds-desc">Live commodity and FX price feeds. WTI crude oil price drives the Fuel Spike cascade model directly. Currency pairs (USD/EUR, USD/GBP, USD/JPY) feed the Exchange Rate trigger.</p>
                    <div class="ds-used-for">Used for: Fuel Spike trigger · Exchange Rate trigger · Macro context</div>
                  </div>
                  <div class="ds-item">
                    <div class="ds-item-hd">
                      <span class="ds-name">Google News RSS</span>
                      <span class="ds-badge ds-badge-live">LIVE</span>
                    </div>
                    <p class="ds-desc">Geo-targeted headline feed for origin and destination geography. Recent news — geopolitical events, weather disruptions, aviation strikes — is injected as live context into every agent's reasoning prompt. Free, no API key required.</p>
                    <div class="ds-used-for">Used for: News Feed trigger · Agent geopolitical context</div>
                  </div>
                  <div class="ds-item">
                    <div class="ds-item-hd">
                      <span class="ds-name">Travelpayouts / Aviasales</span>
                      <span class="ds-badge ds-badge-hist">HISTORICAL</span>
                    </div>
                    <p class="ds-desc">Historical fare baseline data for route pairs. Used to calibrate synthetic fare generation when Duffel returns no live offers, and to provide agents with seasonality context.</p>
                    <div class="ds-used-for">Used for: Synthetic fare fallback · Seasonality calibration</div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getTriggers, runSimulate, fetchRouteNews } from '@/api/airwave.js'

// ── State ─────────────────────────────────────────────────────────────────────
const origin = ref('LHR')
const destination = ref('JFK')
const tripType = ref('one_way')
const departureDate = ref('')
const returnDate = ref('')
const horizon = ref('60')
const horizons = [
  { key: '30',     label: '30 days' },
  { key: '60',     label: '60 days' },
  { key: '90',     label: '90 days' },
  { key: '180',    label: '6 months' },
  { key: 'custom', label: 'Custom' },
]

function addDays(n) {
  const d = new Date()
  d.setDate(d.getDate() + n)
  return d.toISOString().split('T')[0]
}
function setHorizon(key) {
  horizon.value = key
  if (key !== 'custom') {
    departureDate.value = addDays(parseInt(key))
    if (tripType.value === 'round_trip') returnDate.value = addDays(parseInt(key) + 7)
  }
}
// Initialise with 60-day horizon on load
setHorizon('60')

const horizonDateLabel = computed(() => {
  if (!departureDate.value) return ''
  const d = new Date(departureDate.value + 'T12:00:00')
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
})

const cabinClass = ref(1)
const selectedShocks = ref(['FUEL_SPIKE'])
const depth = ref('fast')
const triggers = ref([])
const result = ref(null)
const error = ref('')
const isLoading = ref(false)
const showAll = ref(false)
const logoFailed = ref(false)
const expandedNodes = ref(new Set())
const hoveredAlt = ref(null)
const hoveredShock = ref(null)
const hoveredTrigger = ref(null)
const hoveredAgent = ref(null)
const showValidation = ref(false)

// ── Compare mode ──────────────────────────────────────────────────────────────
const compareMode = ref(false)
const selectedShocks2 = ref([])
const result2 = ref(null)
const hoveredTrigger2 = ref(null)
const hoveredAgentA = ref(null)   // for comparison column A
const hoveredAgentB = ref(null)   // for comparison column B

// ── News Feed ────────────────────────────────────────────────────────────────
const newsItems = ref([])
const selectedNews = ref([])
const newsLoading = ref(false)
const newsError = ref('')
const newsFetchedRoute = ref('')  // tracks last fetched route to avoid re-fetch

const agentProfiles = {
  lcc_rm: {
    tag: 'Low-Cost Carrier',
    who: 'Ryanair, easyJet, Spirit, IndiGo — lean carriers running on thin margins',
    simulates: 'How LCCs immediately pass cost shocks to fares. Unhedged on fuel means every price spike hits margins directly — so fares move within 48 hours. They set the price floor that all other carriers reference.',
    signals: ['First mover — sets the market price floor', 'Raises fares within 48h of any cost shock'],
    hedge: '5%',
    share: '28%',
  },
  legacy_rm: {
    tag: 'Legacy Network Carrier',
    who: 'British Airways, Delta, Lufthansa — full-service carriers with hub networks',
    simulates: 'How full-service carriers react with a deliberate 7–14 day lag after watching LCC moves. Fuel hedging insulates them short-term, but corporate contracts and GDS distribution create pricing floors they cannot break.',
    signals: ['Follows LCC pricing moves 7–14 days later', 'Protects business class yield above leisure'],
    hedge: '75%',
    share: '42%',
  },
  corporate_buyer: {
    tag: 'Enterprise Travel Manager',
    who: 'Fortune 500 procurement managing $40M+ annual travel budgets',
    simulates: 'How corporate demand shrinks when fares exceed policy thresholds. Buyers switch preferred carriers or defer travel at a 12% price delta, pulling significant revenue from airline booking pools.',
    signals: ['Switches carrier when price delta exceeds 12%', 'Books 45–60 days in advance'],
    hedge: null,
    share: null,
  },
  leisure_traveler: {
    tag: 'Price-Elastic Consumer',
    who: 'Vacation travelers using Google Flights and Skyscanner on flexible dates',
    simulates: 'How leisure demand collapses under fare pressure. A 20% fare hike cuts booking probability by 35%, shifting volume to cheaper routes, dates, or travel modes entirely.',
    signals: ['Delays booking when fares rise >15%', 'Books last-minute when prices drop'],
    hedge: null,
    share: null,
  },
  ulcc_rm: {
    tag: 'Ultra-Low Cost Carrier',
    who: 'Wizz Air, Frontier, Allegiant — bare-bones carriers monetising every extra',
    simulates: 'How ULCCs slash base fares during disruption to steal volume, then recover margin through unbundled ancillaries. Zero fuel hedge means maximum cost exposure — and the fastest market reactions.',
    signals: ['Fastest reactor — moves within 24 hours', 'Slashes base fare, recovers via bag and seat fees'],
    hedge: '0%',
    share: '12%',
  },
  premium_boutique: {
    tag: 'Premium Boutique Airline',
    who: 'Emirates Business, Singapore Suites, Finnair Premium — product-led carriers',
    simulates: 'How premium carriers protect fare integrity under pressure. Instead of discounting, they add product value — lounge access, flexibility waivers — and rely on 90% fuel hedging to hold prices stable.',
    signals: ['Never matches LCC discounting moves', 'Adds perks instead of cutting fares'],
    hedge: '90%',
    share: '7%',
  },
  ota_platform: {
    tag: 'Online Travel Agency',
    who: 'Expedia, Booking.com, Google Flights — aggregators reaching 50M+ travellers',
    simulates: 'How OTAs amplify fare shocks by instantly re-ranking cheaper alternatives and firing price-drop alerts when fares spike. They do not control inventory but dramatically accelerate demand shifts across the market.',
    signals: ['Re-ranks cheaper alternatives immediately', 'Fires price alerts to 50M+ registered users'],
    hedge: null,
    share: null,
  },
  miles_optimizer: {
    tag: 'Loyalty & Miles Optimizer',
    who: 'Frequent flyer power users with a 200K-follower award-travel community',
    simulates: 'How award redemption demand spikes when cash fares rise, pulling booking volume out of revenue inventory into the points pool. When shared with a large audience, this ripple effect softens overall fare pressure.',
    signals: ['Triggers award search above +10% cash fare', 'Broadcasts findings to a 200K-follower audience'],
    hedge: null,
    share: null,
  },
}
const today = new Date().toISOString().split('T')[0]

// Data-source explanations shown in shock-pill tooltips
const triggerSources = {
  FUEL_SPIKE:        'WTI crude oil price via Yahoo Finance (live feed). A sharp rise in jet fuel cost activates this scenario.',
  DEMAND_COLLAPSE:   'Flight departures + booking velocity via OpenSky Network (live). A sustained drop in route demand triggers this.',
  CAPACITY_DUMP:     'Scheduled seat capacity on this route via OpenSky Network (live). More seats than passengers available.',
  ROUTE_CANCELLATION:'Flight availability via Google Flights / SerpAPI (live). Fewer flight options detected on this route.',
  EXCHANGE_RATE:     'USD/EUR, USD/GBP, USD/JPY rates via open.exchangerate-api.com (live). A significant currency swing against USD.',
  DISRUPTION_EVENT:  'Airport weather via Open-Meteo (live) + network disruption patterns. Major operational event affecting schedules.',
  NEWS_FEED:         'Google News RSS (free, geo-targeted). Recent headlines from origin and destination geography — geopolitical events, weather disruptions, aviation news — injected as live context into every agent\'s reasoning.',
}

const depths = [
  { key: 'fast',       label: 'Fast',       hint: '~2min',  rounds: 1 },
  { key: 'standard',   label: 'Standard',   hint: '~4min',  rounds: 2 },
  { key: 'deep',       label: 'Deep',       hint: '~7min',  rounds: 3 },
  { key: 'exhaustive', label: 'Exhaustive', hint: '~12min', rounds: 5 },
]

const examples = [
  { label: 'LHR → JFK  Fuel Spike',       origin: 'LHR', dest: 'JFK', shocks: ['FUEL_SPIKE'] },
  { label: 'DXB → SIN  Demand Collapse',  origin: 'DXB', dest: 'SIN', shocks: ['DEMAND_COLLAPSE'] },
  { label: 'CDG → NRT  Exchange Rate',    origin: 'CDG', dest: 'NRT', shocks: ['EXCHANGE_RATE'] },
  { label: 'LAX → ORD  Disruption',       origin: 'LAX', dest: 'ORD', shocks: ['DISRUPTION_EVENT'] },
]

const airportNames = {
  // UK & Ireland
  LHR:'London Heathrow',LGW:'London Gatwick',LCY:'London City',STN:'London Stansted',LTN:'London Luton',
  MAN:'Manchester',EDI:'Edinburgh',BHX:'Birmingham UK',GLA:'Glasgow',LBA:'Leeds Bradford',
  BRS:'Bristol',NCL:'Newcastle',LPL:'Liverpool',SOU:'Southampton',ABZ:'Aberdeen',
  DUB:'Dublin',SNN:'Shannon',ORK:'Cork',
  // USA
  JFK:'New York JFK',EWR:'Newark Liberty',LGA:'New York LaGuardia',
  LAX:'Los Angeles',SFO:'San Francisco',SJC:'San Jose',OAK:'Oakland',SMF:'Sacramento',
  ORD:"Chicago O'Hare",MDW:'Chicago Midway',ATL:'Atlanta Hartsfield',
  DFW:'Dallas Fort Worth',DAL:'Dallas Love Field',
  BOS:'Boston Logan',MIA:'Miami Intl',FLL:'Fort Lauderdale',MCO:'Orlando',TPA:'Tampa',
  SEA:'Seattle Tacoma',PDX:'Portland OR',DEN:'Denver Intl',LAS:'Las Vegas',
  PHX:'Phoenix Sky Harbor',SAN:'San Diego',
  IAD:'Washington Dulles',DCA:'Washington Reagan',BWI:'Baltimore',
  PHL:'Philadelphia',CLT:'Charlotte Douglas',MSP:'Minneapolis',DTW:'Detroit',
  IAH:'Houston Bush',HOU:'Houston Hobby',AUS:'Austin Bergstrom',
  SLC:'Salt Lake City',MSY:'New Orleans',RSW:'Fort Myers',PBI:'West Palm Beach',
  BNA:'Nashville',MCI:'Kansas City',STL:'St Louis',CMH:'Columbus',
  IND:'Indianapolis',RDU:'Raleigh Durham',PIT:'Pittsburgh',MKE:'Milwaukee',
  BUF:'Buffalo',OMA:'Omaha',MEM:'Memphis',ABQ:'Albuquerque',ELP:'El Paso',
  TUL:'Tulsa',OKC:'Oklahoma City',SAT:'San Antonio',JAX:'Jacksonville',
  BHM:'Birmingham AL',ORF:'Norfolk',RIC:'Richmond',GSO:'Greensboro',
  BDL:'Hartford',PWM:'Portland ME',
  // Canada
  YYZ:'Toronto Pearson',YVR:'Vancouver',YUL:'Montreal Trudeau',YYC:'Calgary',
  YEG:'Edmonton',YOW:'Ottawa',YHZ:'Halifax',YWG:'Winnipeg',YQB:'Quebec City',
  // Mexico & Latin America
  MEX:'Mexico City',CUN:'Cancun',GDL:'Guadalajara',MTY:'Monterrey',SJD:'Los Cabos',PVR:'Puerto Vallarta',
  BOG:'Bogota',MDE:'Medellin',CLO:'Cali',GRU:'Sao Paulo Guarulhos',GIG:'Rio de Janeiro',
  BSB:'Brasilia',SSA:'Salvador',REC:'Recife',FOR:'Fortaleza',
  EZE:'Buenos Aires Ezeiza',SCL:'Santiago',LIM:'Lima',UIO:'Quito',GYE:'Guayaquil',
  MVD:'Montevideo',ASU:'Asuncion',
  GUA:'Guatemala City',SAL:'San Salvador',SJO:'San Jose CR',PTY:'Panama City',
  SJU:'San Juan PR',MBJ:'Montego Bay',NAS:'Nassau',ANU:'Antigua',BGI:'Bridgetown',
  // Western Europe — France
  CDG:'Paris Charles de Gaulle',ORY:'Paris Orly',NCE:'Nice',LYS:'Lyon',
  MRS:'Marseille',TLS:'Toulouse',BOD:'Bordeaux',NTE:'Nantes',
  // Germany
  FRA:'Frankfurt',MUC:'Munich',DUS:'Dusseldorf',HAM:'Hamburg',
  BER:'Berlin Brandenburg',STR:'Stuttgart',CGN:'Cologne',NUE:'Nuremberg',
  // Benelux
  AMS:'Amsterdam',EIN:'Eindhoven',BRU:'Brussels',CRL:'Brussels Charleroi',
  // Switzerland & Austria
  ZRH:'Zurich',GVA:'Geneva',BSL:'Basel Mulhouse',VIE:'Vienna',SZG:'Salzburg',INN:'Innsbruck',
  // Italy
  FCO:'Rome Fiumicino',CIA:'Rome Ciampino',MXP:'Milan Malpensa',LIN:'Milan Linate',
  BGY:'Milan Bergamo',VCE:'Venice',BLQ:'Bologna',FLR:'Florence',NAP:'Naples',
  // Spain
  MAD:'Madrid Barajas',BCN:'Barcelona',PMI:'Palma Mallorca',AGP:'Malaga',
  VLC:'Valencia',ALC:'Alicante',SVQ:'Seville',TFN:'Tenerife North',TFS:'Tenerife South',
  LPA:'Las Palmas',IBZ:'Ibiza',
  // Portugal
  LIS:'Lisbon',OPO:'Porto',FAO:'Faro',
  // Greece
  ATH:'Athens',HER:'Heraklion Crete',RHO:'Rhodes',SKG:'Thessaloniki',
  // Nordics
  CPH:'Copenhagen',ARN:'Stockholm Arlanda',OSL:'Oslo Gardermoen',HEL:'Helsinki',
  GOT:'Gothenburg',BGO:'Bergen',TRD:'Trondheim',
  // Eastern Europe
  PRG:'Prague',BTS:'Bratislava',BUD:'Budapest',WAW:'Warsaw',KRK:'Krakow',GDN:'Gdansk',
  OTP:'Bucharest',SOF:'Sofia',ZAG:'Zagreb',BEG:'Belgrade',SKP:'Skopje',TIA:'Tirana',
  KBP:'Kyiv Boryspil',LWO:'Lviv',ODS:'Odessa',
  // Middle East
  DXB:'Dubai Intl',AUH:'Abu Dhabi',SHJ:'Sharjah',DOH:'Doha Hamad',
  KWI:'Kuwait City',BAH:'Bahrain',AMM:'Amman Queen Alia',BEY:'Beirut',
  TLV:'Tel Aviv Ben Gurion',RUH:'Riyadh',JED:'Jeddah',DMM:'Dammam',MCT:'Muscat',
  CAI:'Cairo',HRG:'Hurghada',SSH:'Sharm el-Sheikh',
  // Africa
  JNB:'Johannesburg OR Tambo',CPT:'Cape Town',DUR:'Durban',
  NBO:'Nairobi',ADD:'Addis Ababa',CMN:'Casablanca',
  LOS:'Lagos',ABV:'Abuja',ACC:'Accra',DKR:'Dakar',
  EBB:'Entebbe',DAR:'Dar es Salaam',LUN:'Lusaka',HRE:'Harare',MRU:'Mauritius',
  // South Asia
  BOM:'Mumbai',DEL:'Delhi IGI',BLR:'Bengaluru',MAA:'Chennai',
  CCU:'Kolkata',HYD:'Hyderabad',COK:'Kochi',AMD:'Ahmedabad',
  CMB:'Colombo',DAC:'Dhaka',KTM:'Kathmandu',ISB:'Islamabad',KHI:'Karachi',LHE:'Lahore',
  // Southeast Asia
  SIN:'Singapore Changi',KUL:'Kuala Lumpur',CGK:'Jakarta',BKK:'Bangkok Suvarnabhumi',
  DMK:'Bangkok Don Mueang',HKT:'Phuket',CNX:'Chiang Mai',
  SGN:'Ho Chi Minh City',HAN:'Hanoi',DAD:'Da Nang',
  MNL:'Manila',CEB:'Cebu',REP:'Siem Reap',PNH:'Phnom Penh',RGN:'Yangon',
  // East Asia
  HKG:'Hong Kong',MFM:'Macau',
  PEK:'Beijing Capital',PKX:'Beijing Daxing',PVG:'Shanghai Pudong',SHA:'Shanghai Hongqiao',
  CAN:'Guangzhou',SZX:'Shenzhen',CTU:'Chengdu',CKG:'Chongqing',WUH:'Wuhan',
  XMN:'Xiamen',NKG:'Nanjing',HGH:'Hangzhou',SYX:'Sanya',
  TPE:'Taipei Taoyuan',TSA:'Taipei Songshan',KHH:'Kaohsiung',
  ICN:'Seoul Incheon',GMP:'Seoul Gimpo',PUS:'Busan',
  NRT:'Tokyo Narita',HND:'Tokyo Haneda',KIX:'Osaka Kansai',NGO:'Nagoya',FUK:'Fukuoka',CTS:'Sapporo',
  // Oceania
  SYD:'Sydney Kingsford Smith',MEL:'Melbourne',BNE:'Brisbane',PER:'Perth',
  ADL:'Adelaide',CBR:'Canberra',OOL:'Gold Coast',CNS:'Cairns',
  AKL:'Auckland',CHC:'Christchurch',WLG:'Wellington',ZQN:'Queenstown',
  NAN:'Nadi Fiji',
  // Russia & Central Asia
  SVO:'Moscow Sheremetyevo',DME:'Moscow Domodedovo',LED:'St Petersburg',
  ALA:'Almaty',TAS:'Tashkent',GYD:'Baku',EVN:'Yerevan',TBS:'Tbilisi',
  FRU:'Bishkek',
}

const loadingMsgs = [
  'Seeding live market data…',
  'Fetching NDC fares from Duffel…',
  'Checking weather at origin and destination…',
  'Pulling historical fare baseline…',
  'Building route demand model…',
  'Running P&L shock cascade…',
  'Riley Chen (LCC): pricing strategy under shock…',
  'Marcus Webb (legacy carrier): hedge position and yield response…',
  'Priya Sharma (corporate buyer): policy threshold analysis…',
  'Sam Park (leisure traveller): price elasticity response…',
  'Yara Okonkwo (ULCC): ancillary recovery modelling…',
  'Elena Vasquez (premium carrier): fare integrity decision…',
  'Nikos Papadopoulos (OTA): redistribution and re-ranking…',
  'Tariq Al-Hassan (miles optimizer): award redemption impact…',
  'Synthesising 8-agent market consensus…',
  'Writing fare intelligence brief…',
]
const loadingMsg = ref(loadingMsgs[0])
let _lt = null

// ── Computed ──────────────────────────────────────────────────────────────────
const originName = computed(() => airportNames[origin.value] || '')
const destName   = computed(() => airportNames[destination.value] || '')
const _IATA = /^[A-Z]{3}$/
const canPredict = computed(() =>
  _IATA.test(origin.value) &&
  _IATA.test(destination.value) &&
  origin.value !== destination.value &&
  selectedShocks.value.length > 0 &&
  !!departureDate.value &&
  (tripType.value !== 'round_trip' || !!returnDate.value)
)
const cabinLabel = computed(() =>
  ({1:'Economy',2:'Prem. Economy',3:'Business',4:'First'})[cabinClass.value]||'Economy'
)
const depthEta = computed(() =>
  ({fast:'~2 minutes',standard:'~4 minutes',deep:'~7 minutes',exhaustive:'~12 minutes'})[depth.value]
)
const consensusLabel = computed(() => ({
  strong_raise:  '⬆ Strong rise',
  moderate_raise:'↗ Moderate rise',
  hold:          '→ Holding steady',
  moderate_drop: '↘ Moderate drop',
  strong_drop:   '⬇ Strong drop',
})[result.value?.agent_consensus] || result.value?.agent_consensus || '')

const consensusLabel2 = computed(() => ({
  strong_raise:  '⬆ Strong rise',
  moderate_raise:'↗ Moderate rise',
  hold:          '→ Holding steady',
  moderate_drop: '↘ Moderate drop',
  strong_drop:   '⬇ Strong drop',
})[result2.value?.agent_consensus] || result2.value?.agent_consensus || '')

const mergedCascadeKeys = computed(() => {
  if (!result.value?.cascade_impacts && !result2.value?.cascade_impacts) return []
  const keysA = Object.keys(result.value?.cascade_impacts || {})
  const keysB = Object.keys(result2.value?.cascade_impacts || {})
  const all = [...new Set([...keysA, ...keysB])]
  return all.sort((a, b) => {
    const ia = Math.max(Math.abs(result.value?.cascade_impacts?.[a]?.impact || 0), Math.abs(result2.value?.cascade_impacts?.[a]?.impact || 0))
    const ib = Math.max(Math.abs(result.value?.cascade_impacts?.[b]?.impact || 0), Math.abs(result2.value?.cascade_impacts?.[b]?.impact || 0))
    return ib - ia
  }).slice(0, 8)
})

// Returns true when the two scenarios diverge meaningfully on this cascade node
function cascadeRowDiverges(key) {
  const a = result.value?.cascade_impacts?.[key]?.impact
  const b = result2.value?.cascade_impacts?.[key]?.impact
  if (a == null || b == null) return false
  // Diverge = different direction, or same direction but 1+ severity tier apart (each tier ~0.15)
  const sameDir = (a >= 0) === (b >= 0)
  const bigDiff = Math.abs(a - b) >= 0.15
  return !sameDir || bigDiff
}

// Warns when Scenario A and B have identical shock sets (comparison would be meaningless)
const sameShocksWarning = computed(() => {
  if (!compareMode.value) return false
  const a = [...selectedShocks.value].sort().join(',')
  const b = [...selectedShocks2.value].sort().join(',')
  return a === b
})

const ontimeColor = computed(() => {
  const p = result.value?.disruption?.on_time_probability || 1
  if (p >= 0.8) return '#10b981'
  if (p >= 0.6) return '#f59e0b'
  if (p >= 0.4) return '#f97316'
  return '#ef4444'
})

const visibleActions = computed(() =>
  showAll.value
    ? result.value?.agent_actions||[]
    : (result.value?.agent_actions||[]).slice(0,4)
)

const topCascade = computed(() => {
  if (!result.value?.cascade_impacts) return {}
  const e = Object.entries(result.value.cascade_impacts)
  e.sort((a,b) => Math.abs(b[1].impact) - Math.abs(a[1].impact))
  return Object.fromEntries(e.slice(0,8))
})

const shockBannerItems = computed(() => {
  if (!result.value?.trigger_explains) return []
  return Object.entries(result.value.trigger_explains)
    .filter(([, v]) => v)
    .map(([id, explain]) => {
      const t = triggers.value.find(tr => tr.id === id)
      return { id, explain, icon: t?.icon || '📊', label: t?.label || id }
    })
})

// ── Watchers ──────────────────────────────────────────────────────────────────
watch(result, () => {
  logoFailed.value = false
  expandedNodes.value = new Set()
  showAll.value = false
})

// ── Methods ───────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const r = await getTriggers()
    if (r.success) triggers.value = r.data
  } catch {}
})

// Auto-fetch news when NEWS_FEED shock is selected and route is valid
// deep:true so array mutations (push/splice in toggleShock) are detected
watch([selectedShocks, selectedShocks2, origin, destination], () => {
  const needsNews = (
    selectedShocks.value.includes('NEWS_FEED') ||
    selectedShocks2.value.includes('NEWS_FEED')
  )
  const routeKey = `${origin.value}-${destination.value}`
  if (
    needsNews &&
    origin.value.length === 3 &&
    destination.value.length === 3 &&
    routeKey !== newsFetchedRoute.value
  ) {
    fetchNewsForRoute()
  }
  // Clear if NEWS_FEED is deselected from both
  if (!needsNews) {
    newsItems.value = []
    selectedNews.value = []
    newsFetchedRoute.value = ''
  }
}, { deep: true })

async function fetchNewsForRoute() {
  if (!origin.value || !destination.value) return
  const routeKey = `${origin.value}-${destination.value}`
  newsLoading.value = true
  newsError.value = ''
  try {
    const res = await fetchRouteNews(origin.value, destination.value)
    if (res.success) {
      newsItems.value = res.data.items || []
      newsFetchedRoute.value = routeKey
      // Auto-select top 2 items
      selectedNews.value = newsItems.value.slice(0, 2).map((_, i) => i)
    } else {
      newsError.value = res.error || 'Could not fetch news'
    }
  } catch (e) {
    newsError.value = 'News fetch failed — check SERPAPI_KEY'
  } finally {
    newsLoading.value = false
  }
}

function toggleNewsItem(idx) {
  const i = selectedNews.value.indexOf(idx)
  if (i >= 0) selectedNews.value.splice(i, 1)
  else selectedNews.value.push(idx)
}

function swapRoutes() {
  [origin.value, destination.value] = [destination.value, origin.value]
}

// ── Export ───────────────────────────────────────────────────────────────────
const copied = ref('')

function _buildReport(r, r2) {
  const horizonLabel = horizon.value !== 'custom' ? `Within ${horizon.value} days (≈ ${horizonDateLabel.value})` : horizonDateLabel.value
  const shockNames = t => (r.trigger_ids||[t.trigger_id]).map(id => triggers.value.find(x=>x.id===id)?.label||id).join(' + ')
  const bar = '─'.repeat(56)

  function _scenario(res, label) {
    const delta = res.fare_delta >= 0 ? `▲ +${res.fare_delta_pct}%` : `▼ ${res.fare_delta_pct}%`
    const cascadeLines = Object.entries(res.cascade_impacts||{})
      .map(([k,v]) => `  ${k.padEnd(24)} ${v.direction==='up'?'▲':'▼'} ${Math.abs(Math.round(v.magnitude*100))}%`)
      .join('\n')
    const agentLines = (res.agent_actions||[])
      .map(a => `  [Rd${a.round}] ${a.agent_name.padEnd(26)} ${a.decision}  (${a.magnitude_pct>0?'+':''}${a.magnitude_pct}%)`)
      .join('\n')
    const narrativeSnippet = (res.narrative||'').replace(/#+\s*/g,'').substring(0, 600)
    return [
      label ? `SCENARIO ${label}` : 'SIMULATION',
      `Shock:      ${shockNames(res)}`,
      `Live fare:  $${res.seed_fare.toLocaleString()}   →   AI prediction: $${res.predicted_fare.toLocaleString()}   ${delta}`,
      `Confidence: ${Math.round(res.confidence*100)}%   Consensus: ${(res.agent_consensus||'').toUpperCase()}   Days to effect: ${res.days_to_effect}`,
      '',
      'CASCADE IMPACTS',
      cascadeLines || '  (none)',
      '',
      'AGENT DECISIONS',
      agentLines || '  (none)',
      '',
      'AI ANALYSIS (excerpt)',
      narrativeSnippet + (res.narrative?.length > 600 ? '…' : ''),
    ].join('\n')
  }

  const header = [
    'AIRWAVE SCENARIO INTELLIGENCE REPORT',
    bar,
    `Route:      ${r.route}`,
    `Horizon:    ${horizonLabel}`,
    `Cabin:      ${cabinLabel.value}`,
    `Generated:  ${new Date().toUTCString()}`,
    `Sim ID:     ${r.simulation_id}${r2 ? ' / ' + r2.simulation_id : ''}`,
    bar,
    '',
  ].join('\n')

  const body = r2
    ? _scenario(r, 'A') + '\n\n' + bar + '\n\n' + _scenario(r2, 'B')
    : _scenario(r, null)

  return header + body + '\n\n' + bar + '\n© AirWave Scenario Intelligence\n'
}

async function copyReport(r, r2) {
  const text = _buildReport(r, r2)
  try {
    await navigator.clipboard.writeText(text)
    copied.value = 'text'
    setTimeout(() => { copied.value = '' }, 2500)
  } catch {
    // Fallback for non-secure contexts
    const el = document.createElement('textarea')
    el.value = text
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
    copied.value = 'text'
    setTimeout(() => { copied.value = '' }, 2500)
  }
}

function downloadJson(r, r2) {
  const payload = r2 ? { scenario_a: r, scenario_b: r2 } : r
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `airwave_${r.simulation_id}${r2 ? '_vs_' + r2.simulation_id : ''}.json`
  a.click()
  URL.revokeObjectURL(url)
  copied.value = 'json'
  setTimeout(() => { copied.value = '' }, 2500)
}

// ── Export label helpers ──────────────────────────────────────────────────────
function _shockLabels(r) {
  return (r.trigger_ids || [r.trigger_id])
    .map(id => triggers.value.find(t => t.id === id)?.label || id)
    .join(' + ')
}
// ── Simulation history ────────────────────────────────────────────────────────
const HISTORY_KEY = 'aw_sim_history'
const HISTORY_MAX = 10
const simHistory = ref((() => { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch { return [] } })())
const showHistory = ref(false)
const showMethodology = ref(false)
const methodTab = ref('pipeline')

function pushHistory(res, res2 = null) {
  const entry = {
    id: Date.now(),
    ts: new Date().toISOString(),
    route: res.route,
    shocksA: _shockLabels(res),
    shocksB: res2 ? _shockLabels(res2) : null,
    seedFare: res.seed_fare,
    predictedFare: res.predicted_fare,
    fareDelta: res.fare_delta,
    fareDeltaPct: res.fare_delta_pct,
    consensus: res.agent_consensus,
    resultA: res,
    resultB: res2,
  }
  simHistory.value = [entry, ...simHistory.value].slice(0, HISTORY_MAX)
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(simHistory.value)) } catch {}
}

function recallHistory(entry) {
  result.value = entry.resultA
  result2.value = entry.resultB || null
  if (entry.resultB) compareMode.value = true
  showHistory.value = false
  setTimeout(() => document.querySelector('.pred-band')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80)
}

function clearHistory() {
  simHistory.value = []
  try { localStorage.removeItem(HISTORY_KEY) } catch {}
}

const exportLabel = computed(() => {
  if (!result.value) return ''
  const win = horizon.value !== 'custom' ? `${horizon.value}-day window` : horizonDateLabel.value
  return `${result.value.route}  ·  ${_shockLabels(result.value)}  ·  ${win}`
})
const exportLabelCompare = computed(() => {
  if (!result.value || !result2.value) return ''
  const win = horizon.value !== 'custom' ? `${horizon.value}-day window` : horizonDateLabel.value
  return `${result.value.route}  ·  ${_shockLabels(result.value)} vs ${_shockLabels(result2.value)}  ·  ${win}`
})

// ── PDF export ────────────────────────────────────────────────────────────────
function exportPdf(r, r2) {
  const isCompare = !!r2
  const shocksA = _shockLabels(r)
  const shocksB = r2 ? _shockLabels(r2) : ''
  const horizonLabel = horizon.value !== 'custom' ? `${horizon.value}-day window` : horizonDateLabel.value
  const dateStr = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
  const cabin = cabinLabel.value

  function agentRows(actions) {
    return (actions || []).slice(0, 8).map(a => {
      const color = a.magnitude_pct > 0 ? '#b91c1c' : '#15803d'
      return `<tr>
        <td><strong>${a.agent_name}</strong></td>
        <td style="color:#555">${agentProfiles[a.agent_id]?.tag || ''}</td>
        <td style="white-space:nowrap;font-weight:700">${a.decision.replace(/_/g,' ')}</td>
        <td style="white-space:nowrap;font-weight:700;color:${color}">${a.magnitude_pct > 0 ? '+' : ''}${a.magnitude_pct}%</td>
        <td>${(a.reasoning || '').slice(0, 120)}${(a.reasoning?.length || 0) > 120 ? '…' : ''}</td>
      </tr>`
    }).join('')
  }

  function cascadeRows(impacts) {
    if (!impacts) return ''
    return Object.entries(impacts).slice(0, 7).map(([k, imp]) =>
      `<tr>
        <td>${imp.plain_icon || '📊'} ${imp.plain_label || k}</td>
        <td style="font-weight:700;color:${imp.impact >= 0 ? '#b91c1c' : '#15803d'}">${severityLabel(imp.impact)}</td>
        <td style="color:#555">~${imp.days_to_effect}d</td>
      </tr>`
    ).join('')
  }

  function narHtml(sections) {
    return (sections || []).map(s => s.isWatchList
      ? `<p class="nh">${s.title}</p><ul>${(s.bullets || []).map(b => `<li>${b}</li>`).join('')}</ul>`
      : `<p class="nh">${s.title}</p><p class="nb">${s.body}</p>`
    ).join('')
  }

  const css = `
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'JetBrains Mono',Consolas,monospace;font-size:10.5px;color:#1a1a1a;padding:28px 36px;background:#fff;line-height:1.5}
    .hdr{border-bottom:2px solid #000;padding-bottom:12px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:flex-end}
    .bn{font-size:13px;font-weight:800;letter-spacing:1px}
    .bs{font-size:8.5px;color:#888;letter-spacing:1.5px;margin-top:3px}
    .hr{text-align:right;font-size:9.5px;color:#666;line-height:1.7}
    h1{font-size:17px;font-weight:800;letter-spacing:-.3px;margin-bottom:3px}
    .meta{font-size:9.5px;color:#888;margin-bottom:18px}
    .sec{margin-bottom:18px}
    .st{font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#888;border-bottom:1px solid #e0e0e0;padding-bottom:4px;margin-bottom:9px}
    .fr{display:flex;gap:20px;align-items:center;padding:10px 14px;background:#f7f7f7;margin-bottom:4px}
    .fi{display:flex;flex-direction:column;gap:1px}
    .fl{font-size:8px;color:#999;letter-spacing:.5px;text-transform:uppercase}
    .fv{font-size:20px;font-weight:800;letter-spacing:-1px}
    .fv.up{color:#b91c1c}.fv.dn{color:#15803d}
    .arr{font-size:16px;color:#aaa;margin:0 4px}
    .chip{display:inline-block;padding:2px 9px;font-size:11px;font-weight:700;border-radius:2px}
    .cu{background:#fee2e2;color:#b91c1c}.cd{background:#dcfce7;color:#15803d}
    .cf{font-size:9.5px;color:#666;margin-top:4px}
    table{width:100%;border-collapse:collapse;font-size:9.5px}
    th{background:#f5f5f5;border:1px solid #e5e5e5;padding:4px 7px;text-align:left;font-size:8px;letter-spacing:.5px;text-transform:uppercase;color:#777;font-weight:700}
    td{border:1px solid #e5e5e5;padding:4px 7px;vertical-align:top}
    .nh{font-size:8px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#666;margin:11px 0 4px}
    .nb{font-size:10.5px;line-height:1.7;color:#333;margin-bottom:5px}
    ul{padding-left:14px;margin:3px 0}li{font-size:10.5px;line-height:1.65;color:#333;margin-bottom:2px}
    .cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
    .sl{display:inline-block;padding:2px 7px;font-size:8px;font-weight:700;letter-spacing:1px;margin-bottom:7px}
    .sa{background:#dbeafe;color:#1d4ed8}.sb{background:#fce7f3;color:#be185d}
    .ftr{border-top:1px solid #e5e5e5;padding-top:10px;margin-top:24px;display:flex;justify-content:space-between;font-size:8.5px;color:#aaa}
    @media print{body{padding:14px 20px}@page{margin:.8cm;size:A4}}
  `

  const singleBody = `
    <div class="sec">
      <div class="st">Fare simulation</div>
      <div class="fr">
        <div class="fi"><span class="fl">Live fare</span><span class="fv">$${r.seed_fare.toLocaleString()}</span></div>
        <span class="arr">${r.fare_delta >= 0 ? '→↑' : '→↓'}</span>
        <div class="fi"><span class="fl">Forecast</span><span class="fv ${r.fare_delta >= 0 ? 'up' : 'dn'}">$${r.predicted_fare.toLocaleString()}</span></div>
        <span class="chip ${r.fare_delta >= 0 ? 'cu' : 'cd'}">${r.fare_delta >= 0 ? '▲' : '▼'} ${Math.abs(r.fare_delta_pct)}%</span>
      </div>
      <p class="cf">Confidence: ${Math.round(r.confidence * 100)}% · ${shocksA} · ${cabin}</p>
    </div>
    <div class="sec">
      <div class="st">Market agent decisions</div>
      <table><thead><tr><th>Agent</th><th>Role</th><th>Decision</th><th>Move</th><th>Reasoning</th></tr></thead>
      <tbody>${agentRows(r.agent_actions)}</tbody></table>
    </div>
    <div class="sec">
      <div class="st">P&L shock cascade</div>
      <table><thead><tr><th>P&L Node</th><th>Impact</th><th>Timeline</th></tr></thead>
      <tbody>${cascadeRows(r.cascade_impacts)}</tbody></table>
    </div>
    <div class="sec">
      <div class="st">Fare intelligence brief</div>
      ${narHtml(narrativeSections.value)}
    </div>`

  const compareBody = `
    <div class="cols" style="margin-bottom:16px">
      <div>
        <span class="sl sa">SCENARIO A — ${shocksA}</span>
        <div class="fr" style="padding:8px 12px">
          <div class="fi"><span class="fl">Seed</span><span style="font-size:16px;font-weight:800">$${r.seed_fare.toLocaleString()}</span></div>
          <span class="arr">${r.fare_delta >= 0 ? '↑' : '↓'}</span>
          <div class="fi"><span class="fl">Forecast</span><span style="font-size:16px;font-weight:800;color:${r.fare_delta >= 0 ? '#b91c1c' : '#15803d'}">$${r.predicted_fare.toLocaleString()}</span></div>
          <span class="chip ${r.fare_delta >= 0 ? 'cu' : 'cd'}" style="font-size:10px">${r.fare_delta >= 0 ? '▲' : '▼'} ${Math.abs(r.fare_delta_pct)}%</span>
        </div>
        <p class="cf">Confidence: ${Math.round(r.confidence * 100)}%</p>
      </div>
      <div>
        <span class="sl sb">SCENARIO B — ${shocksB}</span>
        <div class="fr" style="padding:8px 12px">
          <div class="fi"><span class="fl">Seed</span><span style="font-size:16px;font-weight:800">$${r2.seed_fare.toLocaleString()}</span></div>
          <span class="arr">${r2.fare_delta >= 0 ? '↑' : '↓'}</span>
          <div class="fi"><span class="fl">Forecast</span><span style="font-size:16px;font-weight:800;color:${r2.fare_delta >= 0 ? '#b91c1c' : '#15803d'}">$${r2.predicted_fare.toLocaleString()}</span></div>
          <span class="chip ${r2.fare_delta >= 0 ? 'cu' : 'cd'}" style="font-size:10px">${r2.fare_delta >= 0 ? '▲' : '▼'} ${Math.abs(r2.fare_delta_pct)}%</span>
        </div>
        <p class="cf">Confidence: ${Math.round(r2.confidence * 100)}%</p>
      </div>
    </div>
    <div class="sec">
      <div class="st">Agent decisions by scenario</div>
      <div class="cols">
        <table><thead><tr><th colspan="4">Scenario A — ${shocksA}</th></tr><tr><th>Agent</th><th>Decision</th><th>Move</th><th>Reasoning</th></tr></thead><tbody>${agentRows(r.agent_actions)}</tbody></table>
        <table><thead><tr><th colspan="4">Scenario B — ${shocksB}</th></tr><tr><th>Agent</th><th>Decision</th><th>Move</th><th>Reasoning</th></tr></thead><tbody>${agentRows(r2.agent_actions)}</tbody></table>
      </div>
    </div>
    <div class="sec">
      <div class="st">Fare intelligence briefs</div>
      <div class="cols">
        <div><span class="sl sa">A</span>${narHtml(narrativeSections.value)}</div>
        <div><span class="sl sb">B</span>${narHtml(narrativeSections2.value)}</div>
      </div>
    </div>`

  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>AirWave — ${r.route}</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>${css}</style></head>
  <body>
    <div class="hdr">
      <div><div class="bn">MIROFISH AIRWAVE</div><div class="bs">FARE SCENARIO INTELLIGENCE · BY S·ASHWATH</div></div>
      <div class="hr">${dateStr}<br>${horizonLabel} · ${cabin}</div>
    </div>
    <h1>${r.route}${isCompare ? ' — Scenario Comparison' : ' — ' + shocksA}</h1>
    <p class="meta">${isCompare ? shocksA + '  vs  ' + shocksB : shocksA} · ${dateStr}</p>
    ${isCompare ? compareBody : singleBody}
    <div class="ftr">
      <span>MiroFish AirWave · ${r.simulation_id}${r2 ? ' / ' + r2.simulation_id : ''}</span>
      <span>S·Ashwath Scenario Intelligence · ${dateStr}</span>
    </div>
  </body></html>`

  const win = window.open('', '_blank', 'width=960,height=720')
  if (!win) { alert('Allow pop-ups from this page to export PDF, then try again.'); return }
  win.document.write(html)
  win.document.close()
  win.addEventListener('load', () => setTimeout(() => win.print(), 600))
}

function toggleShock(id) {
  const idx = selectedShocks.value.indexOf(id)
  if (idx >= 0) {
    if (selectedShocks.value.length > 1) selectedShocks.value.splice(idx, 1)
    // Don't deselect the last one
  } else {
    selectedShocks.value.push(id)
  }
}

function toggleShock2(id) {
  const idx = selectedShocks2.value.indexOf(id)
  if (idx >= 0) {
    if (selectedShocks2.value.length > 1) selectedShocks2.value.splice(idx, 1)
  } else {
    selectedShocks2.value.push(id)
  }
}

function toggleNode(key) {
  const s = new Set(expandedNodes.value)
  if (s.has(key)) s.delete(key)
  else s.add(key)
  expandedNodes.value = s
}

function applyExample(ex) {
  origin.value = ex.origin
  destination.value = ex.dest
  selectedShocks.value = [...ex.shocks]
}

function fmtDate(d) {
  if (!d) return ''
  try { return new Date(d+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}) }
  catch { return d }
}
function fmtDur(m) {
  if (!m) return ''
  return `${Math.floor(m/60)}h ${m%60}m`
}
function trunc(s, n) {
  if (!s) return ''
  return s.length > n ? s.slice(0,n-1)+'…' : s
}
function riskColor(lvl) {
  return {low:'#10b981',moderate:'#f59e0b',high:'#f97316',severe:'#ef4444'}[lvl]||'#64748b'
}
function agentColor(id) {
  return {
    lcc_rm:           '#6366f1',
    legacy_rm:        '#0ea5e9',
    corporate_buyer:  '#8b5cf6',
    leisure_traveler: '#10b981',
    ulcc_rm:          '#f97316',
    premium_boutique: '#ec4899',
    ota_platform:     '#14b8a6',
    miles_optimizer:  '#f59e0b',
  }[id] || '#64748b'
}
function severityLabel(impact) {
  const abs = Math.abs(impact)
  const arrow = impact >= 0 ? '↑' : '↓'
  if (abs >= 0.5) return `${arrow} Very strong`
  if (abs >= 0.25) return `${arrow} Strong`
  if (abs >= 0.1)  return `${arrow} Moderate`
  return `${arrow} Mild`
}
function severityClass(impact) {
  return impact >= 0 ? 'sev-up' : 'sev-dn'
}
function impactInterpret(imp) {
  const dir = imp.impact >= 0 ? 'up' : 'down'
  const label = imp.plain_label || ''
  const days = imp.days_to_effect
  const conf = Math.round(imp.confidence * 100)
  const confWord = conf >= 80 ? 'high confidence' : conf >= 60 ? 'moderate confidence' : 'lower confidence'
  const msgs = {
    'Traveler Demand': {
      up: 'More travelers are searching and booking this route — airlines will likely raise prices to capitalize.',
      down: 'Fewer travelers are searching this route — airlines may cut prices to fill empty seats.',
    },
    'Seat Occupancy': {
      up: 'Flights on this route are filling up — airlines have less reason to discount, fares hold or rise.',
      down: 'Too many empty seats — airlines will likely discount to improve how full the plane is.',
    },
    'Smart Pricing': {
      up: 'Automated pricing systems are moving fares upward — cheaper seat classes are being closed.',
      down: 'Pricing algorithms are releasing discounted seats — budget options may open up.',
    },
    'Add-on Revenue': {
      up: 'Fees for bags, seat upgrades, and extras are rising alongside base fares.',
      down: 'Add-on revenue is softening — airlines may adjust base fares to compensate.',
    },
    'Cargo Revenue': {
      up: 'Strong cargo demand is helping cover airline costs — passenger fares may stay more stable.',
      down: 'Weaker cargo revenue removes a cost buffer — more pressure falls on ticket prices.',
    },
    'Fuel Bills': {
      up: 'Jet fuel — the airline\'s single biggest cost — is rising sharply. Fare hikes typically follow within days.',
      down: 'Fuel costs are easing, giving airlines room to hold fares steady or even compete on price.',
    },
    'Staff Costs': {
      up: 'Overtime, crew rescheduling, and extra agents are spiking — these costs add up quickly and pressure fares.',
      down: 'Labour costs are easing, giving airlines more financial breathing room.',
    },
    'Booking Fees': {
      up: 'OTA commissions and GDS fees are adding $10–25 per ticket to airline costs.',
      down: 'Distribution costs are falling as booking volumes normalise.',
    },
    'Revenue Per Seat': {
      up: 'Airlines are earning more per seat sold — a healthy sign that pricing power is intact.',
      down: 'Revenue per seat is declining — the airline is earning less on each ticket, creating pressure to raise fares.',
    },
    'Cost Per Seat': {
      up: 'Per-seat costs are rising and squeezing margins — the airline is likely to raise fares to stay profitable.',
      down: 'Per-seat costs are falling — airlines can price more competitively without hurting profitability.',
    },
    'Profit Margin': {
      up: 'Margins are recovering — fare pressure may ease once the airline feels financially stable.',
      down: 'Margins are near zero or negative — airlines are very likely to raise fares to avoid losses.',
    },
    'Route Network': {
      up: 'This shock is amplifying price pressure across connecting routes and hub airports.',
      down: 'Reduced network activity may soften fare pressure on connecting and feeder routes.',
    },
  }
  const sentence = msgs[label]?.[dir] || (dir === 'up'
    ? 'This effect is driving costs upward, which may translate to higher fares.'
    : 'This effect is easing pressure on the airline, which may translate to more competitive fares.')
  return `${sentence} Predicted effect in ~${days} day${days===1?'':'s'} (${confWord}, ${conf}%).`
}
function sourceLabel(key, src) {
  const s = (src || '').toLowerCase()
  if (key === 'fare') {
    if (s.startsWith('duffel')) return s.includes('test') ? '🛫 Prices: Duffel (test)' : '🛫 Prices: Duffel NDC'
    if (s.startsWith('kiwi'))   return '🛫 Prices: Kiwi.com'
    if (s.startsWith('serpapi')) return '🛫 Prices: Google Flights'
    return '🛫 Prices: estimated'
  }
  if (key === 'demand')  return src==='opensky' ? '📡 Demand: OpenSky' : '📡 Demand: estimated'
  if (key === 'history') return src==='travelpayouts' ? '📅 History: Travelpayouts' : '📅 History: estimated'
  if (key === 'macro')   return src==='live' ? '📊 Markets: live' : src==='partial' ? '📊 Markets: partial live' : '📊 Markets: estimated'
  return `${key}: ${src}`
}

// Parse LLM narrative markdown (## Section\nBody...) into structured sections
const narrativeSections = computed(() => {
  const raw = result.value?.narrative
  if (!raw) return []
  const sections = []
  // Split on ## headers
  const chunks = raw.split(/\n(?=##\s)/)
  for (const chunk of chunks) {
    const lines = chunk.trim().split('\n')
    const headerLine = lines[0] || ''
    const title = headerLine.replace(/^#+\s*/, '').trim()
    if (!title) continue
    const body = lines.slice(1).join('\n').trim()
    const isWatchList = /watch|signal|monitor|look for/i.test(title)
    if (isWatchList) {
      // Parse numbered or bulleted list items
      const bullets = body
        .split('\n')
        .map(l => l.replace(/^[\d\.\-\*\•\→]+\s*/, '').trim())
        .filter(l => l.length > 3)
      sections.push({ title, body, bullets, isWatchList: true })
    } else {
      sections.push({ title, body, isWatchList: false })
    }
  }
  // If no ## headers found, treat whole text as one unlabelled block
  if (sections.length === 0 && raw.trim()) {
    sections.push({ title: 'Analysis', body: raw.trim(), isWatchList: false })
  }
  return sections
})

// Identical parser for Scenario B narrative
const narrativeSections2 = computed(() => {
  const raw = result2.value?.narrative
  if (!raw) return []
  const sections = []
  const chunks = raw.split(/\n(?=##\s)/)
  for (const chunk of chunks) {
    const lines = chunk.trim().split('\n')
    const title = lines[0].replace(/^#+\s*/, '').trim()
    if (!title) continue
    const body = lines.slice(1).join('\n').trim()
    const isWatchList = /watch|signal|monitor|look for/i.test(title)
    if (isWatchList) {
      const bullets = body.split('\n').map(l => l.replace(/^[\d\.\-\*\•\→]+\s*/, '').trim()).filter(l => l.length > 3)
      sections.push({ title, body, bullets, isWatchList: true })
    } else {
      sections.push({ title, body, isWatchList: false })
    }
  }
  if (sections.length === 0 && raw.trim()) {
    sections.push({ title: 'Analysis', body: raw.trim(), isWatchList: false })
  }
  return sections
})

function sectionIcon(title) {
  const t = title.toLowerCase()
  if (/what happened|trigger|shock|event/i.test(t))  return '⚡'
  if (/airline|respond|carrier|react/i.test(t))       return '✈'
  if (/fare|price|cost|passenger/i.test(t))           return '💰'
  if (/watch|signal|monitor/i.test(t))                return '◈'
  if (/risk|warning|caution/i.test(t))                return '⚠'
  return '◆'
}

function handlePredict() {
  showValidation.value = true
  if (!canPredict.value || isLoading.value) return
  runSimulation()
}

async function runSimulation() {
  if (!canPredict.value || isLoading.value) return
  error.value = ''; result.value = null; result2.value = null; isLoading.value = true
  let i = 0; loadingMsg.value = loadingMsgs[0]
  _lt = setInterval(() => { i=(i+1)%loadingMsgs.length; loadingMsg.value=loadingMsgs[i] }, 3500)
  const rounds = depths.find(d => d.key === depth.value)?.rounds ?? 1

  // Build news context from selected headlines
  const newsContext = selectedNews.value
    .map(i => newsItems.value[i])
    .filter(Boolean)
    .map(item => `${item.title}${item.source ? ` (${item.source})` : ''}`)

  const basePayload = {
    origin: origin.value,
    destination: destination.value,
    departure_date: departureDate.value || undefined,
    return_date: returnDate.value || undefined,
    trip_type: tripType.value,
    cabin_class: cabinClass.value,
    rounds,
    news_context: newsContext.length > 0 ? newsContext : undefined,
  }

  try {
    if (compareMode.value && selectedShocks2.value.length > 0) {
      // Run both scenarios in parallel
      const [resA, resB] = await Promise.all([
        runSimulate({ ...basePayload, trigger_ids: selectedShocks.value, trigger_id: selectedShocks.value[0] }),
        runSimulate({ ...basePayload, trigger_ids: selectedShocks2.value, trigger_id: selectedShocks2.value[0] }),
      ])
      if (resA.success) result.value = resA.data
      else { error.value = `Scenario A: ${resA.error || 'Simulation failed'}`; return }
      if (resB.success) {
        result2.value = resB.data
        pushHistory(resA.data, resB.data)
      } else { error.value = `Scenario B: ${resB.error || 'Simulation failed'}` }
    } else {
      const res = await runSimulate({ ...basePayload, trigger_ids: selectedShocks.value, trigger_id: selectedShocks.value[0] })
      if (res.success) {
        result.value = res.data
        pushHistory(res.data)
      } else error.value = res.error || 'Simulation failed'
    }
  } catch (e) {
    console.error('[AirWave] Simulation error:', e)
    error.value = e.response?.data?.error || e.message || 'Network error — is the backend running?'
  }
  finally { isLoading.value = false; clearInterval(_lt) }
}
</script>

<style scoped>
/* ── Reset & root ─────────────────────────────────────────────── */
.aw {
  /* MiroFish design tokens */
  --bg:   #ffffff;
  --s1:   #fafafa;
  --s2:   #f5f5f5;
  --bd:   #e5e5e5;
  --bdh:  #cccccc;
  --ink:  #000000;
  --ink2: #666666;
  --ink3: #999999;
  --ac:   #FF4500;          /* MiroFish orange */
  --acg:  rgba(255,69,0,0.07);
  --up:   #dc2626;          /* fare increase — red */
  --dn:   #16a34a;          /* fare decrease — green */
  --am:   #d97706;
  --r:    0px;              /* square corners everywhere */
  --rs:   0px;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-sans: 'Space Grotesk', 'Inter', system-ui, sans-serif;

  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
}

/* ── Nav — MiroFish black bar ──────────────────────────────────── */
.aw-nav {
  background:#000000;
  position:sticky; top:0; z-index:100;
}
.aw-nav-inner {
  max-width:1360px; margin:0 auto; padding:0 40px;
  height:56px; display:flex; align-items:center;
  justify-content:space-between; gap:16px;
}
.aw-brand { display:flex; align-items:center; gap:10px; flex-shrink:0; }
.aw-brand-stack { display:flex; flex-direction:column; gap:1px; }
.aw-brand-name {
  font-family:var(--font-mono); font-size:13px; font-weight:800;
  color:#ffffff; letter-spacing:1px; line-height:1;
}
.aw-brand-product {
  font-family:var(--font-mono); font-size:10px; font-weight:600;
  color:var(--ac); letter-spacing:2px; line-height:1;
}
.aw-brand-div { color:#666; font-family:var(--font-mono); font-size:14px; }
.aw-brand-sub {
  font-family:var(--font-mono); font-size:10px; font-weight:500;
  color:#999; letter-spacing:.5px;
}
.nav-byline {
  font-family:var(--font-mono); font-size:9px; font-weight:700;
  color:#e0e0e0; letter-spacing:.8px;
  padding-left:10px; border-left:1px solid #444; margin-left:2px;
}

/* Right pills */
.nav-pills { display:flex; align-items:center; gap:8px; flex-shrink:0; }
.nav-pill {
  display:flex; align-items:center; gap:6px;
  font-family:var(--font-mono); font-size:10px; font-weight:500;
  color:#999; border:1px solid #333; padding:4px 12px;
  letter-spacing:.3px;
}
.mf-sq { color:var(--ac); font-size:12px; }
.nav-pill-live { color:#4ade80; border-color:#1a4a2a; }
.live-dot {
  width:6px; height:6px; border-radius:50%; background:#4ade80;
  flex-shrink:0; animation:livepulse 2s ease-in-out infinite;
}
@keyframes livepulse { 0%,100%{opacity:1} 50%{opacity:.3} }

/* Card header MiroFish tag */
.mf-card-tag {
  display:flex; align-items:center; gap:4px; margin-left:auto;
  font-family:var(--font-mono); font-size:10px; font-weight:600; color:var(--ac);
  background:var(--acg); border:1px solid rgba(255,69,0,.25);
  padding:2px 8px;
}

/* ── Main ─────────────────────────────────────────────────────── */
.aw-main { max-width:1360px; margin:0 auto; padding:32px 32px 100px; }

/* ── Search card ──────────────────────────────────────────────── */
.aw-search {
  background:var(--bg); border:1px solid var(--bd);
  padding:28px 32px; margin-bottom:20px;
}

.trip-row { display:flex; gap:0; margin-bottom:22px; }
.tt-btn {
  padding:6px 18px; border:1px solid var(--bd);
  background:transparent; color:var(--ink3);
  font-family:var(--font-mono); font-size:11px; font-weight:500;
  letter-spacing:.5px; cursor:pointer; transition:all .15s;
  margin-right:-1px;
}
.tt-btn:hover { border-color:var(--bdh); color:var(--ink); background:var(--s2); }
.tt-btn.tt-active {
  background:#000; border-color:#000; color:#fff;
  z-index:1; position:relative;
}

.fields-row { display:flex; align-items:flex-end; gap:12px; flex-wrap:wrap; margin-bottom:22px; }
.field-group { display:flex; flex-direction:column; gap:5px; position:relative; }
.fl {
  font-family:var(--font-mono); font-size:10px; color:var(--ink3);
  letter-spacing:.5px; text-transform:uppercase; font-weight:600;
}
.fi {
  background:var(--bg); border:1px solid var(--bd);
  color:var(--ink); padding:10px 14px; font-size:14px; font-family:var(--font-sans);
  outline:none; transition:border-color .15s; min-width:0;
}
.fi:focus { border-color:#000; }
.fi option { background:var(--bg); }
.fi-err { border-color:rgba(220,38,38,.5) !important; }
.fi-warn { border-color:rgba(217,119,6,.5) !important; }
.fi-code {
  font-family:var(--font-mono); font-size:20px; font-weight:700;
  letter-spacing:3px; text-align:center; width:80px; padding:10px 8px;
  text-transform:uppercase;
}
.fl-req { color:var(--up); font-size:10px; font-family:var(--font-mono); }
.fhint-err { color:var(--up); font-family:var(--font-mono); font-size:10px; }
.fhint-warn { color:var(--am); font-family:var(--font-mono); font-size:10px; }
.fhint {
  position:absolute; top:100%; left:0; padding-top:4px;
  font-family:var(--font-mono); font-size:10px; color:var(--ink3);
  white-space:nowrap; pointer-events:none;
}

.swap-btn {
  background:var(--s2); border:1px solid var(--bd);
  width:34px; height:34px; display:flex; align-items:center; justify-content:center;
  cursor:pointer; color:var(--ink3); flex-shrink:0; transition:all .15s; align-self:flex-end;
}
.swap-btn:hover { border-color:#000; color:#000; background:var(--s2); }

/* Shock pills */
.shock-section { margin-top:22px; }
.shock-label-row { display:flex; align-items:baseline; gap:10px; margin-bottom:10px; flex-wrap:wrap; }
.shock-label {
  font-family:var(--font-mono); font-size:10px; color:var(--ink3);
  text-transform:uppercase; letter-spacing:.5px; font-weight:600;
}
.shock-hint { font-family:var(--font-mono); font-size:10px; color:var(--ink2); }
.shock-pills { display:flex; flex-wrap:wrap; gap:6px; }
.shock-pill-wrap { position:relative; }
.shock-pill {
  display:flex; align-items:center; gap:7px; padding:7px 14px;
  border:1px solid var(--bd); background:transparent;
  color:var(--ink2); font-size:12px; cursor:pointer; font-family:var(--font-sans);
  transition:all .15s;
}
.shock-pill:hover { border-color:var(--bdh); color:var(--ink); background:var(--s2); }
.shock-pill.shock-active {
  background:#000; border-color:#000; color:#fff;
}
.shock-pill.shock-active .sp-check { color:var(--ac); }
.sp-icon { font-size:15px; }
.sp-check { font-size:11px; color:var(--ac); margin-left:2px; font-weight:700; }
.shock-warn { font-family:var(--font-mono); font-size:11px; color:var(--up); margin-top:8px; display:block; }

/* Shock pill tooltip */
.sp-tooltip {
  position:absolute; bottom:calc(100% + 10px); left:50%;
  transform:translateX(-50%);
  background:#fff; border:1px solid var(--bdh);
  padding:14px 16px;
  width:290px; z-index:200; pointer-events:none;
  box-shadow:0 8px 28px rgba(0,0,0,.1);
}
.spt-head { display:flex; align-items:center; gap:8px; margin-bottom:10px; }
.spt-icon { font-size:18px; }
.spt-label { font-size:14px; font-weight:600; color:var(--ink); }
.spt-explain { font-size:12px; color:var(--ink2); line-height:1.65; margin-bottom:10px; }
.spt-source {
  background:var(--acg); border:1px solid rgba(255,69,0,.2);
  padding:8px 10px; display:flex; gap:8px; align-items:flex-start;
}
.spt-src-badge {
  font-family:var(--font-mono); font-size:10px; font-weight:600; color:var(--ac);
  white-space:nowrap; background:rgba(255,69,0,.1); padding:2px 6px; flex-shrink:0;
}
.spt-src-text { font-size:11px; color:var(--ink3); line-height:1.55; }
.sp-tooltip::after {
  content:''; position:absolute; top:100%; left:50%; transform:translateX(-50%);
  border:6px solid transparent; border-top-color:#ccc;
}

/* Horizon tabs */
.horizon-tabs { display:flex; background:var(--s2); border:1px solid var(--bd); padding:2px; gap:1px; }
.hz-btn {
  padding:5px 11px; border:none; background:transparent;
  color:var(--ink3); font-family:var(--font-mono); font-size:11px; font-weight:500;
  cursor:pointer; letter-spacing:.2px; transition:all .15s; white-space:nowrap;
}
.hz-btn:hover { color:var(--ink); background:var(--bg); }
.hz-btn.hz-active { background:#000; color:#fff; }
.fi-horizon-custom { margin-top:6px; }

/* Depth + action */
.action-row { display:flex; align-items:flex-end; gap:14px; margin-top:16px; flex-wrap:wrap; }
.depth-tabs { display:flex; background:var(--s2); border:1px solid var(--bd); padding:2px; gap:1px; }
.dt-btn {
  padding:6px 14px; border:none; background:transparent;
  color:var(--ink3); font-family:var(--font-mono); font-size:11px; font-weight:500;
  cursor:pointer; letter-spacing:.3px;
  transition:all .15s; display:flex; flex-direction:column; align-items:center; gap:1px;
}
.dt-btn:hover { color:var(--ink); background:var(--bg); }
.dt-btn.dt-active { background:#000; color:#fff; }
.dt-hint { font-size:9px; opacity:.7; letter-spacing:0; }

.predict-btn {
  padding:11px 28px; background:#000000; border:1px solid #000;
  color:#fff; font-family:var(--font-mono); font-size:13px; font-weight:700;
  letter-spacing:1px; cursor:pointer;
  display:flex; align-items:center; gap:12px; white-space:nowrap;
  transition:background .2s, border-color .2s; margin-left:auto;
  animation:mf-pulse 2.5s ease-in-out infinite;
}
.predict-btn:hover:not(:disabled) {
  background:var(--ac); border-color:var(--ac);
  animation:none;
}
.predict-btn:disabled {
  background:#e5e5e5; border-color:#e5e5e5; color:#999;
  cursor:not-allowed; animation:none;
}
.btn-arrow { font-size:16px; }
.btn-running { display:flex; align-items:center; gap:2px; }
.btn-cursor { color:var(--ac); animation:blink 1s step-end infinite; font-weight:700; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
@keyframes mf-pulse {
  0%   { box-shadow:0 0 0 0 rgba(0,0,0,.2); }
  70%  { box-shadow:0 0 0 8px rgba(0,0,0,0); }
  100% { box-shadow:0 0 0 0 rgba(0,0,0,0); }
}

/* ── Error ────────────────────────────────────────────────────── */
.aw-error {
  background:#fff5f5; border:1px solid rgba(220,38,38,.3); border-left:3px solid var(--up);
  padding:14px 18px; color:var(--up); display:flex; align-items:flex-start; gap:10px;
  margin-bottom:18px; line-height:1.5;
}
.aw-error strong { display:block; margin-bottom:2px; font-family:var(--font-mono); font-size:12px; color:#000; letter-spacing:.3px; }
.aw-error p { font-size:12px; color:var(--ink2); }
.err-close { background:none; border:none; color:var(--ink3); cursor:pointer; margin-left:auto; font-size:14px; padding:0; }
.err-close:hover { color:#000; }

/* ── Loading panel — MiroFish terminal ────────────────────────── */
.aw-loading { display:flex; align-items:center; justify-content:center; min-height:360px; }
.lp-terminal {
  border:1px solid var(--bdh); width:100%; max-width:560px;
  box-shadow:0 4px 24px rgba(0,0,0,.06);
}
.lp-term-header {
  background:#f0f0f0; border-bottom:1px solid var(--bdh);
  padding:10px 16px; display:flex; align-items:center; gap:6px;
}
.lp-term-dot { width:11px; height:11px; border-radius:50%; flex-shrink:0; }
.lp-td-r { background:#ff5f57; }
.lp-td-y { background:#febc2e; }
.lp-td-g { background:#28c840; }
.lp-term-title {
  font-family:var(--font-mono); font-size:11px; color:#999;
  margin-left:8px; letter-spacing:.3px;
}
.lp-term-body {
  background:#fafafa; padding:24px 28px;
  display:flex; flex-direction:column; gap:10px;
}
.lp-cmd {
  font-family:var(--font-mono); font-size:13px; color:#000;
  font-weight:600; letter-spacing:.2px;
}
.lp-log {
  font-family:var(--font-mono); font-size:12px; color:var(--ink3); padding-left:16px;
}
.lp-log-active { color:var(--ac); font-weight:600; }
.lp-eta-line {
  font-family:var(--font-mono); font-size:11px; color:#bbb;
  border-top:1px solid var(--bd); padding-top:12px; margin-top:4px;
}
.lp-cursor { color:var(--ac); animation:blink 1s step-end infinite; font-weight:700; }

/* ── Synthetic data warning banner ───────────────────────────── */
.aw-synthetic-warn {
  background:rgba(217,119,6,.06); border:1px solid rgba(217,119,6,.3);
  border-left:3px solid var(--am); padding:14px 18px;
  display:flex; align-items:flex-start; gap:12px; margin-bottom:18px;
  color:var(--am);
}
.aw-synthetic-warn svg { flex-shrink:0; margin-top:1px; }
.aw-synthetic-warn strong {
  display:block; margin-bottom:3px;
  font-family:var(--font-mono); font-size:11px; font-weight:700;
  color:#000; letter-spacing:.3px; text-transform:uppercase;
}
.aw-synthetic-warn p { font-size:12px; color:var(--ink2); line-height:1.6; margin:0; }

/* ── Results layout ───────────────────────────────────────────── */
.results-body { display:grid; grid-template-columns:clamp(400px,460px,500px) 1fr; gap:20px; align-items:start; }
@media (max-width:960px) { .results-body { grid-template-columns:1fr; } }
.col-l, .col-r { display:flex; flex-direction:column; gap:16px; }

/* ── Prediction band ──────────────────────────────────────────── */
.pred-band {
  border:1px solid #000; background:#000;
  padding:24px 32px; display:flex; align-items:center; gap:24px; flex-wrap:wrap;
  margin-bottom:16px;
}
.pb-left { display:flex; flex-direction:column; gap:4px; }
.pb-route {
  font-family:var(--font-mono); font-size:16px; font-weight:700;
  letter-spacing:2px; color:#fff;
}
.pb-sim { font-family:var(--font-mono); font-size:10px; color:#888; }
.pb-center { flex:1; }
.pb-fares { display:flex; align-items:center; gap:20px; justify-content:center; flex-wrap:wrap; }
.pb-fare-item { display:flex; flex-direction:column; gap:3px; }
.pb-fare-lbl {
  font-family:var(--font-mono); font-size:9px; color:#888;
  text-align:center; text-transform:uppercase; letter-spacing:.8px;
}
.pb-fare-val {
  font-size:32px; font-weight:700; letter-spacing:-1px;
  font-variant-numeric:tabular-nums; color:#fff;
}
.pb-pred { color:var(--ac) !important; }
.pb-arrow { color:#444; font-size:24px; }
.arr-up { color:#f87171 !important; }
.arr-dn { color:#4ade80 !important; }
.pb-right { display:flex; flex-direction:column; align-items:flex-end; gap:8px; min-width:160px; }
.delta-chip {
  font-family:var(--font-mono); font-size:13px; font-weight:700; padding:4px 12px; letter-spacing:.5px;
}
.dc-up { background:rgba(220,38,38,.25); color:#fca5a5; border:1px solid rgba(220,38,38,.3); }
.dc-dn { background:rgba(22,163,74,.2); color:#86efac; border:1px solid rgba(22,163,74,.3); }
.consensus-lbl { font-family:var(--font-mono); font-size:11px; font-weight:600; color:#bbb; letter-spacing:.3px; }
.conf-bar-wrap { display:flex; align-items:center; gap:7px; }
.conf-bar-lbl { font-family:var(--font-mono); font-size:10px; color:#888; }
.conf-bar { flex:1; min-width:80px; height:3px; background:#333; }
.conf-fill { height:100%; background:var(--ac); transition:width .4s; }
.conf-pct { font-family:var(--font-mono); font-size:11px; color:#bbb; min-width:30px; text-align:right; }

/* Consensus border accents */
.cs-strong_raise  { border-color:rgba(220,38,38,.6)!important; }
.cs-moderate_raise { border-color:rgba(255,69,0,.5)!important; }
.cs-hold { border-color:#333!important; }
.cs-moderate_drop { border-color:rgba(22,163,74,.5)!important; }
.cs-strong_drop   { border-color:rgba(22,163,74,.6)!important; }

/* Shock explain banner */
.shock-banner {
  background:var(--acg); border:1px solid rgba(255,69,0,.2); border-left:3px solid var(--ac);
  padding:14px 18px; display:flex; flex-direction:column; gap:10px; margin-bottom:16px;
}
.sb-header { display:flex; align-items:center; gap:8px; }
.sb-bulb { font-size:15px; flex-shrink:0; }
.sb-title { font-family:var(--font-mono); font-size:11px; font-weight:700; color:var(--ac); letter-spacing:.5px; text-transform:uppercase; }
.sb-explain { font-size:13px; color:var(--ink2); line-height:1.65; }

/* Multi-shock chips */
.sb-chips { display:flex; flex-wrap:wrap; gap:6px; }
.sb-chip {
  position:relative; display:flex; align-items:center; gap:5px;
  padding:4px 12px;
  background:var(--acg); border:1px solid rgba(255,69,0,.3);
  cursor:default; transition:border-color .15s, background .15s;
}
.sb-chip:hover { background:rgba(255,69,0,.12); border-color:rgba(255,69,0,.5); }
.sb-chip-icon { font-size:13px; }
.sb-chip-label { font-family:var(--font-mono); font-size:11px; font-weight:500; color:var(--ac); white-space:nowrap; }

/* Chip tooltip */
.sb-tooltip {
  position:absolute; bottom:calc(100% + 8px); left:50%;
  transform:translateX(-50%);
  background:#fff; border:1px solid var(--bdh);
  padding:12px 14px;
  width:260px; font-size:12px; color:var(--ink2); line-height:1.65;
  box-shadow:0 8px 28px rgba(0,0,0,.12); z-index:200; pointer-events:none;
  text-align:left;
}
.sb-tooltip::after {
  content:''; position:absolute; top:100%; left:50%; transform:translateX(-50%);
  border:6px solid transparent; border-top-color:#ccc;
}
.sbt-fade-enter-active { transition:opacity .12s ease, transform .12s ease; }
.sbt-fade-leave-active { transition:opacity .08s ease; }
.sbt-fade-enter-from { opacity:0; transform:translateX(-50%) translateY(4px); }
.sbt-fade-leave-to { opacity:0; }

/* ── Flight card ──────────────────────────────────────────────── */
.flight-card {
  background:var(--bg); border:1px solid var(--bd); overflow:hidden;
}
.fc-top {
  padding:16px 20px; border-bottom:1px solid var(--bd);
  display:flex; align-items:center; justify-content:space-between;
}
.fc-route { display:flex; align-items:center; gap:10px; }
.fc-code { font-size:17px; font-weight:700; letter-spacing:1px; }
.fc-arrow { color:var(--ink3); }
.trip-badge { font-family:var(--font-mono); font-size:10px; padding:3px 10px; font-weight:600; letter-spacing:.5px; text-transform:uppercase; }
.tb-ow  { background:var(--s2); color:var(--ink3); border:1px solid var(--bd); }
.tb-rt  { background:var(--acg); color:var(--ac); border:1px solid rgba(255,69,0,.25); }

.fc-body { padding:20px; display:flex; align-items:center; gap:16px; min-width:0; }
.airline-col { display:flex; flex-direction:column; align-items:center; gap:5px; min-width:72px; }
.logo-box {
  width:52px; height:52px; background:#fff; border-radius:10px;
  display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0;
}
.al-img { width:44px; height:44px; object-fit:contain; }
.al-fallback { width:100%; height:100%; display:flex; align-items:center; justify-content:center; }
.al-name { font-size:11px; color:var(--ink2); text-align:center; line-height:1.3; }
.al-fno { font-size:11px; color:var(--ink3); }

.times-col { flex:1; display:flex; align-items:center; gap:6px; }
.t-blk { display:flex; flex-direction:column; gap:2px; min-width:72px; }
.t-blk.t-right { align-items:flex-end; }
.t-time { font-size:22px; font-weight:700; letter-spacing:-.4px; font-variant-numeric:tabular-nums; }
.nd { font-size:10px; color:var(--am); font-weight:700; }
.t-iata.t-ac { font-size:12px; font-weight:600; color:var(--ac); }
.t-apt { font-size:11px; color:var(--ink3); line-height:1.3; }
.t-date { font-size:11px; color:var(--ink3); }
.dur-blk { flex:1; display:flex; flex-direction:column; align-items:center; gap:4px; }
.dur-line { display:block; height:1px; width:100%; background:var(--bdh); }
.dur-txt { font-size:11px; color:var(--ink3); }
.stops-pill { font-family:var(--font-mono); font-size:10px; padding:2px 8px; font-weight:600; letter-spacing:.3px; }
.sp-direct { background:rgba(22,163,74,.1); color:var(--dn); border:1px solid rgba(22,163,74,.25); }
.sp-stops  { background:rgba(217,119,6,.1); color:var(--am); border:1px solid rgba(217,119,6,.25); }

.fare-blk { display:flex; flex-direction:column; align-items:flex-end; gap:4px; min-width:90px; }
.fare-lbl { font-size:11px; color:var(--ink3); }
.fare-val { font-size:26px; font-weight:700; letter-spacing:-.5px; font-variant-numeric:tabular-nums; }
.cabin-pill { font-family:var(--font-mono); font-size:10px; color:var(--ink3); background:var(--s2); border:1px solid var(--bd); padding:2px 8px; letter-spacing:.3px; }

/* ── Historical Baseline ──────────────────────────────────────── */
.hist-baseline {
  background:var(--s1); border:1px solid var(--bd); border-radius:var(--r);
  padding:14px 18px;
}
.hb-header {
  display:flex; align-items:center; gap:8px; margin-bottom:12px;
}
.hb-icon { font-size:14px; }
.hb-title { font-size:12px; font-weight:600; letter-spacing:.3px; text-transform:uppercase; color:var(--ink2); flex:1; }
.hb-src {
  font-family:var(--font-mono); font-size:10px; padding:2px 8px;
  border-radius:0; font-weight:600; letter-spacing:.3px;
}
.hb-live { background:rgba(34,197,94,.1); color:#16a34a; border:1px solid rgba(34,197,94,.25); }
.hb-est  { background:var(--s2); color:var(--ink3); border:1px solid var(--bd); }
.hb-metrics {
  display:grid; grid-template-columns:repeat(4,1fr); gap:10px;
}
@media(max-width:700px){ .hb-metrics{ grid-template-columns:repeat(2,1fr); } }
.hb-metric { display:flex; flex-direction:column; gap:3px; }
.hb-lbl { font-size:10px; color:var(--ink3); text-transform:uppercase; letter-spacing:.3px; }
.hb-val { font-size:17px; font-weight:700; font-variant-numeric:tabular-nums; }
.hb-trend { font-size:13px; font-weight:600; font-variant-numeric:tabular-nums; }
.hbt-up { color:var(--ac); }
.hbt-dn { color:#3b82f6; }
.hb-note {
  margin-top:10px; font-size:11px; color:var(--ink3);
  border-top:1px solid var(--bd); padding-top:8px; line-height:1.5;
}

/* ── Alternative flights ──────────────────────────────────────── */
.alt-flights {
  background:var(--s1); border:1px solid var(--bd); border-radius:var(--r);
  overflow:visible; position:relative;
}
.alt-title {
  padding:12px 16px; font-size:12px; color:var(--ink3);
  border-bottom:1px solid var(--bd); display:flex; align-items:center; gap:8px;
}
.alt-title-hint { opacity:.55; font-size:10px; letter-spacing:.3px; }
.alt-row {
  display:flex; align-items:center; gap:10px; padding:12px 16px;
  border-bottom:1px solid var(--bd); font-size:13px;
  cursor:pointer; transition:background .15s; position:relative;
}
.alt-row:last-child { border-bottom:none; }
.alt-row:hover { background:var(--s2); }
.alt-hover-hint {
  margin-left:auto; color:var(--ac); font-size:15px; opacity:0;
  transition:opacity .15s; flex-shrink:0;
}
.alt-row:hover .alt-hover-hint { opacity:.7; }

/* Tooltip card */
.alt-tooltip {
  position:absolute; bottom:calc(100% + 8px); left:0; z-index:200;
  background:#fff; border:1px solid var(--bdh);
  padding:14px 16px; min-width:280px;
  box-shadow:0 8px 28px rgba(0,0,0,.1);
  pointer-events:none;
}
.at-header { display:flex; align-items:center; gap:10px; margin-bottom:14px; }
.at-logo-box {
  width:36px; height:36px; background:#fff; border-radius:8px;
  display:flex; align-items:center; justify-content:center; flex-shrink:0; overflow:hidden;
}
.at-logo { width:28px; height:28px; object-fit:contain; }
.at-logo-fb { font-size:16px; }
.at-airline-info { display:flex; flex-direction:column; gap:2px; }
.at-name { font-size:14px; font-weight:600; color:var(--ink); }
.at-fnum { font-size:11px; color:var(--ink3); }
.at-times-row { display:flex; align-items:center; gap:6px; margin-bottom:14px; }
.at-time-blk { display:flex; flex-direction:column; gap:2px; }
.at-time-blk.at-right { align-items:flex-end; }
.at-t { font-size:20px; font-weight:700; letter-spacing:-.3px; font-variant-numeric:tabular-nums; }
.at-ap { font-size:11px; color:var(--ac); font-weight:600; }
.at-mid { flex:1; display:flex; flex-direction:column; align-items:center; gap:4px; }
.at-line { width:100%; height:1px; background:var(--bdh); }
.at-dur-lbl { font-size:11px; color:var(--ink3); }
.at-footer {
  display:flex; align-items:center; justify-content:space-between;
  border-top:1px solid var(--bd); padding-top:10px;
}
.at-price { font-size:20px; font-weight:700; font-variant-numeric:tabular-nums; color:var(--ink); }
.at-cabin { font-size:11px; color:var(--ink3); margin-left:6px; }
.at-note { font-size:10px; color:var(--ink3); text-align:right; line-height:1.4; max-width:130px; }

/* Tooltip transition */
.tooltip-fade-enter-active { transition:opacity .12s ease, transform .12s ease; }
.tooltip-fade-leave-active { transition:opacity .08s ease; }
.tooltip-fade-enter-from { opacity:0; transform:translateY(4px); }
.tooltip-fade-leave-to { opacity:0; }

.alt-logo-wrap {
  width:28px; height:28px; background:#fff; border-radius:6px;
  display:flex; align-items:center; justify-content:center; flex-shrink:0; overflow:hidden;
}
.alt-logo { width:22px; height:22px; object-fit:contain; }
.alt-logo-fb { font-size:14px; }
.alt-airline { color:var(--ink2); min-width:80px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.alt-times { color:var(--ink); font-weight:500; flex:1; white-space:nowrap; }
.alt-dur { color:var(--ink3); white-space:nowrap; }
.alt-stops { font-family:var(--font-mono); font-size:10px; padding:1px 7px; white-space:nowrap; }
.alt-price { font-size:14px; font-weight:700; color:var(--ink); min-width:60px; text-align:right; font-variant-numeric:tabular-nums; }

/* ── Weather card ─────────────────────────────────────────────── */
.weather-card {
  background:var(--s1); border:1px solid var(--bd); border-radius:var(--r); padding:18px 20px;
}
.weather-card.wr-high    { border-color:rgba(249,115,22,.3); }
.weather-card.wr-severe  { border-color:rgba(239,68,68,.3); }
.weather-card.wr-moderate{ border-color:rgba(245,158,11,.3); }
.wc-head { display:flex; align-items:center; gap:7px; margin-bottom:12px; font-size:13px; font-weight:600; }
.risk-pill { font-size:10px; padding:2px 8px; border-radius:0; font-weight:600; margin-left:auto; letter-spacing:.3px; }
.rp-low      { background:rgba(16,185,129,.1);  color:#065f46; border:1px solid rgba(16,185,129,.3); }
.rp-moderate { background:rgba(245,158,11,.1);  color:#92400e; border:1px solid rgba(245,158,11,.3); }
.rp-high     { background:rgba(249,115,22,.1);  color:#c2410c; border:1px solid rgba(249,115,22,.3); }
.rp-severe   { background:rgba(239,68,68,.1);   color:#991b1b; border:1px solid rgba(239,68,68,.3); }

.wx-pair { display:flex; gap:10px; margin-bottom:12px; }
.wx-item { flex:1; display:flex; align-items:center; gap:8px; background:var(--s2); border-radius:var(--rs); padding:10px; }
.wx-em { font-size:22px; flex-shrink:0; }
.wx-info { flex:1; }
.wx-code { font-family:var(--font-mono); font-size:12px; font-weight:700; color:var(--ink); display:block; letter-spacing:.3px; }
.wx-desc { font-size:12px; color:var(--ink2); display:block; }
.wx-stats { display:flex; flex-wrap:wrap; gap:6px; margin-top:4px; font-size:11px; color:var(--ink3); }
.wx-ring { position:relative; width:44px; height:44px; flex-shrink:0; display:flex; align-items:center; justify-content:center; }
.wx-sc { position:absolute; font-size:12px; font-weight:700; }

.ot-row { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.ot-lbl { font-size:12px; color:var(--ink2); white-space:nowrap; }
.ot-track { flex:1; height:4px; background:var(--s2); border:1px solid var(--bd); }
.ot-fill { height:100%; transition:width .4s; }
.ot-pct { font-size:13px; font-weight:700; min-width:36px; text-align:right; }
.wx-primary { font-size:12px; color:var(--ink3); padding-top:6px; border-top:1px solid var(--bd); }

/* ── Card shared ──────────────────────────────────────────────── */
.agents-card, .cascade-card, .narrative-card {
  background:var(--bg); border:1px solid var(--bd); overflow:hidden;
}
.card-hd {
  padding:12px 20px; border-bottom:1px solid var(--bd);
  font-family:var(--font-mono); font-size:11px; font-weight:700;
  letter-spacing:.5px; text-transform:uppercase;
  display:flex; align-items:center; gap:7px;
  background:var(--s2);
}
.card-hd-note {
  margin-left:auto; font-family:var(--font-mono); font-size:10px; font-weight:400;
  color:var(--ink3); background:var(--bg); border:1px solid var(--bd);
  padding:2px 7px; white-space:nowrap;
}

/* ── Agents ───────────────────────────────────────────────────── */
.agents-list { padding:0; }
.agent-row {
  display:flex; gap:12px; padding:14px 20px;
  border-bottom:1px solid var(--bd);
}
.agent-row:last-child { border-bottom:none; }
.ag-av {
  width:32px; height:32px; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-family:var(--font-mono); font-size:11px; font-weight:800;
  color:#fff; margin-top:1px;
}
.ag-body { flex:1; min-width:0; }
.ag-hdr { display:flex; align-items:center; gap:7px; flex-wrap:wrap; margin-bottom:4px; }
.ag-name { font-size:13px; font-weight:600; font-family:var(--font-sans); }
.ag-round {
  font-family:var(--font-mono); font-size:10px; color:var(--ink3);
  background:var(--s2); border:1px solid var(--bd); padding:1px 6px;
  letter-spacing:.3px;
}
.dec-chip {
  font-family:var(--font-mono); font-size:10px; padding:2px 8px;
  text-transform:uppercase; letter-spacing:.3px; font-weight:600;
}
.dc-raise_fares { background:rgba(220,38,38,.1); color:var(--up); border:1px solid rgba(220,38,38,.2); }
.dc-drop_fares  { background:rgba(22,163,74,.1); color:var(--dn); border:1px solid rgba(22,163,74,.2); }
.dc-hold_fares  { background:var(--s2); color:var(--ink3); border:1px solid var(--bd); }
.dc-hedge       { background:var(--acg); color:var(--ac); border:1px solid rgba(255,69,0,.2); }
.ag-mag { font-family:var(--font-mono); font-size:12px; font-weight:700; margin-left:auto; }
.mag-up { color:var(--up); }
.mag-dn { color:var(--dn); }
.ag-reason { font-size:12px; color:var(--ink2); line-height:1.6; margin-top:2px; }
.show-more-btn {
  display:block; width:100%; padding:10px; text-align:center; background:none;
  border:none; border-top:1px solid var(--bd);
  font-family:var(--font-mono); color:var(--ac); cursor:pointer;
  font-size:11px; letter-spacing:.5px; text-transform:uppercase;
}
.show-more-btn:hover { background:var(--acg); }

/* ── Cascade grid ─────────────────────────────────────────────── */
.cascade-intro {
  padding:12px 20px; font-size:12px; color:var(--ink3);
  border-bottom:1px solid var(--bd); line-height:1.6;
}
.cascade-grid { padding:12px 16px; display:flex; flex-direction:column; gap:6px; }

.cn-card {
  border:1px solid transparent; border-radius:var(--rs); cursor:pointer;
  transition:border-color .15s, background .15s; overflow:hidden;
}
.cn-card:hover { background:var(--s2); border-color:var(--bd); }
.cn-card.expanded { background:var(--s2); border-color:var(--bdh); }

.cn-main { display:flex; align-items:center; gap:10px; padding:10px 12px; }
.cn-icon { font-size:16px; flex-shrink:0; width:22px; text-align:center; }
.cn-info { flex:1; min-width:0; }

/* Top row: label + severity badge */
.cn-top-row { display:flex; align-items:center; justify-content:space-between; margin-bottom:5px; gap:8px; }
.cn-label { font-size:13px; font-weight:500; color:var(--ink); }
.cn-sev {
  font-family:var(--font-mono); font-size:10px; font-weight:700; padding:2px 8px; border-radius:0;
  white-space:nowrap; flex-shrink:0; letter-spacing:.3px;
}
.sev-up { background:rgba(220,38,38,.08); color:#b91c1c; border:1px solid rgba(220,38,38,.2); }
.sev-dn { background:rgba(22,163,74,.08); color:#15803d; border:1px solid rgba(22,163,74,.2); }

/* Bar row: bar + days timeline */
.cn-bar-row { display:flex; align-items:center; gap:8px; }
.cn-bar { flex:1; height:4px; background:var(--s2); overflow:hidden; border:1px solid var(--bd); }
.cn-fill { height:100%; transition:width .5s ease; }
.cn-timeline { font-size:11px; color:var(--ink3); white-space:nowrap; min-width:30px; text-align:right; }

/* Chevron (now directly in cn-main, not inside cn-meta) */
.cn-chevron { color:var(--ink3); transition:transform .2s; flex-shrink:0; }
.cn-chevron.rotated { transform:rotate(180deg); }

/* Expanded section */
.cn-expand { padding:2px 12px 14px 44px; display:flex; flex-direction:column; gap:8px; }

.cn-interpret {
  font-size:13px; color:var(--ink); line-height:1.65;
  background:var(--acg); border-left:2px solid var(--ac);
  padding:8px 10px;
}
.cn-what {
  font-size:12px; color:var(--ink2); line-height:1.6;
  display:flex; gap:6px; align-items:flex-start;
}
.cn-what-icon { flex-shrink:0; font-size:13px; }
.cn-meta-row {
  display:flex; align-items:center; gap:10px; flex-wrap:wrap;
}
.cn-meta-item { font-size:11px; color:var(--ink3); }
.cn-conf-badge {
  font-size:10px; font-family:var(--font-mono); padding:2px 8px; border-radius:0;
}
.cb-high { background:rgba(16,185,129,.1);  color:#065f46; border:1px solid rgba(16,185,129,.25); }
.cb-med  { background:rgba(245,158,11,.1);  color:#92400e; border:1px solid rgba(245,158,11,.25); }
.cb-low  { background:rgba(100,116,139,.1); color:var(--ink3); border:1px solid var(--bd); }

/* ── Narrative ────────────────────────────────────────────────── */
/* ── Narrative sections ───────────────────────── */
.narrative-body { padding:4px 0 6px; }
.nr-section {
  padding:16px 20px 14px;
  border-bottom:1px solid var(--bd);
}
.nr-section:last-child { border-bottom:none; }
.nr-heading {
  display:flex; align-items:center; gap:7px;
  font-family:var(--font-mono); font-size:10px; font-weight:700;
  color:#000; letter-spacing:.5px; text-transform:uppercase;
  margin-bottom:9px;
}
.nr-icon { color:var(--ac); font-size:11px; flex-shrink:0; }
.nr-body {
  font-size:13px; color:var(--ink2); line-height:1.8;
  margin:0;
}
.nr-raw { padding:18px 20px; font-size:13px; color:var(--ink2); line-height:1.85; margin:0; }

/* Watch List */
.nr-watchlist .nr-heading { margin-bottom:10px; }
.nr-bullets { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:7px; }
.nr-bullet {
  display:flex; align-items:flex-start; gap:9px;
  font-size:12px; color:var(--ink2); line-height:1.6;
}
.nr-bullet-dot {
  font-family:var(--font-mono); font-size:10px; color:var(--ac);
  flex-shrink:0; margin-top:2px; font-weight:700;
}

/* ── Export bar ────────────────────────────────────────────────── */
.export-bar {
  display:flex; align-items:center; justify-content:space-between;
  padding:10px 16px; border:1px solid var(--bd); background:var(--s2);
  margin-top:8px; flex-wrap:wrap; gap:8px;
}
.export-label {
  font-family:var(--font-mono); font-size:10px; color:var(--ink3); letter-spacing:.3px;
}
.export-actions { display:flex; gap:6px; }
.exp-btn {
  display:flex; align-items:center; gap:6px;
  padding:6px 14px; font-family:var(--font-mono); font-size:11px; font-weight:600;
  letter-spacing:.3px; cursor:pointer; border:1px solid var(--bd);
  background:var(--bg); color:var(--ink2); transition:all .15s;
}
.exp-btn:hover { border-color:var(--ink); color:var(--ink); }
.exp-btn.exp-btn-done { border-color:#16a34a; color:#16a34a; background:rgba(34,197,94,.06); }

/* ── Sources card ─────────────────────────────────────────────── */
.sources-card {
  background:var(--s2); border:1px solid var(--bd);
  padding:14px 18px; display:flex; flex-direction:column; gap:10px;
}
.sources-label {
  display:flex; align-items:center; gap:6px;
  font-family:var(--font-mono); font-size:10px; color:var(--ink3);
  text-transform:uppercase; letter-spacing:.5px; font-weight:600;
}
.sources-row { display:flex; flex-wrap:wrap; gap:6px; }
.src-chip { font-family:var(--font-mono); font-size:10px; padding:3px 10px; letter-spacing:.3px; }
.src-live { background:rgba(22,163,74,.1); color:var(--dn); border:1px solid rgba(22,163,74,.25); }
.src-syn  { background:var(--bg); color:var(--ink3); border:1px solid var(--bd); }

/* ── Empty state / pitch ──────────────────────────────────────── */
.aw-empty { padding:56px 24px 64px; max-width:860px; margin:0 auto; }

.empty-hero { text-align:center; margin-bottom:48px; }
.empty-eyebrow {
  font-family:var(--font-mono); font-size:10px; font-weight:600;
  letter-spacing:2px; color:var(--ac); margin-bottom:16px;
  display:block; text-transform:uppercase;
}
.empty-h {
  font-family:var(--font-sans); font-size:38px; font-weight:800;
  letter-spacing:-.5px; margin-bottom:14px; color:var(--ink);
  line-height:1.15;
}
.empty-sub {
  font-size:14px; color:var(--ink2); line-height:1.85;
  max-width:560px; margin:0 auto;
}
.empty-sub em { font-style:normal; color:var(--ink); font-weight:600; }

.empty-pillars {
  display:grid; grid-template-columns:repeat(3,1fr); gap:1px;
  background:var(--bd); border:1px solid var(--bd); border-radius:var(--r);
  margin-bottom:36px; overflow:hidden;
}
.empty-pillar {
  background:var(--s1); padding:22px 18px;
  display:flex; flex-direction:column; gap:8px;
}
.ep-num {
  font-family:var(--font-mono); font-size:10px; font-weight:700;
  color:var(--ac); letter-spacing:.5px;
}
.ep-title {
  font-size:13px; font-weight:700; color:var(--ink); letter-spacing:-.2px;
}
.ep-desc { font-size:12px; color:var(--ink2); line-height:1.65; }

.empty-examples { text-align:center; }
.empty-ex-lbl {
  display:block; font-family:var(--font-mono); font-size:10px;
  color:var(--ink3); letter-spacing:.5px; margin-bottom:10px;
  text-transform:uppercase;
}
.example-row { display:flex; flex-wrap:wrap; gap:6px; justify-content:center; }
.ex-chip {
  padding:7px 16px; border:1px solid var(--bd);
  background:var(--bg); color:var(--ink2);
  font-family:var(--font-mono); font-size:11px; cursor:pointer;
  letter-spacing:.3px; transition:all .15s;
}
.ex-chip:hover { border-color:var(--ink); color:var(--ink); background:var(--s2); }

@media(max-width:640px) {
  .empty-pillars { grid-template-columns:1fr; }
  .empty-h { font-size:26px; }
}

/* ── Transition ───────────────────────────────────────────────── */
.fade-up-enter-active { transition:opacity .4s ease, transform .4s ease; }
.fade-up-enter-from   { opacity:0; transform:translateY(12px); }

/* ── History nav pill ─────────────────────────────────────────── */
.nav-pill-hist {
  background:transparent; border:1px solid #444; cursor:pointer;
  font-family:var(--font-mono); font-size:10px; font-weight:600;
  color:#aaa; letter-spacing:.5px; padding:3px 10px;
  transition:all .15s;
}
.nav-pill-hist:hover { border-color:#888; color:#fff; }

/* ── History drawer ───────────────────────────────────────────── */
.hist-backdrop {
  position:fixed; inset:0; background:rgba(0,0,0,.55); z-index:400;
  display:flex; justify-content:flex-end;
}
.hist-drawer {
  width:380px; max-width:100vw; height:100%; background:var(--bg);
  border-left:1px solid var(--bd); display:flex; flex-direction:column;
  overflow:hidden;
}
.hist-hd {
  display:flex; align-items:center; justify-content:space-between;
  padding:16px 20px; border-bottom:1px solid var(--bd); flex-shrink:0;
  background:#000;
}
.hist-title {
  font-family:var(--font-mono); font-size:12px; font-weight:700;
  color:#fff; letter-spacing:.5px; text-transform:uppercase;
}
.hist-hd-actions { display:flex; align-items:center; gap:10px; }
.hist-clear {
  font-family:var(--font-mono); font-size:10px; color:#888;
  background:none; border:none; cursor:pointer; padding:0;
  letter-spacing:.3px;
}
.hist-clear:hover { color:#fff; }
.hist-close {
  background:none; border:none; color:#888; font-size:16px;
  cursor:pointer; padding:0; line-height:1;
}
.hist-close:hover { color:#fff; }
.hist-empty {
  padding:40px 20px; text-align:center;
  font-size:13px; color:var(--ink3); line-height:1.6;
}
.hist-list { flex:1; overflow-y:auto; padding:8px; display:flex; flex-direction:column; gap:4px; }
.hist-entry {
  padding:12px 14px; border:1px solid var(--bd); cursor:pointer;
  transition:all .15s; background:var(--bg);
}
.hist-entry:hover { border-color:var(--ink); background:var(--s2); }
.he-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:4px; }
.he-route { font-family:var(--font-mono); font-size:13px; font-weight:700; color:var(--ink); letter-spacing:.5px; }
.he-delta { font-family:var(--font-mono); font-size:11px; font-weight:700; }
.he-up { color:#dc2626; }
.he-dn { color:#16a34a; }
.he-shocks { font-size:11px; color:var(--ink2); margin-bottom:6px; line-height:1.4; }
.he-meta { display:flex; align-items:center; justify-content:space-between; }
.he-fare { font-family:var(--font-mono); font-size:11px; color:var(--ink3); }
.he-ts { font-size:10px; color:var(--ink3); }

/* ── Comparison winner verdict ────────────────────────────────── */
.cdb-winner-chip {
  font-family:var(--font-mono); font-size:11px; font-weight:800;
  padding:4px 14px; letter-spacing:.6px; white-space:nowrap; flex-shrink:0;
}
.cdb-w-a { background:rgba(220,38,38,.12); color:#b91c1c; border:1px solid rgba(220,38,38,.3); }
.cdb-w-b { background:rgba(147,51,234,.1); color:#7c3aed; border:1px solid rgba(147,51,234,.25); }
.cdb-draw-chip {
  font-family:var(--font-mono); font-size:11px; font-weight:700;
  padding:4px 14px; letter-spacing:.6px; white-space:nowrap; flex-shrink:0;
  background:var(--s2); color:var(--ink3); border:1px solid var(--bd);
}
.cdb-verdict { display:flex; align-items:baseline; gap:8px; flex:1; min-width:0; }
.cdb-verdict-num {
  font-family:var(--font-mono); font-size:18px; font-weight:800;
  color:var(--ink); white-space:nowrap; flex-shrink:0;
}
.cdb-verdict-txt { font-size:12px; color:var(--ink2); line-height:1.5; }

/* ── History panel slide transition ──────────────────────────── */
.hist-fade-enter-active,
.hist-fade-leave-active { transition:opacity .2s ease; }
.hist-fade-enter-active .hist-drawer,
.hist-fade-leave-active .hist-drawer { transition:transform .25s cubic-bezier(0.16,1,0.3,1); }
.hist-fade-enter-from { opacity:0; }
.hist-fade-enter-from .hist-drawer { transform:translateX(100%); }
.hist-fade-leave-to { opacity:0; }
.hist-fade-leave-to .hist-drawer { transform:translateX(100%); }

/* ── Methodology nav pill ──────────────────────────────────────── */
.nav-pill-method {
  background:transparent; border:1px solid #555; cursor:pointer;
  font-family:var(--font-mono); font-size:10px; font-weight:700;
  color:#aaa; letter-spacing:.5px; padding:3px 10px;
  transition:all .15s;
}
.nav-pill-method:hover { border-color:#ddd; color:#fff; background:rgba(255,255,255,.06); }

/* ── Methodology backdrop ──────────────────────────────────────── */
.meth-backdrop {
  position:fixed; inset:0; background:rgba(0,0,0,.72); z-index:500;
  display:flex; align-items:center; justify-content:center; padding:20px;
}
.meth-panel {
  width:100%; max-width:780px; max-height:88vh;
  background:var(--bg); border:1px solid var(--bd);
  display:flex; flex-direction:column; overflow:hidden;
}

/* Header */
.meth-hd {
  display:flex; align-items:center; justify-content:space-between;
  padding:18px 24px; border-bottom:1px solid var(--bd); flex-shrink:0;
  background:#000;
}
.meth-hd-left { display:flex; flex-direction:column; gap:2px; }
.meth-eyebrow {
  font-family:var(--font-mono); font-size:9px; font-weight:700;
  color:#555; letter-spacing:1.5px; text-transform:uppercase;
}
.meth-title {
  font-family:var(--font-mono); font-size:16px; font-weight:800;
  color:#fff; letter-spacing:.3px; text-transform:uppercase;
}
.meth-close {
  background:none; border:none; color:#666; font-size:16px;
  cursor:pointer; padding:0; line-height:1; transition:color .15s;
}
.meth-close:hover { color:#fff; }

/* Tabs */
.meth-tabs {
  display:flex; border-bottom:1px solid var(--bd); flex-shrink:0;
  background:#000;
}
.meth-tab {
  font-family:var(--font-mono); font-size:11px; font-weight:600;
  letter-spacing:.5px; text-transform:uppercase;
  background:none; border:none; border-bottom:2px solid transparent;
  color:#666; cursor:pointer; padding:12px 20px;
  transition:all .15s; margin-bottom:-1px;
}
.meth-tab:hover { color:#bbb; }
.meth-tab-active { color:#fff; border-bottom-color:#fff; }

/* Body */
.meth-body { flex:1; overflow-y:auto; padding:28px 28px 32px; }

.meth-intro {
  font-size:14px; color:var(--ink2); line-height:1.7;
  margin:0 0 28px; max-width:62ch;
}

/* ── Pipeline tab ──────────────────────────────────────────────── */
.pip-steps { display:flex; flex-direction:column; }
.pip-step { display:flex; gap:20px; align-items:flex-start; }
.pip-num {
  font-family:var(--font-mono); font-size:28px; font-weight:800;
  color:var(--bd); line-height:1; flex-shrink:0; width:36px;
  padding-top:2px;
}
.pip-content { flex:1; padding-bottom:8px; }
.pip-label {
  font-family:var(--font-mono); font-size:13px; font-weight:700;
  color:var(--ink); letter-spacing:.3px; margin-bottom:8px;
  text-transform:uppercase;
}
.pip-desc { font-size:13px; color:var(--ink2); line-height:1.7; margin:0 0 12px; }
.pip-badges { display:flex; flex-wrap:wrap; gap:6px; }
.pip-badge {
  font-family:var(--font-mono); font-size:10px; font-weight:600;
  padding:3px 9px; background:var(--s2); color:var(--ink3);
  border:1px solid var(--bd); letter-spacing:.3px;
}
.pip-badge-det {
  background:rgba(22,163,74,.08); color:#16a34a;
  border-color:rgba(22,163,74,.25);
}
.pip-connector {
  width:1px; background:var(--bd); height:24px;
  margin-left:17px; flex-shrink:0;
}
.pip-disclaimer {
  margin-top:28px; padding:16px; border:1px solid var(--bd);
  background:var(--s2); font-size:12px; color:var(--ink2); line-height:1.6;
}
.pip-disclaimer strong { color:var(--ink); }

/* ── Agents tab ────────────────────────────────────────────────── */
.agt-grid {
  display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
  gap:12px;
}
.agt-card {
  border:1px solid var(--bd); padding:16px;
  background:var(--bg); display:flex; flex-direction:column; gap:10px;
}
.agt-card-hd { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
.agt-tag {
  font-family:var(--font-mono); font-size:10px; font-weight:700;
  color:var(--ink); letter-spacing:.4px; text-transform:uppercase;
  line-height:1.3;
}
.agt-meta { display:flex; align-items:center; gap:4px; flex-shrink:0; }
.agt-meta-item {
  font-family:var(--font-mono); font-size:9px; color:var(--ink3);
  white-space:nowrap; display:flex; align-items:center; gap:3px;
}
.agt-meta-icon { font-size:9px; }
.agt-meta-sep { color:var(--bd); font-size:10px; }
.agt-who { font-size:11px; color:var(--ink3); line-height:1.5; margin:0; }
.agt-sim { font-size:12px; color:var(--ink2); line-height:1.6; margin:0; }
.agt-signals { display:flex; flex-direction:column; gap:4px; }
.agt-signal {
  font-size:11px; color:var(--ink2); padding-left:12px;
  position:relative; line-height:1.4;
}
.agt-signal::before {
  content:'→'; position:absolute; left:0;
  color:var(--ink3); font-size:10px;
}

/* ── Data sources tab ──────────────────────────────────────────── */
.ds-list { display:flex; flex-direction:column; gap:14px; }
.ds-item {
  border:1px solid var(--bd); padding:16px 18px;
  display:flex; flex-direction:column; gap:8px;
}
.ds-item-hd { display:flex; align-items:center; gap:10px; }
.ds-name {
  font-family:var(--font-mono); font-size:13px; font-weight:700;
  color:var(--ink); letter-spacing:.2px;
}
.ds-badge {
  font-family:var(--font-mono); font-size:9px; font-weight:700;
  padding:2px 8px; letter-spacing:.6px;
}
.ds-badge-live {
  background:rgba(22,163,74,.1); color:#16a34a;
  border:1px solid rgba(22,163,74,.3);
}
.ds-badge-hist {
  background:rgba(234,179,8,.08); color:#ca8a04;
  border:1px solid rgba(234,179,8,.25);
}
.ds-desc { font-size:13px; color:var(--ink2); line-height:1.65; margin:0; }
.ds-used-for {
  font-family:var(--font-mono); font-size:10px; color:var(--ink3);
  letter-spacing:.2px; padding-top:4px;
  border-top:1px solid var(--bd);
}

/* ── Methodology transition ────────────────────────────────────── */
.meth-fade-enter-active,
.meth-fade-leave-active { transition:opacity .2s ease; }
.meth-fade-enter-active .meth-panel,
.meth-fade-leave-active .meth-panel { transition:opacity .2s ease, transform .25s cubic-bezier(0.16,1,0.3,1); }
.meth-fade-enter-from { opacity:0; }
.meth-fade-enter-from .meth-panel { transform:translateY(16px); opacity:0; }
.meth-fade-leave-to { opacity:0; }
.meth-fade-leave-to .meth-panel { transform:translateY(8px); opacity:0; }

@media(max-width:600px) {
  .meth-body { padding:20px 16px 24px; }
  .meth-hd { padding:14px 16px; }
  .meth-tab { padding:10px 14px; font-size:10px; }
  .agt-grid { grid-template-columns:1fr; }
  .pip-num { font-size:20px; }
}

/* ── Agent role tag (always-visible type badge) ───────────────── */
.ag-role-tag {
  font-family:var(--font-mono); font-size:9px; font-weight:600;
  color:var(--ink3); background:var(--s2); border:1px solid var(--bd);
  padding:1px 6px; letter-spacing:.4px; white-space:nowrap;
  text-transform:uppercase;
}
.agent-row:hover .ag-role-tag {
  background:var(--acg); border-color:rgba(255,69,0,.25); color:var(--ac);
}

/* ── Agent profile panel (expands on row hover) ───────────────── */
.ag-profile {
  margin-top:10px;
  border-top:1px solid var(--bd);
  padding-top:10px;
  overflow:hidden;
}

.agp-who {
  font-family:var(--font-mono); font-size:10px; font-weight:600;
  color:var(--ac); letter-spacing:.3px; margin-bottom:6px;
}

.agp-desc {
  font-size:12px; color:var(--ink); line-height:1.7; margin-bottom:10px;
}

.agp-signals {
  display:flex; flex-direction:column; gap:4px; margin-bottom:10px;
}

.agp-sig {
  font-family:var(--font-mono); font-size:10px; color:var(--ink2);
  display:flex; align-items:flex-start; gap:7px; line-height:1.5;
}

.agp-sig-dot {
  color:var(--ac); font-size:7px; flex-shrink:0; margin-top:2px;
}

.agp-meta {
  display:flex; gap:18px; padding-top:8px; border-top:1px solid var(--bd);
}

.agp-meta-item {
  font-family:var(--font-mono); font-size:10px; color:var(--ink3);
  display:flex; align-items:center; gap:5px;
}

.agp-meta-item strong {
  color:var(--ink); font-weight:700;
}

/* ── Agent expand transition ──────────────────────────────────── */
.ag-expand-enter-active {
  transition:max-height .22s ease, opacity .2s ease;
  max-height:240px;
}
.ag-expand-leave-active {
  transition:max-height .15s ease, opacity .12s ease;
}
.ag-expand-enter-from { max-height:0; opacity:0; }
.ag-expand-enter-to   { max-height:240px; opacity:1; }
.ag-expand-leave-from { max-height:240px; opacity:1; }
.ag-expand-leave-to   { max-height:0; opacity:0; }

/* Same-shock dupe warning */
.shock-warn-dupe {
  display:block; margin-top:8px;
  font-family:var(--font-mono); font-size:11px;
  color:#b45309; background:rgba(217,119,6,.08);
  border:1px solid rgba(217,119,6,.3); padding:6px 12px;
  letter-spacing:.2px;
}

/* ── Compare toggle ───────────────────────────────────────────── */
.cmp-toggle-row {
  display:flex; align-items:center; gap:12px;
  margin:14px 0 0; padding-top:16px;
  border-top:1px solid var(--bd);
}
.cmp-toggle-btn {
  display:inline-flex; align-items:center; gap:7px;
  padding:6px 16px; border:1px solid var(--bd);
  background:transparent; color:var(--ink2);
  font-family:var(--font-mono); font-size:11px; font-weight:600;
  letter-spacing:.4px; cursor:pointer; transition:all .15s;
  text-transform:uppercase;
}
.cmp-toggle-btn:hover { border-color:var(--ac); color:var(--ac); background:var(--acg); }
.cmp-toggle-active { background:var(--ac) !important; border-color:var(--ac) !important; color:#fff !important; }
.cmp-toggle-hint {
  font-family:var(--font-mono); font-size:10px; color:var(--ink3);
  letter-spacing:.2px;
}

/* ── Scenario B shock section ─────────────────────────────────── */
.shock-section-b {
  margin-top:14px; padding-top:16px;
  border-top:1px dashed var(--bdh);
}
.shock-label-b { color:var(--ink); }
.shock-pill-b {
  border-color:var(--bd);
}
.shock-active-b {
  background:#000 !important; border-color:#000 !important; color:#fff !important;
}

/* Scenario A / B badges */
.scn-badge {
  display:inline-flex; align-items:center; justify-content:center;
  width:18px; height:18px;
  font-family:var(--font-mono); font-size:10px; font-weight:800;
  flex-shrink:0; letter-spacing:0;
}
.scn-a { background:var(--ac); color:#fff; }
.scn-b { background:#000; color:#fff; }

/* ── Comparison results ───────────────────────────────────────── */
.cmp-results { margin-top:24px; display:flex; flex-direction:column; gap:16px; }

/* Header band */
.cmp-header {
  background:var(--bg); border:1px solid var(--bd); overflow:hidden;
}
.cmp-route-line {
  padding:12px 20px 10px;
  border-bottom:1px solid var(--bd);
  display:flex; align-items:center; gap:8px;
  background:var(--s2);
}
.cmp-route-code { font-family:var(--font-mono); font-size:12px; font-weight:700; color:var(--ink); letter-spacing:.5px; }
.cmp-cabin-lbl, .cmp-date-lbl { font-family:var(--font-mono); font-size:11px; color:var(--ink3); }
.cmp-divider { color:var(--bd); font-family:var(--font-mono); }

.cmp-banner {
  display:flex; align-items:stretch;
}
.cmp-half {
  flex:1; padding:22px 24px;
  display:flex; flex-direction:column; gap:10px;
}
.cmp-a { border-right:1px solid var(--bd); }
.cmp-vs {
  padding:0 20px;
  display:flex; align-items:center; justify-content:center;
  font-family:var(--font-mono); font-size:12px; font-weight:800;
  color:var(--ink3); letter-spacing:1px;
  flex-shrink:0;
  border-right:1px solid var(--bd);
}
.cmp-scn-badge-wrap {
  display:flex; align-items:center; gap:8px;
}
.cmp-scn-shocks {
  font-family:var(--font-mono); font-size:11px; color:var(--ink2); letter-spacing:.2px;
}

.cmp-fare-line {
  display:flex; align-items:center; gap:10px; flex-wrap:wrap;
}
.cmp-base {
  font-family:var(--font-mono); font-size:22px; font-weight:800;
  color:var(--ink3); letter-spacing:-.5px;
}
.cmp-predicted {
  font-family:var(--font-mono); font-size:28px; font-weight:800; letter-spacing:-.5px;
}
.cmp-pct {
  font-family:var(--font-mono); font-size:14px; font-weight:700;
  padding:3px 10px; border:1px solid;
}
.cmp-up { color:var(--up); border-color:rgba(220,38,38,.25); background:rgba(220,38,38,.05); }
.cmp-dn { color:var(--dn); border-color:rgba(22,163,74,.25); background:rgba(22,163,74,.05); }

.cmp-meta-row { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
.cmp-conf { font-family:var(--font-mono); font-size:11px; color:var(--ink3); }
.cmp-cons { font-family:var(--font-mono); font-size:11px; color:var(--ink); font-weight:600; }

/* Delta summary bar */
.cmp-delta-bar {
  padding:10px 24px 12px;
  border-top:1px solid var(--bd);
  background:var(--s2);
  display:flex; align-items:center; gap:10px; flex-wrap:wrap;
}
.cdb-label {
  font-family:var(--font-mono); font-size:10px; font-weight:700;
  color:var(--ink3); text-transform:uppercase; letter-spacing:.4px;
  white-space:nowrap;
}
.cdb-val { font-size:13px; color:var(--ink); }

/* Comparison body */
.cmp-body { display:flex; flex-direction:column; gap:14px; }
.cmp-section-card {
  background:var(--bg); border:1px solid var(--bd); overflow:hidden;
}

/* Cascade comparison grid */
.cmp-cascade-grid { padding:0; }
.cmp-cas-row {
  display:grid; grid-template-columns:1fr 1fr 1fr;
  gap:0;
  border-bottom:1px solid var(--bd);
}
.cmp-cas-row:last-child { border-bottom:none; }
.cmp-cas-hdr {
  background:var(--s2);
  font-family:var(--font-mono); font-size:10px; font-weight:700;
  color:var(--ink3); text-transform:uppercase; letter-spacing:.4px;
}
.cmp-cas-node, .cmp-cas-val {
  padding:10px 16px; font-size:12px;
  display:flex; align-items:center; gap:6px;
  border-right:1px solid var(--bd);
}
.cmp-cas-val:last-child { border-right:none; }
.cmp-cas-node { color:var(--ink); font-weight:500; }
.cas-up { color:var(--up); font-weight:600; }
.cas-dn { color:var(--dn); font-weight:600; }
.cas-na { color:var(--ink3); }

/* Side by side narratives */
.cmp-narratives {
  display:grid; grid-template-columns:1fr 1fr;
}
.cmp-nar-col { border-right:1px solid var(--bd); }
.cmp-nar-col:last-child { border-right:none; }
.cmp-nar-hdr {
  padding:10px 20px;
  border-bottom:1px solid var(--bd);
  display:flex; align-items:center; gap:8px;
  font-family:var(--font-mono); font-size:11px; font-weight:600;
  color:var(--ink2); background:var(--s2);
  letter-spacing:.3px;
}
.cmp-nar-body { max-height:600px; overflow-y:auto; }

/* comparison mode tag */
.cmp-mode-tag {
  font-family:var(--font-mono); font-size:9px; font-weight:700;
  color:#fff; background:#000; padding:2px 7px;
  letter-spacing:.5px; text-transform:uppercase;
}

/* intro paragraph inside comparison cards */
.cmp-section-intro {
  padding:10px 20px 12px; font-size:12px; color:var(--ink3);
  border-bottom:1px solid var(--bd); line-height:1.65;
}

/* highlight rows where the two scenarios diverge */
.cas-row-diff { background:rgba(255,69,0,.03); }
.cas-diff-tag {
  display:inline-block; margin-left:6px;
  font-family:var(--font-mono); font-size:9px; font-weight:700;
  color:var(--ac); background:var(--acg); border:1px solid rgba(255,69,0,.25);
  padding:1px 5px; letter-spacing:.3px; text-transform:uppercase;
}

/* agent columns in compare mode */
.cmp-agents-cols {
  display:grid; grid-template-columns:1fr 1fr;
}
.cmp-agents-col { border-right:1px solid var(--bd); }
.cmp-agents-col:last-child { border-right:none; }
/* smaller agent rows in compare mode (less padding) */
.agent-row-cmp { padding:10px 16px !important; }
.agent-row-cmp .ag-reason { font-size:11px; }

/* predicted fare in narrative column header */
.cmp-nar-fare {
  margin-left:auto; font-family:var(--font-mono); font-size:11px;
  font-weight:700; color:var(--ink);
}

@media (max-width: 900px) {
  .cmp-banner { flex-direction:column; }
  .cmp-a { border-right:none; border-bottom:1px solid var(--bd); }
  .cmp-vs { padding:12px 24px; border-right:none; border-bottom:1px solid var(--bd); }
  .cmp-agents-cols { grid-template-columns:1fr; }
  .cmp-agents-col { border-right:none; border-bottom:1px solid var(--bd); }
  .cmp-agents-col:last-child { border-bottom:none; }
  .cmp-narratives { grid-template-columns:1fr; }
  .cmp-nar-col { border-right:none; border-bottom:1px solid var(--bd); }
  .cmp-nar-col:last-child { border-bottom:none; }
  .cmp-toggle-row { flex-wrap:wrap; }
  .cmp-cas-row { grid-template-columns:1fr 1fr 1fr; }
}

/* ── News Feed panel ──────────────────────────────────────────── */
.news-panel {
  margin-top:16px; border:1px solid var(--bd);
  background:var(--bg); overflow:hidden;
}
.news-panel-hd {
  display:flex; align-items:flex-start; gap:12px;
  padding:14px 20px; border-bottom:1px solid var(--bd);
  background:var(--s2);
}
.news-hd-icon { font-size:20px; flex-shrink:0; margin-top:1px; }
.news-hd-title {
  font-family:var(--font-mono); font-size:12px; font-weight:700;
  color:var(--ink); letter-spacing:.3px; margin-bottom:3px;
  display:flex; align-items:center; gap:8px;
}
.news-loading-badge {
  font-size:10px; color:var(--ink3); font-weight:400;
}
.news-hd-sub { font-size:12px; color:var(--ink3); line-height:1.5; }
.news-hd-actions { display:flex; align-items:center; gap:6px; margin-left:auto; flex-shrink:0; }
.news-action-btn {
  background:none; border:1px solid var(--bd); padding:4px 10px;
  font-family:var(--font-mono); font-size:11px; cursor:pointer; color:var(--ink2);
  transition:all .15s; letter-spacing:.2px;
}
.news-action-btn:hover { border-color:var(--ac); color:var(--ac); }
.news-refresh-btn {
  background:none; border:1px solid var(--bd); padding:4px 10px;
  font-family:var(--font-mono); font-size:13px; cursor:pointer; color:var(--ink2);
  transition:all .15s;
}
.news-refresh-btn:hover { border-color:var(--ac); color:var(--ac); }
.news-error {
  padding:12px 20px; font-size:12px; color:#b45309;
  background:rgba(217,119,6,.06); border-bottom:1px solid rgba(217,119,6,.2);
}
/* Loading skeleton */
.news-skeleton-list { padding:8px 12px; display:flex; flex-direction:column; gap:6px; }
.news-skeleton-item { padding:10px 12px; }
.nsk-line { height:10px; background:var(--s2); border-radius:2px; animation:shimmer 1.4s ease-in-out infinite; }
.nsk-title { width:80%; margin-bottom:6px; }
.nsk-meta { width:40%; height:8px; }
@keyframes shimmer { 0%,100%{opacity:.5} 50%{opacity:1} }
/* News items */
.news-items-list { padding:8px 12px; display:flex; flex-direction:column; gap:4px; max-height:380px; overflow-y:auto; }
.news-item {
  display:flex; align-items:flex-start; gap:12px;
  padding:10px 12px; cursor:pointer; border:1px solid transparent;
  transition:all .13s;
}
.news-item:hover { background:var(--s1); border-color:var(--bd); }
.news-item-sel {
  background:rgba(255,69,0,.04) !important;
  border-color:rgba(255,69,0,.3) !important;
}
.ni-check { flex-shrink:0; width:18px; height:18px; margin-top:1px; display:flex; align-items:center; justify-content:center; }
.ni-checked {
  width:18px; height:18px; background:var(--ac); color:#fff;
  font-size:10px; font-weight:900; display:flex; align-items:center; justify-content:center;
  font-family:var(--font-mono);
}
.ni-unchecked {
  width:18px; height:18px; border:1.5px solid var(--bd); display:block;
}
.ni-body { flex:1; min-width:0; }
.ni-title { font-size:13px; font-weight:500; color:var(--ink); line-height:1.5; margin-bottom:3px; }
.news-item-sel .ni-title { color:#000; }
.ni-meta { display:flex; gap:8px; align-items:center; }
.ni-cat-icon { font-size:12px; flex-shrink:0; }
.ni-cat {
  font-family:var(--font-mono); font-size:10px; font-weight:700;
  padding:1px 6px; letter-spacing:.2px;
}
.ni-cat-political { background:rgba(139,92,246,.1); color:#7c3aed; }
.ni-cat-weather   { background:rgba(6,182,212,.1);  color:#0891b2; }
.ni-cat-aviation  { background:rgba(255,69,0,.08);  color:var(--ac); }
.ni-geo {
  font-family:var(--font-mono); font-size:10px; font-weight:600;
  padding:1px 6px; letter-spacing:.3px;
}
.ni-geo-o { background:rgba(15,23,42,.06); color:var(--ink2); }
.ni-geo-d { background:rgba(15,23,42,.06); color:var(--ink2); }
.ni-source { font-family:var(--font-mono); font-size:10px; color:var(--ink3); font-weight:500; }
.ni-date { font-family:var(--font-mono); font-size:10px; color:var(--ink3); }
.ni-snippet { font-size:11px; color:var(--ink3); line-height:1.6; margin:6px 0 0; }
.news-empty { padding:16px 20px; font-size:12px; color:var(--ink3); }
</style>
