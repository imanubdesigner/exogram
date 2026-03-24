<template>
  <div class="graph-page container">
    <Navbar />

    <header class="network-header">
      <h1 class="network-title">{{ i18n.t('graph.title') }}</h1>
    </header>

    <div v-if="loading" class="state-msg">
      {{ i18n.t('graph.loading_network') }}
    </div>

    <div v-else-if="error" class="state-msg error">
      {{ error }}
    </div>

    <div v-else-if="Object.keys(graphNodes).length <= 1" class="empty-state">
      <p class="empty-text">{{ i18n.t('graph.empty_text') }}</p>
      <router-link to="/dashboard" class="btn-action">{{ i18n.t('graph.back_dashboard') }}</router-link>
    </div>

    <section v-else class="graph-panel">
      <div class="graph-panel-head">
        <div class="graph-panel-head-right">
          <div class="graph-controls">
            <div class="graph-control-inline">
              <label class="graph-control-label" for="tree-depth-select">{{ i18n.t('graph.label_depth') }}</label>
              <select
                id="tree-depth-select"
                v-model="requestedDepthSelection"
                class="graph-level-select"
                :aria-label="i18n.t('graph.depth_aria')"
              >
                <option v-for="depth in depthOptions" :key="`depth-option-${depth}`" :value="String(depth)">
                  {{ depth }}
                </option>
              </select>
            </div>
            <div class="graph-control-inline">
              <label class="graph-control-label" for="tree-nodes-select">{{ i18n.t('graph.label_nodes') }}</label>
              <select
                id="tree-nodes-select"
                v-model="requestedNodeLimitSelection"
                class="graph-level-select"
                :aria-label="i18n.t('graph.nodes_aria')"
              >
                <option v-for="limit in nodeLimitOptions" :key="`nodes-option-${limit}`" :value="String(limit)">
                  {{ limit }}
                </option>
              </select>
            </div>
            <div class="graph-control-inline">
              <select v-model="visibleLevelSelection" class="graph-level-select" :aria-label="i18n.t('graph.levels_aria')">
                <option value="all">{{ i18n.t('graph.all_levels') }}</option>
                <option v-for="level in availableLevels" :key="`level-option-${level}`" :value="String(level)">
                  {{ level }}
                </option>
              </select>
            </div>
            <div class="graph-zoom-controls" role="group" :aria-label="i18n.t('graph.zoom_group_aria')">
              <button
                class="btn-action btn-action-sm graph-zoom-btn"
                type="button"
                :disabled="zoomScale <= ZOOM_MIN"
                :aria-label="i18n.t('graph.zoom_out_aria')"
                @click="zoomOut"
              >
                -
              </button>
              <span class="graph-zoom-value">{{ zoomPercent }}%</span>
              <button
                class="btn-action btn-action-sm graph-zoom-btn"
                type="button"
                :disabled="zoomScale >= ZOOM_MAX"
                :aria-label="i18n.t('graph.zoom_in_aria')"
                @click="zoomIn"
              >
                +
              </button>
            </div>
            <button
              class="btn-action btn-action-sm graph-expand-btn"
              type="button"
              :disabled="loading"
              @click="applyTreeLimits"
            >
              {{ i18n.t('graph.apply') }}
            </button>
          </div>
          <button class="btn-action btn-action-sm graph-expand-btn" type="button" @click="openExpandedGraph">
            {{ i18n.t('graph.expand') }}
          </button>
        </div>
      </div>
      <p v-if="treeMeta.truncated" class="graph-note">
        {{ i18n.t('graph.note_truncated', { nodes: treeMeta.max_nodes, depth: treeMeta.max_depth }) }}
      </p>
      <div ref="graphWrapperRef" class="graph-wrapper" @mousedown="startPan($event, graphWrapperRef)">
        <svg :width="scaledSvgWidth" :height="scaledSvgHeight" class="tree-svg">
          <g class="zoom-layer" :transform="`scale(${zoomScale})`">
            <!-- Edges primero (debajo de nodos) -->
            <g class="edges-layer">
              <path
                v-for="edge in visibleEdges"
                :key="edge.id"
                :d="edge.d"
                class="tree-edge"
              />
            </g>

            <!-- Nodos -->
            <g class="nodes-layer">
              <g
                v-for="node in visibleNodes"
                :key="node.id"
                :transform="`translate(${node.x}, ${node.y})`"
                class="tree-node"
              >
                <circle
                  :r="node.is_root ? 10 : 7"
                  :class="['node-circle', { 'is-root': node.is_root }]"
                />
                <text
                  :dy="node.is_root ? -14 : -11"
                  class="node-label"
                  text-anchor="middle"
                >{{ node.name }}</text>
              </g>
            </g>
          </g>
        </svg>
      </div>
    </section>

    <div
      v-if="isGraphExpanded"
      class="graph-float-backdrop"
      role="dialog"
      aria-modal="true"
      :aria-label="i18n.t('graph.expand_aria')"
      @click.self="closeExpandedGraph"
    >
      <div class="graph-float-card">
        <div class="graph-float-head">
          <div class="graph-panel-head-right">
            <div class="graph-controls">
              <div class="graph-control-inline">
                <label class="graph-control-label" for="float-tree-depth-select">{{ i18n.t('graph.label_depth') }}</label>
                <select
                  id="float-tree-depth-select"
                  v-model="requestedDepthSelection"
                  class="graph-level-select"
                  :aria-label="i18n.t('graph.depth_aria')"
                >
                  <option v-for="depth in depthOptions" :key="`float-depth-option-${depth}`" :value="String(depth)">
                    {{ depth }}
                  </option>
                </select>
              </div>
              <div class="graph-control-inline">
                <label class="graph-control-label" for="float-tree-nodes-select">{{ i18n.t('graph.label_nodes') }}</label>
                <select
                  id="float-tree-nodes-select"
                  v-model="requestedNodeLimitSelection"
                  class="graph-level-select"
                  :aria-label="i18n.t('graph.nodes_aria')"
                >
                  <option v-for="limit in nodeLimitOptions" :key="`float-nodes-option-${limit}`" :value="String(limit)">
                    {{ limit }}
                  </option>
                </select>
              </div>
              <div class="graph-control-inline">
                <select v-model="visibleLevelSelection" class="graph-level-select" :aria-label="i18n.t('graph.levels_aria')">
                  <option value="all">{{ i18n.t('graph.all_levels') }}</option>
                  <option v-for="level in availableLevels" :key="`float-level-option-${level}`" :value="String(level)">
                    {{ level }}
                  </option>
                </select>
              </div>
              <div class="graph-zoom-controls" role="group" :aria-label="i18n.t('graph.zoom_group_aria')">
                <button
                  class="btn-action btn-action-sm graph-zoom-btn"
                  type="button"
                  :disabled="zoomScale <= ZOOM_MIN"
                  :aria-label="i18n.t('graph.zoom_out_aria')"
                  @click="zoomOut"
                >
                  -
                </button>
                <span class="graph-zoom-value">{{ zoomPercent }}%</span>
                <button
                  class="btn-action btn-action-sm graph-zoom-btn"
                  type="button"
                  :disabled="zoomScale >= ZOOM_MAX"
                  :aria-label="i18n.t('graph.zoom_in_aria')"
                  @click="zoomIn"
                >
                  +
                </button>
              </div>
              <button
                class="btn-action btn-action-sm graph-expand-btn"
                type="button"
                :disabled="loading"
                @click="applyTreeLimits"
              >
                {{ i18n.t('graph.apply') }}
              </button>
            </div>
            <button class="btn-action btn-action-sm graph-expand-btn" type="button" @click="closeExpandedGraph">
              {{ i18n.t('graph.close') }}
            </button>
          </div>
        </div>
        <p v-if="treeMeta.truncated" class="graph-note">
          {{ i18n.t('graph.note_active_limit', { nodes: treeMeta.max_nodes, depth: treeMeta.max_depth }) }}
        </p>
        <div
          ref="expandedGraphWrapperRef"
          class="graph-wrapper graph-wrapper-expanded"
          @mousedown="startPan($event, expandedGraphWrapperRef)"
        >
          <svg :width="scaledSvgWidth" :height="scaledSvgHeight" class="tree-svg">
            <g class="zoom-layer" :transform="`scale(${zoomScale})`">
              <g class="edges-layer">
                <path
                  v-for="edge in visibleEdges"
                  :key="`float-edge-${edge.id}`"
                  :d="edge.d"
                  class="tree-edge"
                />
              </g>
              <g class="nodes-layer">
                <g
                  v-for="node in visibleNodes"
                  :key="`float-node-${node.id}`"
                  :transform="`translate(${node.x}, ${node.y})`"
                  class="tree-node"
                >
                  <circle
                    :r="node.is_root ? 10 : 7"
                    :class="['node-circle', { 'is-root': node.is_root }]"
                  />
                  <text
                    :dy="node.is_root ? -14 : -11"
                    class="node-label"
                    text-anchor="middle"
                  >{{ node.name }}</text>
                </g>
              </g>
            </g>
          </svg>
        </div>
      </div>
    </div>

    <section class="invite-panel">
      <div v-if="loadingInvitations" class="invite-inline">
        <span class="invite-count text-muted">{{ i18n.t('graph.invite_loading') }}</span>
      </div>
      <div v-else-if="invitationsRemaining > 0" class="invite-inline">
        <span class="invite-count">{{ i18n.t('graph.invite_remaining', { count: invitationsRemaining }) }}</span>
        <div class="invite-form">
          <input
            v-model.trim="inviteEmail"
            type="email"
            class="invite-input"
            :placeholder="i18n.t('graph.invite_placeholder')"
            autocomplete="email"
          />
          <button class="btn-action" :disabled="sendingInvite || !inviteEmail" @click="sendInvitation">
            {{ sendingInvite ? i18n.t('graph.invite_sending') : i18n.t('graph.invite_send') }}
          </button>
        </div>
        <div class="invite-community-cta">
          <router-link :to="{ name: 'waitlist_community' }" class="btn-text">
            {{ i18n.t('graph.cta_community') }}
          </router-link>
        </div>
      </div>

      <div v-else class="invite-inline">
        <span class="invite-count text-muted">{{ i18n.t('graph.invite_none') }}</span>
      </div>
    </section>

    <section class="invited-list-section">
      <h3 class="section-label">{{ i18n.t('graph.sent_title') }}</h3>
      <div v-if="invitedUsers.length === 0" class="state-msg invited-empty">
        {{ i18n.t('graph.sent_empty') }}
      </div>
      <div v-else class="invited-list">
        <div v-for="invited in invitedUsers" :key="invited.id" class="invited-row" :class="invitationStatusClass(invited)">
          <div class="invited-main">
            <span class="invited-nickname">{{ invited.email }}</span>
            <span class="invited-status">
              {{ invitationStatusLabel(invited) }}
            </span>
          </div>
          <p v-if="invited.created_user_nickname" class="reset-feedback">
            {{ i18n.t('graph.temp_user') }}: @{{ invited.created_user_nickname }}
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'
import { useI18nStore } from '../stores/i18n'
import { authService } from '../services/auth'
import { logger } from '../utils/logger'
import Navbar from '../components/Navbar.vue'

