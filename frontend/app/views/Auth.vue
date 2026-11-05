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

const isRegister = computed(() => props.mode === 'register')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (isRegister.value) {
      await register(username.value, password.value, displayName.value)
    } else {
      await login(username.value, password.value)
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
      <h2 class="auth-title">
        {{ isRegister ? '新しいディスクを用意する' : 'ディスクを読み込む' }}
      </h2>
      <p class="auth-sub">
        {{
          isRegister
            ? 'ユーザー名とパスワードだけで始められます。'
            : 'アカウントにログインして、タイムラインへ。'
        }}
      </p>

      <p v-if="error" class="msg msg-error">{{ error }}</p>

      <form @submit.prevent="submit">
        <div v-if="isRegister" class="field">
          <label class="field-label" for="display-name">表示名（省略可）</label>
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
          <label class="field-label" for="username">ユーザー名</label>
          <input
            id="username"
            v-model="username"
            class="input"
            type="text"
            autocomplete="username"
            :placeholder="isRegister ? '半角英数字と _ の 3〜20 文字' : ''"
          />
        </div>

        <div class="field">
          <label class="field-label" for="password">パスワード</label>
          <input
            id="password"
            v-model="password"
            class="input"
            type="password"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
            :placeholder="isRegister ? '6 文字以上' : ''"
          />
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
          <a href="#/login">ログイン</a>
        </template>
        <template v-else>
          アカウントをお持ちでない方は
          <a href="#/register">新規登録</a>
        </template>
      </p>
    </section>
    </div>
  </div>
</template>
