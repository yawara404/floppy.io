<script setup>
import { ref, computed } from 'vue'
import { login, register } from '~/composables/useAuth'

const props = defineProps({
  mode: { type: String, default: 'login' },
})

const username = ref('')
const password = ref('')
const displayName = ref('')
const error = ref('')
const loading = ref(false)
const showPassword = ref(false)

const isRegister = computed(() => props.mode === 'register')

async function submit() {
  if (loading.value) return
  error.value = ''
  loading.value = true
  try {
    if (isRegister.value) {
      await register(username.value.trim(), password.value, displayName.value.trim())
    } else {
      await login(username.value.trim(), password.value)
    }
    navigateTo('/')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <div class="auth-shell">
    <aside class="auth-aside" aria-hidden="true">
      <div>
        <p class="auth-aside-kicker">FLOPPY.IO / ACCESS TERMINAL</p>
        <h2 class="auth-aside-title">
          1.44MB<span>の世界へ。</span>
        </h2>
        <p class="auth-aside-note">
          書けるのは、ディスク 1 枚分。
          だから、残したいものだけが残る。
        </p>
      </div>

      <div class="auth-disk"></div>
    </aside>

    <section class="panel auth-panel">
      <p class="auth-kicker">
        {{ isRegister ? 'CREATE ACCOUNT' : 'WELCOME BACK' }}
      </p>
      <h1 class="auth-title">
        {{ isRegister ? '新しいディスクを用意する' : 'ディスクを読み込む' }}
      </h1>
      <p class="auth-sub">
        {{
          isRegister
            ? 'ユーザー名とパスワードだけで始められます。'
            : 'アカウントにログインして、タイムラインへ。'
        }}
      </p>

      <p v-if="error" id="auth-error" class="msg msg-error" role="alert">{{ error }}</p>

      <form :aria-busy="loading" @submit.prevent="submit">
        <div v-if="isRegister" class="field">
          <label class="field-label" for="display-name">表示名（省略可）</label>
          <input
            id="display-name"
            v-model="displayName"
            class="input"
            type="text"
            maxlength="64"
            autocomplete="nickname"
            placeholder="例: フロッピー太郎"
          />
        </div>

        <div class="field">
          <label class="field-label" for="username">ユーザー名</label>
          <input
            id="username"
            v-model="username"
            class="input"
            type="text"
            autocomplete="username"
            autocapitalize="none"
            :spellcheck="false"
            required
            :minlength="isRegister ? 3 : undefined"
            :maxlength="isRegister ? 20 : undefined"
            :pattern="isRegister ? '[A-Za-z0-9_]{3,20}' : undefined"
            :aria-describedby="isRegister ? 'username-hint' : undefined"
            :placeholder="isRegister ? '半角英数字と _ の 3〜20 文字' : ''"
          />
        </div>

        <p v-if="isRegister" id="username-hint" class="field-hint">半角英数字と _、3〜20 文字。プロフィールの URL に使います。</p>

        <div class="field">
          <label class="field-label" for="password">パスワード</label>
          <div class="password-field">
            <input
              id="password"
              v-model="password"
              class="input"
              :type="showPassword ? 'text' : 'password'"
              required
              :minlength="isRegister ? 6 : undefined"
              :aria-describedby="isRegister ? 'password-hint' : undefined"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
              :placeholder="isRegister ? '6 文字以上' : ''"
            />
            <button
              type="button"
              class="password-toggle"
              :aria-label="showPassword ? 'パスワードを隠す' : 'パスワードを表示する'"
              :aria-pressed="showPassword"
              @click="showPassword = !showPassword"
            >{{ showPassword ? '隠す' : '表示' }}</button>
          </div>
          <p v-if="isRegister" id="password-hint" class="field-hint">6 文字以上。他のサービスと異なるパスワードをおすすめします。</p>
        </div>

        <div class="panel-actions">
          <button type="submit" class="btn btn-primary" :disabled="loading">
            {{ loading ? '処理中…' : isRegister ? '登録する' : 'ログインする' }}
          </button>
        </div>
      </form>

      <p class="auth-switch">
        <template v-if="isRegister">
          すでにアカウントがある方は
          <NuxtLink to="/login">ログイン</NuxtLink>
        </template>
        <template v-else>
          アカウントをお持ちでない方は
          <NuxtLink to="/register">新規登録</NuxtLink>
        </template>
      </p>
    </section>
    </div>
  </div>
</template>
