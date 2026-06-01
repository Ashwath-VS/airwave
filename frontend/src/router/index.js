import { createRouter, createWebHistory } from 'vue-router'
import SimulatorView from '../views/SimulatorView.vue'

const routes = [
  { path: '/', name: 'Simulator', component: SimulatorView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