const authStore = useAuthStore()
const uiStore = useUIStore()
const i18n = useI18nStore()

const rawNodes = ref({})
const rawEdges = ref({})
const treeMeta = ref({
  max_depth: 4,
  max_nodes: 180,
  truncated: false,
  nodes_returned: 0,
})
const loading = ref(true)
const error = ref(null)
const invitationsRemaining = ref(0)
const sendingInvite = ref(false)
const loadingInvitations = ref(true)
const inviteEmail = ref('')
const invitedUsers = ref([])
const isGraphExpanded = ref(false)
const visibleLevelSelection = ref('all')
const zoomScale = ref(1)
const requestedDepthSelection = ref('4')
const requestedNodeLimitSelection = ref('180')
const depthOptions = [2, 3, 4, 5, 6, 7, 8]
const nodeLimitOptions = [80, 120, 180, 260, 400, 600, 900]
const graphWrapperRef = ref(null)
const expandedGraphWrapperRef = ref(null)
const panState = ref({
  active: false,
  target: null,
  startX: 0,
  startY: 0,
  originLeft: 0,
  originTop: 0,
})

// Layout constants
const ZOOM_MIN = 0.6
const ZOOM_MAX = 2
const ZOOM_STEP = 0.15
const LEVEL_WIDTH = 160   // px entre niveles (eje X)
const NODE_GAP   = 48    // px entre nodos del mismo nivel (eje Y)
const PADDING_X  = 60
const PADDING_Y  = 24

