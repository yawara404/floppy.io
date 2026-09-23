<script setup>
import { ref, computed } from 'vue'
import { login, register } from '../store/auth.js'
import { navigate } from '../utils/router.js'

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
    navigate('/')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel auth-panel">
    <h2 class="panel-title">
      {{ isRegister ? '新規登録' : 'ログイン' }}
    </h2>

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
</template>
