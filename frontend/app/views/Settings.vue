<script setup>
import { ref, watch } from 'vue'
import { apiPost, apiUpload } from '~/utils/api'
import { currentUser, isLoggedIn, applyUser, logout } from '~/composables/useAuth'
import PixelEditor from '../components/PixelEditor.vue'

const AVATAR_LIMIT = 1474560

const displayName = ref('')
const bio = ref('')
const profileMsg = ref('')
const profileErr = ref('')
const savingProfile = ref(false)

const currentPw = ref('')
const newPw = ref('')
const newPw2 = ref('')
const pwMsg = ref('')
const pwErr = ref('')
const savingPw = ref(false)

// プロフィール画像
const avatarInput = ref(null)
const avatarFile = ref(null)
const avatarPreview = ref('')
const avatarMsg = ref('')
const avatarErr = ref('')
const savingAvatar = ref(false)

// 返信の受け付け（既定はオフ＝返信できない）
const repliesEnabled = ref(false)
const replyMsg = ref('')
const replyErr = ref('')
const savingReply = ref(false)

// プロフィールアイコン（32×32 ドット絵）
const iconPixel = ref('')
const iconDraft = ref('')
const iconEditorOpen = ref(false)
const iconMsg = ref('')
const iconErr = ref('')
const savingIcon = ref(false)

// ログイン状態が復元されたらフォームに反映する
watch(
  currentUser,
  (u) => {
    if (u) {
      displayName.value = u.display_name || ''
      bio.value = u.bio || ''
      repliesEnabled.value = Boolean(u.allow_replies)
      iconPixel.value = u.icon_pixel || ''
    }
  },
  { immediate: true },
)

function openIconEditor() {
  iconErr.value = ''
  iconMsg.value = ''
  iconDraft.value = iconPixel.value
  iconEditorOpen.value = true
}

function cancelIconEditor() {
  iconDraft.value = iconPixel.value
  iconErr.value = ''
  iconEditorOpen.value = false
}

async function saveIcon() {
  iconErr.value = ''
  iconMsg.value = ''
  savingIcon.value = true

  try {
    const data = await apiPost('/update_icon_pixel', {
      pixel_data: iconDraft.value || '',
    })
    applyUser(data.user)
    iconPixel.value = data.user.icon_pixel || ''
    iconEditorOpen.value = false
    iconMsg.value = iconPixel.value
      ? 'プロフィールアイコンを保存しました。'
      : 'アイコンを未設定に戻しました。'
  } catch (e) {
    iconErr.value = e.message
  } finally {
    savingIcon.value = false
  }
}

async function clearIcon() {
  iconErr.value = ''
  iconMsg.value = ''
  savingIcon.value = true

  try {
    const data = await apiPost('/update_icon_pixel', { pixel_data: '' })
    applyUser(data.user)
    iconPixel.value = ''
    iconDraft.value = ''
    iconEditorOpen.value = false
    iconMsg.value = 'プロフィールアイコンを削除しました。'
  } catch (e) {
    iconErr.value = e.message
  } finally {
    savingIcon.value = false
  }
}

async function toggleReplies(event) {
  const next = Boolean(event.target.checked)
  replyMsg.value = ''
  replyErr.value = ''
  savingReply.value = true

  try {
    const data = await apiPost('/update_reply_setting', { allow_replies: next })
    applyUser(data.user)
    repliesEnabled.value = Boolean(data.user.allow_replies)
    replyMsg.value = next
      ? '返信を受け付けるようにしました。'
      : '返信を受け付けないようにしました。'
  } catch (e) {
    replyErr.value = e.message
    repliesEnabled.value = Boolean(currentUser.value?.allow_replies)
    if (event.target) event.target.checked = repliesEnabled.value
  } finally {
    savingReply.value = false
  }
}

async function saveProfile() {
  profileMsg.value = ''
  profileErr.value = ''
  savingProfile.value = true
  try {
    const data = await apiPost('/update_profile', {
      display_name: displayName.value,
      bio: bio.value,
    })
    applyUser(data.user)
    profileMsg.value = 'プロフィールを保存しました。'
  } catch (e) {
    profileErr.value = e.message
  } finally {
    savingProfile.value = false
  }
}

async function savePassword() {
  pwMsg.value = ''
  pwErr.value = ''

  if (newPw.value !== newPw2.value) {
    pwErr.value = '新しいパスワードが一致しません。'
    return
  }

  savingPw.value = true
  try {
    await apiPost('/change_password', {
      current_password: currentPw.value,
      new_password: newPw.value,
    })
    currentPw.value = ''
    newPw.value = ''
    newPw2.value = ''
    pwMsg.value = 'パスワードを変更しました。'
  } catch (e) {
    pwErr.value = e.message
  } finally {
    savingPw.value = false
  }
}

