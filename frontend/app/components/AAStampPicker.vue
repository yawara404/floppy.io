<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import { useDialog } from '~/composables/useDialog'
import { aaGroups } from '~/utils/aaStamps'

const emit = defineEmits(['select', 'close'])

const CUSTOM_KEY = 'floppy_aa_stamps_v1'
const RECENT_KEY = 'floppy_aa_recent_v1'
const FAVORITES_KEY = 'floppy_aa_favorites_v1'
const MAX_CUSTOM = 50
const MAX_LENGTH = 300
const MAX_RECENT = 12

const presets = new Map(aaGroups.flatMap((group) => group.items.map((stamp) => [stamp.text, stamp])))
const custom = ref([])
const recent = ref([])
const favorites = ref([])
const category = ref('all')
const query = ref('')
const editing = ref(false)
const draft = ref('')
const message = ref('')
const hasError = ref(false)
const viewportStyle = ref(null)

const titleId = useId()
const editorId = useId()
const searchEl = ref(null)
const editorEl = ref(null)
const resultsEl = ref(null)
const addEl = ref(null)
const { dialogEl, closeEl } = useDialog()

const tabs = [
  { id: 'all', label: 'すべて' },
  { id: 'favorites', label: 'お気に入り' },
  { id: 'recent', label: '履歴' },
  ...aaGroups,
  { id: 'custom', label: '自作' },
]

function describeStamp(text) {
  return presets.get(text) || { text, title: '', category: '自作' }
}

function normalizeSearch(value) {
  return value.normalize('NFKC').toLowerCase()
}

const terms = computed(() => normalizeSearch(query.value).trim().split(/\s+/).filter(Boolean))

const sections = computed(() => {
  if (terms.value.length) {
    const texts = new Set([...favorites.value, ...recent.value, ...presets.keys(), ...custom.value])
    const matches = [...texts].map(describeStamp).filter((stamp) => {
      const haystack = normalizeSearch([stamp.text, stamp.title, stamp.category, stamp.keywords].join(' '))
      return terms.value.every((term) => haystack.includes(term))
    })
    return [{ id: 'search', label: '検索結果', items: matches }]
  }

  const personal = [
    { id: 'favorites', label: 'お気に入り', items: favorites.value.map(describeStamp) },
    { id: 'recent', label: '最近使った', items: recent.value.map(describeStamp) },
  ]
  const groups = [...personal, ...aaGroups, { id: 'custom', label: '自作', items: custom.value.map(describeStamp) }]

  if (category.value !== 'all') return groups.filter((group) => group.id === category.value)
  return [
    ...personal.map((group) => ({ ...group, items: group.items.slice(0, 6) })),
    ...groups.slice(personal.length),
  ].filter((group) => group.items.length)
})

const emptyMessages = {
  search: '見つかりませんでした。別の言葉や AA の一部で検索できます。',
  favorites: 'スタンプの ☆ を押すと、ここに並びます。',
  recent: '挿入したスタンプがここに並びます。',
  custom: '「＋ 自作を追加」から好きな AA を保存できます。',
}

const draftLength = computed(() => [...draft.value.replace(/\s+$/, '')].length)

function readList(key, limit) {
  try {
    const stored = JSON.parse(window.localStorage.getItem(key) || '[]')
    if (!Array.isArray(stored)) return []
    const texts = stored.filter((value) => typeof value === 'string' && value.trim())
    return [...new Set(texts)].slice(0, limit)
  } catch {
    return []
  }
}

function saveList(key, list, values) {
  try {
    window.localStorage.setItem(key, JSON.stringify(values))
    list.value = values
    return true
  } catch {
    notify('このブラウザに保存できませんでした。', true)
    return false
  }
}

function notify(text = '', error = false) {
  message.value = text
  hasError.value = error
}

function chooseStamp(text) {
  const used = [text, ...recent.value.filter((stamp) => stamp !== text)].slice(0, MAX_RECENT)
  saveList(RECENT_KEY, recent, used)
  emit('select', text)
}

function selectCategory(id) {
  category.value = id
  query.value = ''
  notify()
  resultsEl.value?.scrollTo({ top: 0 })
}

function clearSearch() {
  query.value = ''
  resultsEl.value?.scrollTo({ top: 0 })
  searchEl.value?.focus()
}