/**
 * Construye un árbol jerárquico desde los datos planos de la API.
 * Asigna columna (depth) y fila (orden dentro del nivel) a cada nodo.
 */
const layout = computed(() => {
  const nodes = rawNodes.value
  const edges = rawEdges.value

  if (!Object.keys(nodes).length) return { nodes: [], edges: [] }

  // Construir mapa de hijos
  const children = {}
  for (const [, edge] of Object.entries(edges)) {
    if (!children[edge.source]) children[edge.source] = []
    children[edge.source].push(edge.target)
  }

  // Encontrar raíz
  const root = Object.values(nodes).find(n => n.is_root)
  if (!root) return { nodes: [], edges: [] }

  // BFS para asignar nivel (columna)
  const levelOf = {}
  const queue = [[root.name, 0]]
  const visited = new Set()
  while (queue.length) {
    const [id, level] = queue.shift()
    if (visited.has(id)) continue
    visited.add(id)
    levelOf[id] = level
    for (const child of (children[id] || [])) {
      if (!visited.has(child)) queue.push([child, level + 1])
    }
  }

  // Agrupar por nivel
  const byLevel = {}
  for (const [id, level] of Object.entries(levelOf)) {
    if (!byLevel[level]) byLevel[level] = []
    byLevel[level].push(id)
  }

  // Asignar coordenadas
  const maxLevel = Math.max(...Object.keys(byLevel).map(Number))
  const maxNodesInLevel = Math.max(...Object.values(byLevel).map(g => g.length))

  const positions = {}
  for (const [level, nodeIds] of Object.entries(byLevel)) {
    const col = parseInt(level)
    nodeIds.forEach((id, row) => {
      // Centrar verticalmente cada nivel
      const totalH = nodeIds.length * NODE_GAP
      const startY = (maxNodesInLevel * NODE_GAP - totalH) / 2
      positions[id] = {
        x: PADDING_X + col * LEVEL_WIDTH,
        y: PADDING_Y + startY + row * NODE_GAP
      }
    })
  }

  const renderedNodes = Object.keys(positions).map(id => ({
    id,
    name: nodes[id]?.name || id,
    is_root: nodes[id]?.is_root || false,
    depth: levelOf[id] ?? 0,
    x: positions[id].x,
    y: positions[id].y
  }))

  const renderedEdges = Object.entries(rawEdges.value).map(([id, edge]) => {
    const src = positions[edge.source]
    const tgt = positions[edge.target]
    if (!src || !tgt) return null
    const dx = Math.max(30, (tgt.x - src.x) * 0.45)
    const d = `M ${src.x} ${src.y} C ${src.x + dx} ${src.y}, ${tgt.x - dx} ${tgt.y}, ${tgt.x} ${tgt.y}`
    return { id, source: edge.source, target: edge.target, x1: src.x, y1: src.y, x2: tgt.x, y2: tgt.y, d }
  }).filter(Boolean)

  return { nodes: renderedNodes, edges: renderedEdges, maxLevel, maxNodesInLevel }
})