async function onLogout() {
  await logout()
  await navigateTo('/')
}

// ---------------------------------------------------------------------------
// プロフィール画像
// ---------------------------------------------------------------------------
function clearAvatarSelection() {
  if (avatarPreview.value) URL.revokeObjectURL(avatarPreview.value)
  avatarFile.value = null
  avatarPreview.value = ''
  if (avatarInput.value) avatarInput.value.value = ''
}

function onAvatarChange(event) {
  const file = event.target.files?.[0]
  if (!file) return

  avatarErr.value = ''
  avatarMsg.value = ''

  if (!file.type.startsWith('image/')) {
    avatarErr.value = '画像ファイルを選んでください。'
    return
  }

  if (file.size > AVATAR_LIMIT) {
    avatarErr.value = 'プロフィール画像は 1.44MB 以内にしてください。'
    return
  }

  if (avatarPreview.value) URL.revokeObjectURL(avatarPreview.value)
  avatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
}

async function saveAvatar() {
  if (!avatarFile.value) return

  avatarErr.value = ''
  avatarMsg.value = ''
  savingAvatar.value = true

  try {
    const form = new FormData()
    form.append('avatar', avatarFile.value)
    const data = await apiUpload('/update_avatar', form)
    applyUser(data.user)
    clearAvatarSelection()
    avatarMsg.value = 'プロフィール画像を更新しました。'
  } catch (e) {
    avatarErr.value = e.message
  } finally {
    savingAvatar.value = false
  }
}

async function removeAvatar() {
  avatarErr.value = ''
  avatarMsg.value = ''
  savingAvatar.value = true

  try {
    const form = new FormData()
    form.append('remove', '1')
    const data = await apiUpload('/update_avatar', form)
    applyUser(data.user)
    clearAvatarSelection()
    avatarMsg.value = 'プロフィール画像を削除しました。'
  } catch (e) {
    avatarErr.value = e.message
  } finally {
    savingAvatar.value = false
  }
}
</script>

