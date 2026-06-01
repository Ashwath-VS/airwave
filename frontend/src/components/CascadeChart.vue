<template>
  <div class="cascade-chart" ref="container"></div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  impacts: { type: Object, default: () => ({}) },
})

const container = ref(null)
let resizeObs = null

const LABELS = {
  FUEL_COST:        'Fuel Cost',
  CASK:             'Unit Cost (CASK)',
  RASK:             'Revenue/Seat (RASK)',
  YIELD_MGT:        'Yield Mgt',
  OPERATING_MARGIN: 'Op. Margin',
  LOAD_FACTOR:      'Load Factor',
  ANCILLARY_REV:    'Ancillary Rev',
  HEDGING:          'Hedging',
  FLEET_UTIL:       'Fleet Util.',
  LABOR_COST:       'Labor',
  MAINTENANCE:      'Maintenance',
  DEMAND_INDEX:     'Demand Index',
}

function draw () {
  if (!container.value) return
  d3.select(container.value).selectAll('*').remove()

  const entries = Object.entries(props.impacts)
    .map(([k, v]) => ({ id: k, label: LABELS[k] || k, impact: v.impact, conf: v.confidence }))
    .filter(d => Math.abs(d.impact) > 0.001)
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
    .slice(0, 10)

  if (!entries.length) return

  const W   = container.value.clientWidth || 400
  const ROW = 26
  const ML  = 120
  const MR  = 56
  const MT  = 8
  const H   = entries.length * ROW + MT * 2

  const maxAbs = d3.max(entries, d => Math.abs(d.impact)) || 0.01
  const x = d3.scaleLinear().domain([-maxAbs, maxAbs]).range([ML, W - MR])

  const svg = d3.select(container.value)
    .append('svg')
    .attr('width', W)
    .attr('height', H)

  const g = svg.append('g')

  // Zero line
  g.append('line')
    .attr('x1', x(0)).attr('x2', x(0))
    .attr('y1', MT).attr('y2', H - MT)
    .attr('stroke', '#2a2a2a')
    .attr('stroke-width', 1)

  entries.forEach((d, i) => {
    const y    = MT + i * ROW
    const mid  = ROW / 2
    const bar0 = x(0)
    const barW = Math.abs(x(d.impact) - x(0))
    const barX = d.impact >= 0 ? bar0 : bar0 - barW
    const col  = d.impact >= 0 ? '#00e676' : '#ff3b30'

    // Label
    g.append('text')
      .attr('x', ML - 8)
      .attr('y', y + mid + 1)
      .attr('text-anchor', 'end')
      .attr('dominant-baseline', 'middle')
      .attr('fill', '#888')
      .attr('font-size', 11)
      .attr('font-family', 'JetBrains Mono, monospace')
      .text(d.label)

    // Bar
    g.append('rect')
      .attr('x', barX)
      .attr('y', y + 4)
      .attr('width', Math.max(barW, 1))
      .attr('height', ROW - 8)
      .attr('rx', 2)
      .attr('fill', col)
      .attr('opacity', 0.7 + d.conf * 0.3)

    // Value label
    g.append('text')
      .attr('x', d.impact >= 0 ? x(d.impact) + 4 : x(d.impact) - 4)
      .attr('y', y + mid + 1)
      .attr('text-anchor', d.impact >= 0 ? 'start' : 'end')
      .attr('dominant-baseline', 'middle')
      .attr('fill', col)
      .attr('font-size', 10)
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-weight', 600)
      .text(`${d.impact >= 0 ? '+' : ''}${(d.impact * 100).toFixed(0)}%`)
  })
}

watch(() => props.impacts, draw, { deep: true })

onMounted(() => {
  draw()
  resizeObs = new ResizeObserver(draw)
  if (container.value) resizeObs.observe(container.value)
})
onUnmounted(() => resizeObs?.disconnect())
</script>

<style scoped>
.cascade-chart { width: 100%; min-height: 60px; }
</style>