function handleSearchKey(event) {
  if (event.isComposing || event.keyCode === 229 || !terms.value.length) return
  const firstStamp = sections.value[0]?.items[0]
  if (!firstStamp) return

  if (event.key === 'Enter') {
    event.preventDefault()
    chooseStamp(firstStamp.text)
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    resultsEl.value?.querySelector('.aa-insert')?.focus()
  }
}

function restoreFocusIfRemoved(button) {
  nextTick(() => {
    if (!button.isConnected) closeEl.value?.focus()
  })
}

function toggleFavorite(text, button) {
  const isFavorite = favorites.value.includes(text)
  const values = isFavorite
    ? favorites.value.filter((stamp) => stamp !== text)
    : [text, ...favorites.value]
  if (saveList(FAVORITES_KEY, favorites, values)) {
    notify(isFavorite ? 'お気に入りから外しました。' : 'お気に入りに追加しました。')
    restoreFocusIfRemoved(button)
  }
}

async function startEditing() {
  editing.value = true
  notify()
  await nextTick()
  editorEl.value?.focus()
}

async function finishEditing(status = '') {
  editing.value = false
  notify(status)
  await nextTick()
  addEl.value?.focus()
}

function addStamp() {
  // AA の位置合わせに必要な先頭の空白は保持する。
  const text = draft.value.replace(/\s+$/, '')
  if (!text.trim()) {
    notify('スタンプを入力してください。', true)
    return
  }
  if (draftLength.value > MAX_LENGTH) {
    notify(`スタンプは ${MAX_LENGTH} 文字以内で保存できます。`, true)
    return
  }
  if (presets.has(text) || custom.value.includes(text)) {
    notify('同じスタンプが既にあります。', true)
    return
  }
  if (custom.value.length >= MAX_CUSTOM) {
    notify(`自作スタンプは ${MAX_CUSTOM} 件まで保存できます。`, true)
    return
  }

  if (saveList(CUSTOM_KEY, custom, [text, ...custom.value])) {
    draft.value = ''
    selectCategory('custom')
    finishEditing('このブラウザに保存しました。')
  }
}

function removeStamp(text, button) {
  if (saveList(CUSTOM_KEY, custom, custom.value.filter((stamp) => stamp !== text))) {
    notify('自作スタンプから削除しました。')
    restoreFocusIfRemoved(button)
  }
}

function fitToViewport() {
  const viewport = window.visualViewport
  // モバイルのソフトキーボードが開いても検索結果や保存ボタンを表示する。
  viewportStyle.value = viewport?.scale === 1 && viewport.height < window.innerHeight
    ? { '--aa-viewport-top': `${viewport.offsetTop}px`, '--aa-viewport-height': `${viewport.height}px` }
    : null
}

onMounted(async () => {
  custom.value = readList(CUSTOM_KEY, MAX_CUSTOM).map((text) => [...text].slice(0, MAX_LENGTH).join(''))
  recent.value = readList(RECENT_KEY, MAX_RECENT)
  favorites.value = readList(FAVORITES_KEY)
  window.visualViewport?.addEventListener('resize', fitToViewport)
  window.visualViewport?.addEventListener('scroll', fitToViewport)
  fitToViewport()
  await nextTick()
  if (window.matchMedia('(min-width: 601px) and (pointer: fine)').matches) searchEl.value?.focus()
})

onBeforeUnmount(() => {
  window.visualViewport?.removeEventListener('resize', fitToViewport)
  window.visualViewport?.removeEventListener('scroll', fitToViewport)
})
</script>

