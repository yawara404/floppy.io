<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import PixelEditor from './PixelEditor.vue'
import { apiPost, apiUpload, resolveMediaUrl } from '~/utils/api'
import { applyUser } from '~/composables/useAuth'
import { drawPixel } from '~/utils/pixel'

const props = defineProps({
  user: { type: Object, required: true },
})

const emit = defineEmits(['saved', 'cancel'])

const AVATAR_LIMIT = 1474560

const displayName = ref(props.user.display_name || '')
const bio = ref(props.user.bio || '')
const error = ref('')
const saving = ref(false)

// プロフィール画像（選択したファイルは「保存する」でアップロードする）
const avatarInput = ref(null)
const avatarFile = ref(null)
const avatarPreview = ref('')
const removeAvatar = ref(false)

// 32×32 アイコン
const iconDraft = ref(props.user.icon_pixel || '')
const iconEditorOpen = ref(false)
const iconPreview = ref(null)

// 再読み込みでユーザー情報が変わったらフォームへ反映する
watch(
  () => props.user.display_name,
  (value) => {
    displayName.value = value || ''
  },
)
watch(
  () => props.user.bio,
  (value) => {
    bio.value = value || ''
  },
)
watch(
  () => props.user.icon_pixel,
  (value) => {
    if (!iconEditorOpen.value) iconDraft.value = value || ''
  },
)

function renderIconPreview() {
  if (!iconPreview.value) return
  // 未設定のときは空白（32×32 の白）を表示する
  drawPixel(iconPreview.value, iconDraft.value || '0'.repeat(1024))
}

watch(iconDraft, renderIconPreview, { flush: 'post' })
onMounted(renderIconPreview)

onBeforeUnmount(() => {
  if (avatarPreview.value) URL.revokeObjectURL(avatarPreview.value)
})

function onAvatarChange(event) {
  const file = event.target.files?.[0]
  if (!file) return

  error.value = ''

  if (!file.type.startsWith('image/')) {
    error.value = '画像ファイルを選んでください。'
    return
  }

  if (file.size > AVATAR_LIMIT) {
    error.value = 'プロフィール画像は 1.44MB 以内にしてください。'
    return
  }

  if (avatarPreview.value) URL.revokeObjectURL(avatarPreview.value)
  avatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
  removeAvatar.value = false
}

function clearAvatarSelection() {
  if (avatarPreview.value) URL.revokeObjectURL(avatarPreview.value)
  avatarFile.value = null
  avatarPreview.value = ''
  if (avatarInput.value) avatarInput.value.value = ''
}

function markAvatarRemoved() {
  clearAvatarSelection()
  removeAvatar.value = true
}

function undoAvatarRemoval() {
  removeAvatar.value = false
}

function clearIconDraft() {
  iconDraft.value = ''
  iconEditorOpen.value = false
}