const renderedNodes = computed(() => layout.value.nodes || [])
const renderedEdges = computed(() => layout.value.edges || [])
const availableLevels = computed(() => {
  const totalLevels = Math.max(1, (layout.value.maxLevel ?? 0) + 1)
  return Array.from({ length: totalLevels }, (_, index) => index + 1)
})

const visibleDepthLimit = computed(() => {
  if (visibleLevelSelection.value === 'all') return Number.POSITIVE_INFINITY
  const selectedLevels = Number.parseInt(visibleLevelSelection.value, 10)
  if (!Number.isFinite(selectedLevels)) return Number.POSITIVE_INFINITY
  return Math.max(0, selectedLevels - 1)
})

const visibleNodes = computed(() =>
  renderedNodes.value.filter(node => (node.depth ?? 0) <= visibleDepthLimit.value)
)

const visibleNodeIds = computed(() => new Set(visibleNodes.value.map(node => node.id)))

const visibleEdges = computed(() =>
  renderedEdges.value.filter(edge => visibleNodeIds.value.has(edge.source) && visibleNodeIds.value.has(edge.target))
)

const visibleGraphStats = computed(() => {
  if (!visibleNodes.value.length) {
    return { maxDepth: 0, maxNodesInLevel: 1 }
  }
  const perDepth = {}
  let maxDepth = 0
  for (const node of visibleNodes.value) {
    const depth = node.depth ?? 0
    perDepth[depth] = (perDepth[depth] || 0) + 1
    maxDepth = Math.max(maxDepth, depth)
  }
  const maxNodesInLevel = Math.max(...Object.values(perDepth))
  return { maxDepth, maxNodesInLevel }
})