<template>
  <Teleport to="body">
    <dialog
      id="aa-panel"
      ref="dialogEl"
      class="aa-dialog"
      :style="viewportStyle"
      :aria-labelledby="titleId"
      @cancel.prevent="emit('close')"
      @click.self="emit('close')"
    >
      <div class="aa-window">
        <header class="aa-head">
          <h2 v-if="editing" :id="titleId">自作スタンプを追加</h2>
          <h2 v-else :id="titleId"><span class="aa-mark">AA</span> スタンプ</h2>
          <button ref="closeEl" type="button" class="aa-close" aria-label="閉じる" @click="emit('close')">
            ×
          </button>
        </header>

        <form v-if="editing" class="aa-editor" @submit.prevent="addStamp">
          <label :for="editorId" class="field-label">スタンプの AA</label>
          <textarea :id="editorId" ref="editorEl" v-model="draft" class="input aa-draft" rows="5" />
          <p class="aa-draft-info">
            <span>このブラウザに保存</span>
            <span :class="{ 'aa-error': draftLength > MAX_LENGTH }">{{ draftLength }} / {{ MAX_LENGTH }} 文字</span>
          </p>
          <div class="aa-editor-actions">
            <button type="button" class="btn" @click="finishEditing()">戻る</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </form>

        <template v-else>
          <div class="aa-controls">
            <div class="aa-search">
              <input
                ref="searchEl"
                v-model="query"
                type="search"
                class="input"
                placeholder="猫、お祝い、枠などで検索"
                aria-label="AA スタンプを検索"
                @input="resultsEl?.scrollTo({ top: 0 })"
                @keydown="handleSearchKey"
              />
              <button v-if="query" type="button" class="btn" aria-label="検索をクリア" @click="clearSearch">
                ×
              </button>
            </div>
            <div class="aa-tabs" :class="{ 'aa-tabs-searching': terms.length }" role="group" aria-label="スタンプの種類">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                type="button"
                class="aa-tab"
                :aria-pressed="!terms.length && category === tab.id"
                @click="selectCategory(tab.id)"
              >
                {{ tab.label }}
              </button>
            </div>
          </div>

          <div ref="resultsEl" class="aa-results">
            <section v-for="group in sections" :key="group.id" class="aa-section">
              <h3>{{ group.label }}</h3>
              <p v-if="!group.items.length" class="aa-empty">{{ emptyMessages[group.id] }}</p>
              <div v-else class="aa-grid">
                <div v-for="stamp in group.items" :key="stamp.text" class="aa-card">
                  <button
                    type="button"
                    class="aa-insert"
                    :title="stamp.text"
                    :aria-label="`${stamp.title || stamp.text} を挿入`"
                    @click="chooseStamp(stamp.text)"
                  >
                    <span class="aa-sample">{{ stamp.text }}</span>
                  </button>
                  <div class="aa-card-actions">
                    <span v-if="stamp.title" class="aa-name">{{ stamp.title }}</span>
                    <button
                      type="button"
                      class="aa-icon aa-star"
                      :aria-pressed="favorites.includes(stamp.text)"
                      :aria-label="`${stamp.title || stamp.text} のお気に入り`"
                      :title="favorites.includes(stamp.text) ? 'お気に入りから外す' : 'お気に入りに追加'"
                      @click="toggleFavorite(stamp.text, $event.currentTarget)"
                    >
                      {{ favorites.includes(stamp.text) ? '★' : '☆' }}
                    </button>
                    <button
                      v-if="category === 'custom' && !terms.length"
                      type="button"
                      class="aa-icon aa-remove"
                      :aria-label="`${stamp.text} を自作から削除`"
                      title="自作から削除"
                      @click="removeStamp(stamp.text, $event.currentTarget)"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <footer class="aa-footer">
            <button ref="addEl" type="button" class="btn" @click="startEditing">＋ 自作を追加</button>
          </footer>
        </template>

        <p class="aa-status" :class="{ 'aa-error': hasError }" role="status">{{ message }}</p>
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.aa-dialog {
  position: fixed;
  inset: 0;
  top: var(--aa-viewport-top, 0px);
  width: 100%;
  max-width: none;
  height: 100%;
  height: var(--aa-viewport-height, 100dvh);
  max-height: none;
  margin: 0;
  padding: 20px;
  overflow: hidden;
  border: 0;
  background: transparent;
  color: var(--ink);
}

.aa-dialog[open] {
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  place-items: center;
}

.aa-dialog::backdrop {
  background: rgb(25 37 29 / 52%);
}

.aa-window {
  display: flex;
  flex-direction: column;
  width: min(100%, 640px);
  max-height: 100%;
  min-height: 0;
  border: 2px solid var(--ink);
  background: var(--paper);
  box-shadow: 5px 5px 0 rgb(25 37 29 / 60%);
}

.aa-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 12px;
  border-bottom: 1px solid var(--line-strong);
  background: var(--header);
  color: var(--header-ink);
}

.aa-head h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
}

