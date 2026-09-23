<script setup>
import { ref, watch } from 'vue'
import { apiPost, apiUpload } from '../utils/api.js'
import { currentUser, isLoggedIn, applyUser, logout } from '../store/auth.js'
import { navigate } from '../utils/router.js'

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

// ログイン状態が復元されたらフォームに反映する
watch(
  currentUser,
  (u) => {
    if (u) {
      displayName.value = u.display_name || ''
      bio.value = u.bio || ''
    }
  },
  { immediate: true },
)

async function saveProfile() {
  profileMsg.value = ''
  profileErr.value = ''
  savingProfile.value = true
  try {
    const data = await apiPost('/update_profile.php', {
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
    await apiPost('/change_password.php', {
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
  navigate('/')
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
    const data = await apiUpload('/update_avatar.php', form)
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
    const data = await apiUpload('/update_avatar.php', form)
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
      <a class="btn btn-primary" href="#/login">ログイン</a>
      <a class="btn" href="#/register">新規登録</a>
    </div>

    <template v-else>
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
              未設定のときは、最新投稿のドット絵がアイコンになります。
            </p>
          </div>
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