const svgBaseWidth = computed(() => {
  const maxDepth = visibleGraphStats.value.maxDepth || 0
  return PADDING_X * 2 + maxDepth * LEVEL_WIDTH + 60
})

const svgBaseHeight = computed(() => {
  const mn = visibleGraphStats.value.maxNodesInLevel || 1
  const contentHeight = Math.max(0, mn - 1) * NODE_GAP + 28
  return Math.max(140, PADDING_Y * 2 + contentHeight)
})

const scaledSvgWidth = computed(() => Math.ceil(svgBaseWidth.value * zoomScale.value))
const scaledSvgHeight = computed(() => Math.ceil(svgBaseHeight.value * zoomScale.value))
const zoomPercent = computed(() => Math.round(zoomScale.value * 100))

// Alias para el v-if del template
const graphNodes = computed(() => rawNodes.value)

const openExpandedGraph = () => {
  isGraphExpanded.value = true
}

const closeExpandedGraph = () => {
  endPan()
  isGraphExpanded.value = false
}

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

const zoomIn = () => {
  zoomScale.value = clamp(zoomScale.value + ZOOM_STEP, ZOOM_MIN, ZOOM_MAX)
}

const zoomOut = () => {
  zoomScale.value = clamp(zoomScale.value - ZOOM_STEP, ZOOM_MIN, ZOOM_MAX)
}

const handleGraphEscape = (event) => {
  if (event.key === 'Escape' && isGraphExpanded.value) {
    closeExpandedGraph()
    return
  }

  if (!isGraphExpanded.value || !expandedGraphWrapperRef.value) return
  const STEP = 80
  if (event.key === 'ArrowLeft') expandedGraphWrapperRef.value.scrollLeft -= STEP
  if (event.key === 'ArrowRight') expandedGraphWrapperRef.value.scrollLeft += STEP
  if (event.key === 'ArrowUp') expandedGraphWrapperRef.value.scrollTop -= STEP
  if (event.key === 'ArrowDown') expandedGraphWrapperRef.value.scrollTop += STEP
}