<template>
  <div>
    <div v-if="!isLoggedIn" class="callout">
      <span>設定を変更するにはログインが必要です。</span>
      <NuxtLink class="btn btn-primary" to="/login">ログイン</NuxtLink>
      <NuxtLink class="btn" to="/register">新規登録</NuxtLink>
    </div>

    <template v-else>
      <section class="panel">
        <p class="section-kicker">ACCOUNT / SETTINGS</p>
        <h2 class="panel-title">アカウント設定</h2>
        <p class="panel-note">
          プロフィールとログイン情報を管理します。ユーザー名は変更できません。
        </p>
      </section>

      <section class="panel">
        <h2 class="panel-title">プロフィール画像</h2>

        <p v-if="avatarErr" class="msg msg-error">{{ avatarErr }}</p>
        <p v-if="avatarMsg" class="msg msg-info">{{ avatarMsg }}</p>

        <div class="avatar-editor">
          <img
            v-if="avatarPreview || currentUser.avatar_url"
            class="avatar-preview"
            :src="avatarPreview || currentUser.avatar_url"
            alt="プロフィール画像のプレビュー"
          />
          <div v-else class="avatar-preview avatar-preview-empty">
            未設定
          </div>

          <div class="avatar-editor-body">
            <div class="avatar-editor-actions">
              <label class="btn" for="avatar-file">画像を選ぶ</label>
              <input
                id="avatar-file"
                ref="avatarInput"
                class="image-input"
                type="file"
                accept="image/*"
                @change="onAvatarChange"
              />
              <button
                v-if="avatarFile"
                type="button"
                class="btn btn-primary"
                :disabled="savingAvatar"
                @click="saveAvatar"
              >
                {{ savingAvatar ? '保存中…' : 'この画像にする' }}
              </button>
              <button
                v-if="currentUser.avatar_url"
                type="button"
                class="link-btn danger"
                :disabled="savingAvatar"
                @click="removeAvatar"
              >
                画像を削除
              </button>
            </div>

            <p class="field-handle">
              「プロフィールアイコン（32×32 ドット絵）」も未設定のときは、
              最新投稿のドット絵がアイコンになります。
            </p>
          </div>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">プロフィールアイコン（32×32 ドット絵）</h2>
        <p class="panel-note">
          32×32 のドット絵アイコンを描いて設定できます。設定するとプロフィール画像より
          優先されます。未設定のときは、最新投稿のドット絵がアイコンになります。
        </p>

        <p v-if="iconErr" class="msg msg-error" role="alert">{{ iconErr }}</p>
        <p v-if="iconMsg" class="msg msg-info">{{ iconMsg }}</p>

        <div class="icon-editor-status">
          <span class="field-label">CURRENT ICON</span>
          <span class="icon-editor-state">
            {{ iconPixel ? '32×32 ドット絵を設定中' : '未設定' }}
          </span>
        </div>

        <div class="panel-actions">
          <button
            type="button"
            class="btn"
            @click="iconEditorOpen ? cancelIconEditor() : openIconEditor()"
          >
            {{ iconEditorOpen ? 'エディタを閉じる' : '32×32 アイコンを描く' }}
          </button>
          <button
            v-if="iconPixel"
            type="button"
            class="link-btn danger"
            :disabled="savingIcon"
            @click="clearIcon"
          >
            アイコンを削除
          </button>
        </div>

        <PixelEditor
          v-if="iconEditorOpen"
          v-model="iconDraft"
          :canvas-width="32"
          :canvas-height="32"
          :allow-resize="false"
        />

        <div v-if="iconEditorOpen" class="panel-actions">
          <button
            type="button"
            class="btn btn-primary"
            :disabled="savingIcon"
            @click="saveIcon"
          >
            {{ savingIcon ? '保存中…' : 'アイコンを保存' }}
          </button>
          <button
            type="button"
            class="btn"
            :disabled="savingIcon"
            @click="cancelIconEditor"
          >
            キャンセル
          </button>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">プロフィール</h2>

        <p v-if="profileErr" class="msg msg-error">{{ profileErr }}</p>
        <p v-if="profileMsg" class="msg msg-info">{{ profileMsg }}</p>

        <div class="field">
          <label class="field-label" for="display-name">表示名</label>
          <input
            id="display-name"
            v-model="displayName"
            class="input"
            type="text"
            maxlength="64"
            placeholder="例: フロッピー太郎"
          />
        </div>

        <div class="field">
          <label class="field-label" for="bio">bio（300 文字まで）</label>
          <textarea
            id="bio"
            v-model="bio"
            class="input"
            rows="3"
            maxlength="300"
            placeholder="自己紹介を書いてみましょう"
          ></textarea>
        </div>

        <div class="field-handle">
          ユーザー名 <b>@{{ currentUser.username }}</b> は変更できません。
        </div>

        <div class="panel-actions">
          <button
            type="button"
            class="btn btn-primary"
            :disabled="savingProfile"
            @click="saveProfile"
          >
            {{ savingProfile ? '保存中…' : '保存する' }}
          </button>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">返信</h2>
        <p class="panel-note">
          オンにすると、あなたの投稿に他のユーザーが返信できるようになります。
          初期設定はオフ（返信を受け付けない）です。
        </p>

        <p v-if="replyErr" class="msg msg-error" role="alert">{{ replyErr }}</p>
        <p v-if="replyMsg" class="msg msg-info">{{ replyMsg }}</p>

        <label class="check-row">
          <input
            type="checkbox"
            :checked="repliesEnabled"
            :disabled="savingReply"
            @change="toggleReplies"
          />
          <span class="check-row-body">
            <span class="check-row-title">返信を受け付ける</span>
            <span class="check-row-state">
              {{ repliesEnabled ? 'オン — 誰でも返信できます' : 'オフ — 返信できません' }}
            </span>
          </span>
        </label>
      </section>

      <section class="panel">
        <h2 class="panel-title">パスワード変更</h2>

        <p v-if="pwErr" class="msg msg-error">{{ pwErr }}</p>
        <p v-if="pwMsg" class="msg msg-info">{{ pwMsg }}</p>

        <div class="field">
          <label class="field-label" for="current-pw">現在のパスワード</label>
          <input
            id="current-pw"
            v-model="currentPw"
            class="input"
            type="password"
            autocomplete="current-password"
          />
        </div>

        <div class="field">
          <label class="field-label" for="new-pw">新しいパスワード（6 文字以上）</label>
          <input
            id="new-pw"
            v-model="newPw"
            class="input"
            type="password"
            autocomplete="new-password"
          />
        </div>

        <div class="field">
          <label class="field-label" for="new-pw2">新しいパスワード（確認）</label>
          <input
            id="new-pw2"
            v-model="newPw2"
            class="input"
            type="password"
            autocomplete="new-password"
          />
        </div>

        <div class="panel-actions">
          <button
            type="button"
            class="btn btn-primary"
            :disabled="savingPw"
            @click="savePassword"
          >
            {{ savingPw ? '変更中…' : 'パスワードを変更する' }}
          </button>
        </div>
      </section>

      <section class="panel">
        <h2 class="panel-title">ログアウト</h2>
        <p class="panel-note">
          この端末のログイン状態を解除します。
        </p>
        <div class="panel-actions">
          <button type="button" class="btn" @click="onLogout">ログアウトする</button>
        </div>
      </section>
    </template>
  </div>
</template>