.aa-mark {
  padding: 5px 4px 4px;
  border: 1px solid currentColor;
  font: 10px/1 var(--font-pixel);
}

.aa-close {
  width: 44px;
  min-height: 44px;
  margin-left: auto;
  border: 0;
  border-left: 1px solid var(--line-strong);
  background: transparent;
  color: inherit;
  font-size: 22px;
  cursor: pointer;
}

.aa-close:hover {
  background: var(--header-2);
}

.aa-controls {
  padding: 12px 12px 10px;
  border-bottom: 1px dashed var(--line-strong);
}

.aa-search {
  display: flex;
  gap: 5px;
}

.aa-search input {
  min-width: 0;
  font-size: 16px;
}

.aa-search input::-webkit-search-cancel-button {
  display: none;
}

.aa-search .btn {
  width: 44px;
  flex-shrink: 0;
  padding: 0;
  font-size: 18px;
}

.aa-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 10px;
}

.aa-tab {
  min-height: 36px;
  padding: 3px 8px;
  border: 1px solid var(--line);
  background: var(--paper-2);
  color: var(--ink);
  font: 13px var(--font-display);
  cursor: pointer;
}

.aa-tab:hover {
  border-color: var(--accent);
}

.aa-tab[aria-pressed="true"] {
  border-color: var(--accent-deep);
  background: var(--accent-deep);
  color: var(--paper);
}

.aa-results {
  height: min(360px, 47dvh);
  min-height: 0;
  padding: 12px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.aa-section + .aa-section {
  margin-top: 16px;
}

.aa-section h3 {
  margin-bottom: 7px;
  color: var(--accent-deep);
  font-size: 14px;
}

.aa-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.aa-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 1px solid var(--line);
  background: var(--paper-2);
}

.aa-insert {
  display: grid;
  flex: 1;
  align-content: center;
  justify-items: center;
  width: 100%;
  min-height: 44px;
  padding: 5px;
  border: 0;
  background: transparent;
  color: var(--ink);
  cursor: pointer;
}

.aa-insert:hover,
.aa-icon:hover {
  background: var(--accent-soft);
}

.aa-sample {
  display: block;
  max-width: 100%;
  max-height: 4.95em;
  overflow: hidden;
  font: 13px/1.25 'IBM Plex Mono', ui-monospace, 'Noto Sans JP', monospace;
  text-overflow: ellipsis;
  white-space: pre;
}

.aa-name {
  margin-right: auto;
  color: var(--ink-2);
  font-family: var(--font-display);
  font-size: 12px;
}

.aa-card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 3px;
  padding-left: 8px;
  border-top: 1px dotted var(--line);
}

.aa-icon {
  width: 44px;
  min-height: 32px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-2);
  font: 18px/1 var(--font-body);
  cursor: pointer;
}

.aa-star[aria-pressed="true"] {
  color: var(--orange);
}

.aa-remove {
  color: var(--danger);
}

.aa-remove:hover {
  background: var(--paper-3);
}

.aa-card :focus-visible,
.aa-close:focus-visible {
  outline-offset: -2px;
}

.aa-empty {
  margin: 0;
  padding: 12px;
  border: 1px dashed var(--line);
  color: var(--muted);
  font-size: 13px;
}

.aa-footer {
  padding: 8px 12px;
  border-top: 1px solid var(--line);
  background: var(--paper-2);
}

.aa-editor {
  min-height: 0;
  padding: 12px;
  overflow-y: auto;
}

.aa-draft {
  min-height: 112px;
  resize: vertical;
  font: 16px/1.5 var(--font-mono);
}

.aa-draft-info {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin: 6px 0 12px;
  color: var(--muted);
  font-size: 12px;
}

.aa-editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.aa-status {
  margin: 0;
  color: var(--accent-deep);
  font-size: 12px;
}

.aa-status:not(:empty) {
  padding: 4px 12px;
  border-top: 1px solid var(--line);
}

.aa-error {
  color: var(--danger);
}

@media (max-width: 600px) {
  .aa-dialog {
    padding: 8px 8px max(8px, env(safe-area-inset-bottom));
  }

  .aa-dialog[open] {
    place-items: end center;
  }

  .aa-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .aa-tabs-searching {
    display: none;
  }

  .aa-icon {
    min-height: 40px;
  }
}
</style>