const resetPanState = () => {
  if (panState.value.target) {
    panState.value.target.classList.remove('is-panning')
  }
  panState.value = {
    active: false,
    target: null,
    startX: 0,
    startY: 0,
    originLeft: 0,
    originTop: 0,
  }
}

const onPanMove = (event) => {
  if (!panState.value.active || !panState.value.target) return
  const deltaX = event.clientX - panState.value.startX
  const deltaY = event.clientY - panState.value.startY
  panState.value.target.scrollLeft = panState.value.originLeft - deltaX
  panState.value.target.scrollTop = panState.value.originTop - deltaY
}

const endPan = () => {
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', endPan)
  resetPanState()
}

const startPan = (event, wrapperRef) => {
  if (event.button !== 0) return
  const target = wrapperRef?.value
  if (!target) return
  if (event.target.closest('button,select,input,textarea,a,label,option')) return
  panState.value = {
    active: true,
    target,
    startX: event.clientX,
    startY: event.clientY,
    originLeft: target.scrollLeft,
    originTop: target.scrollTop,
  }
  target.classList.add('is-panning')
  window.addEventListener('mousemove', onPanMove)
  window.addEventListener('mouseup', endPan)
  event.preventDefault()
}

watch(availableLevels, (levels) => {
  if (visibleLevelSelection.value === 'all') return
  const selectedLevels = Number.parseInt(visibleLevelSelection.value, 10)
  if (!Number.isFinite(selectedLevels)) {
    visibleLevelSelection.value = 'all'
    return
  }
  if (levels.length && selectedLevels > levels[levels.length - 1]) {
    visibleLevelSelection.value = String(levels[levels.length - 1])
  }
})

watch(isGraphExpanded, (expanded) => {
  if (expanded) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(async () => {
  window.addEventListener('keydown', handleGraphEscape)
  await Promise.all([
    loadNetworkTree(),
    loadInvitationData()
  ])
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleGraphEscape)
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', endPan)
  resetPanState()
  document.body.style.overflow = ''
})

const loadNetworkTree = async () => {
  error.value = null
  try {
    logger.debug('Cargando red de invitaciones')
    const selectedDepth = Number.parseInt(requestedDepthSelection.value, 10)
    const selectedNodeLimit = Number.parseInt(requestedNodeLimitSelection.value, 10)
    const data = await authService.getNetworkTree({
      maxDepth: Number.isFinite(selectedDepth) ? selectedDepth : undefined,
      maxNodes: Number.isFinite(selectedNodeLimit) ? selectedNodeLimit : undefined,
    })
    rawNodes.value = data.nodes
    rawEdges.value = data.edges
    treeMeta.value = {
      max_depth: data?.meta?.max_depth ?? selectedDepth ?? treeMeta.value.max_depth,
      max_nodes: data?.meta?.max_nodes ?? selectedNodeLimit ?? treeMeta.value.max_nodes,
      truncated: !!data?.meta?.truncated,
      nodes_returned: data?.meta?.nodes_returned ?? Object.keys(data.nodes || {}).length,
    }
    requestedDepthSelection.value = String(treeMeta.value.max_depth)
    requestedNodeLimitSelection.value = String(treeMeta.value.max_nodes)
  } catch (err) {
    logger.error('Error cargando red', err)
    error.value = i18n.t('graph.messages.tree_load_error')
  } finally {
    loading.value = false
  }
}

const applyTreeLimits = async () => {
  zoomScale.value = 1
  await loadNetworkTree()
}

const loadInvitationData = async () => {
  loadingInvitations.value = true
  try {
    logger.debug('Cargando datos de invitaciones en red')
    const statsData = await authStore.fetchInvitationStats()
    invitationsRemaining.value = statsData.remaining
    invitedUsers.value = Array.isArray(statsData.sent_invitations) ? statsData.sent_invitations : []
  } catch (err) {
    logger.error('Error loading invitation data on graph', err)
    uiStore.showError(i18n.t('graph.messages.invite_load_error'))
  } finally {
    loadingInvitations.value = false
  }
}

const invitationStatusClass = (invitation) => {
  if (invitation?.is_used) return 'status-active'
  if (invitation?.is_expired) return 'status-expired'
  return 'status-pending'
}

const invitationStatusLabel = (invitation) => {
  if (invitation?.is_used) {
    return invitation?.created_user_must_change_credentials
      ? i18n.t('graph.status_credentials_pending')
      : i18n.t('graph.status_active')
  }
  if (invitation?.is_expired) return i18n.t('graph.status_expired')
  return i18n.t('graph.status_pending')
}

const sendInvitation = async () => {
  const email = inviteEmail.value.trim().toLowerCase()
  if (!email) {
    uiStore.showError(i18n.t('graph.messages.invalid_email'))
    return
  }

  sendingInvite.value = true
  try {
    logger.debug('Enviando invitación por email', { email })
    const result = await authStore.sendInvitation(email)
    inviteEmail.value = ''
    uiStore.showSuccess(result.message || i18n.t('graph.messages.invite_sent'))
    await loadInvitationData()
    await loadNetworkTree()
  } catch (err) {
    logger.error('Error sending invitation email', err)
    uiStore.showError(err.message || i18n.t('graph.messages.invite_send_error'))
  } finally {
    sendingInvite.value = false
  }
}
</script>

<style scoped>
.graph-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  padding-bottom: var(--space-3xl);
}