async function saveAll() {
  error.value = ''
  saving.value = true

  try {
    // 1. 表示名 / bio
    const profile = await apiPost('/update_profile', {
      display_name: displayName.value,
      bio: bio.value,
    })
    applyUser(profile.user)

    // 2. プロフィール画像（削除 or 新しい画像）
    if (removeAvatar.value) {
      const form = new FormData()
      form.append('remove', '1')
      const data = await apiUpload('/update_avatar', form)
      applyUser(data.user)
      removeAvatar.value = false
    } else if (avatarFile.value) {
      const form = new FormData()
      form.append('avatar', avatarFile.value)
      const data = await apiUpload('/update_avatar', form)
      applyUser(data.user)
      clearAvatarSelection()
    }

    // 3. 32×32 アイコン（変更されているときだけ保存）
    if (iconDraft.value !== (props.user.icon_pixel || '')) {
      const data = await apiPost('/update_icon_pixel', {
        pixel_data: iconDraft.value || '',
      })
      applyUser(data.user)
    }

    emit('saved')
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="panel profile-edit-panel">
    <div class="profile-edit-head">
      <div>
        <p class="section-kicker">EDIT PROFILE</p>
        <h2 class="panel-title">プロフィールを編集</h2>
      </div>
      <button type="button" class="link-btn" @click="$emit('cancel')">
        閉じる ×
      </button>
    </div>

    <p v-if="error" class="msg msg-error" role="alert">{{ error }}</p>

    <div class="field">
      <label class="field-label" for="edit-display-name">表示名</label>
      <input
        id="edit-display-name"
        v-model="displayName"
        class="input"
        type="text"
        maxlength="64"
        placeholder="例: フロッピー太郎"
      />
    </div>

    <div class="field">
      <label class="field-label" for="edit-bio">bio（300 文字まで）</label>
      <textarea
        id="edit-bio"
        v-model="bio"
        class="input"
        rows="3"
        maxlength="300"
        placeholder="自己紹介を書いてみましょう"
      ></textarea>
    </div>

    <!-- プロフィール画像 -->
    <div class="field">
      <span class="field-label">プロフィール画像</span>
      <div class="avatar-editor">
        <img
          v-if="avatarPreview || (!removeAvatar && user.avatar_url)"
          class="avatar-preview"
          :src="avatarPreview || resolveMediaUrl(user.avatar_url)"
          alt="プロフィール画像のプレビュー"
        />
        <div v-else class="avatar-preview avatar-preview-empty">未設定</div>

        <div class="avatar-editor-body">
          <div class="avatar-editor-actions">
            <label class="btn btn-sm" for="edit-avatar-file">画像を選ぶ</label>
            <input
              id="edit-avatar-file"
              ref="avatarInput"
              class="image-input"
              type="file"
              accept="image/*"
              @change="onAvatarChange"
            />
            <button
              v-if="avatarPreview"
              type="button"
              class="link-btn danger"
              @click="clearAvatarSelection"
            >
              選択を解除
            </button>
            <button
              v-if="user.avatar_url && !removeAvatar"
              type="button"
              class="link-btn danger"
              @click="markAvatarRemoved"
            >
              画像を削除
            </button>
            <button
              v-if="removeAvatar"
              type="button"
              class="link-btn"
              @click="undoAvatarRemoval"
            >
              削除をやめる
            </button>
          </div>
          <p class="field-handle">
            選択した画像は「保存する」で反映されます（1.44MB 以内）。
          </p>
        </div>
      </div>
    </div>

    <!-- 32×32 アイコン -->
    <div class="field">
      <span class="field-label">プロフィールアイコン（32×32 ドット絵）</span>
      <div class="icon-edit-row">
        <canvas
          ref="iconPreview"
          class="icon-preview"
          width="32"
          height="32"
        ></canvas>
        <div class="icon-edit-body">
          <div class="avatar-editor-actions">
            <button
              type="button"
              class="btn btn-sm"
              @click="iconEditorOpen = !iconEditorOpen"
            >
              {{ iconEditorOpen ? 'エディタを閉じる' : '32×32 アイコンを編集' }}
            </button>
            <button
              v-if="iconDraft"
              type="button"
              class="link-btn danger"
              @click="clearIconDraft"
            >
              アイコンを消す
            </button>
          </div>
          <p class="field-handle">
            設定するとプロフィール画像より優先されます。変更は「保存する」で反映されます。
          </p>
        </div>
      </div>
      <PixelEditor
        v-if="iconEditorOpen"
        v-model="iconDraft"
        :canvas-width="32"
        :canvas-height="32"
        :allow-resize="false"
      />
    </div>

    <div class="panel-actions">
      <button
        type="button"
        class="btn btn-primary"
        :disabled="saving"
        @click="saveAll"
      >
        {{ saving ? '保存中…' : '保存する' }}
      </button>
      <button type="button" class="btn" :disabled="saving" @click="$emit('cancel')">
        やめる
      </button>
      <NuxtLink class="link-btn profile-edit-settings" to="/settings">
        設定でパスワードを変更 →
      </NuxtLink>
    </div>

  </section>
</template>