/* Override global "section + section" margin — the flex gap handles spacing here */
.graph-page > section + section {
  margin-top: 0;
}

.network-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  margin-bottom: var(--space-sm);
}

.network-title {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  margin: 0;
  text-transform: lowercase;
}

.invite-panel,
.invited-list-section,
.graph-panel,
.empty-state {
  border: 1px solid var(--border-subtle);
  border-radius: var(--border-radius);
  background: var(--bg-secondary, transparent);
  padding: var(--space-md);
}

.invite-panel {
  display: flex;
  justify-content: stretch;
}

.invite-inline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  width: 100%;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.invite-count {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  letter-spacing: 0.03em;
  text-transform: lowercase;
}

.invite-form {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-sm);
  flex: 1;
  max-width: 400px;
}

.invite-community-cta {
  flex-basis: 100%;
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-xs);
}

.btn-text {
  font-family: var(--font-display);
  font-size: var(--font-size-sm);
  font-style: italic;
  color: var(--text-tertiary);
  border-bottom: 1px solid transparent;
  transition: color var(--transition-fast), border-color var(--transition-fast);
}

.btn-text:hover {
  color: var(--text-primary);
  border-bottom-color: var(--text-primary);
}

.invite-input {
  width: 100%;
  min-height: 32px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-primary);
  padding: 0 var(--space-sm);
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
}

.btn-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: 0 var(--space-md);
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  letter-spacing: 0.04em;
  text-transform: lowercase;
  text-decoration: none;
}

.btn-action:hover {
  border-color: var(--text-primary);
  background: rgba(10, 10, 10, 0.04);
  color: var(--text-primary);
}

.btn-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-action-sm {
  min-height: 28px;
  padding: 0 var(--space-sm);
  font-size: 10px;
}

.section-label {
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  margin-bottom: var(--space-md);
}

.invited-empty {
  text-align: center;
  padding: var(--space-sm) 0 0;
}

.invited-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.invited-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.invited-row:last-child {
  border-bottom: none;
}

.invited-main {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-sm);
}

.invited-nickname {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.invited-status {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  letter-spacing: 0.03em;
  flex-shrink: 0;
}

.invited-row.status-active .invited-status {
  color: var(--text-secondary);
}

.invited-row.status-expired .invited-status {
  opacity: 0.5;
}

.invited-row.status-expired .invited-nickname {
  opacity: 0.5;
}

.reset-feedback {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-family: var(--font-ui);
  font-style: italic;
}

.graph-panel-head {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.graph-panel-head-right {
  display: flex;
  width: 100%;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.graph-controls {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  justify-content: flex-end;
  flex-wrap: wrap;
}

.graph-control-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.graph-control-label {
  font-size: 10px;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.graph-level-select {
  min-height: 26px;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-ui);
  font-size: 11px;
  padding: 0 8px;
  text-transform: lowercase;
}

.graph-level-select:focus {
  outline: none;
  border-color: var(--text-primary);
}

.graph-zoom-controls {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.graph-zoom-btn {
  width: 26px;
  min-width: 26px;
  padding: 0;
  font-size: 14px;
  line-height: 1;
}

.graph-zoom-value {
  min-width: 40px;
  text-align: center;
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
}

.graph-panel {
  padding: var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.graph-expand-btn {
  min-height: 26px;
  padding: 0 var(--space-sm);
}

.graph-wrapper {
  background:
    radial-gradient(circle at 20% 20%, rgba(10, 10, 10, 0.02) 0%, transparent 45%),
    radial-gradient(circle at 85% 80%, rgba(10, 10, 10, 0.03) 0%, transparent 40%),
    var(--bg-primary);
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  overflow-x: auto;
  overflow-y: auto;
  cursor: grab;
  min-height: 150px;
  max-height: 400px;
  padding: var(--space-md);
}

.graph-wrapper.is-panning {
  cursor: grabbing;
  user-select: none;
}

.tree-svg {
  display: block;
  min-width: max-content;
}

.graph-float-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-lg);
  background: rgba(252, 252, 252, 0.74);
  backdrop-filter: blur(6px);
}

.graph-float-card {
  width: min(1200px, 100%);
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  background: var(--bg-secondary, #fff);
  padding: var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.06);
}

.graph-float-head {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.graph-wrapper-expanded {
  min-height: 62vh;
  max-height: 78vh;
  padding: var(--space-md);
}

.tree-edge {
  stroke: var(--border-medium);
  stroke-width: 1.1;
  opacity: 0.75;
  fill: none;
}

.node-circle {
  fill: var(--bg-secondary);
  stroke: var(--border-medium);
  stroke-width: 1.4;
  transition: all 0.2s ease;
}

.node-circle.is-root {
  fill: var(--text-primary);
  stroke: var(--text-primary);
}

.tree-node:hover .node-circle {
  fill: rgba(184, 138, 50, 0.2);
  stroke: #b88a32;
}

.node-label {
  font-family: var(--font-display);
  font-size: 11px;
  fill: var(--text-secondary);
  pointer-events: none;
  letter-spacing: 0.02em;
}

.state-msg {
  text-align: center;
  padding: var(--space-2xl) 0;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

.state-msg.error {
  color: #991B1B;
}

.graph-note {
  margin: 0;
  font-size: 11px;
  color: var(--text-tertiary);
  font-style: italic;
}

.empty-state {
  text-align: center;
}

.empty-text {
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  font-style: italic;
  color: var(--text-tertiary);
  margin: 0 0 var(--space-md) 0;
}

@media (max-width: 640px) {
  .invite-panel,
  .invited-list-section,
  .graph-panel,
  .empty-state {
    padding: var(--space-sm);
  }

  .graph-panel {
    padding: var(--space-xs);
  }

  .graph-panel-head-right {
    width: 100%;
    justify-content: flex-end;
    gap: var(--space-xs);
  }

  .graph-controls {
    justify-content: flex-end;
  }

  .graph-control-inline {
    max-width: 112px;
  }

  .graph-float-backdrop {
    padding: var(--space-sm);
  }

  .graph-float-card {
    padding: var(--space-xs);
  }

  .graph-wrapper-expanded {
    min-height: 68vh;
    max-height: 82vh;
  }

  .invite-inline {
    justify-content: space-between;
    align-items: flex-start;
    gap: var(--space-sm);
  }

  .invited-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
}
</style>
