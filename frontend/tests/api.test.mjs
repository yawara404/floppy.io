import test from 'node:test'
import assert from 'node:assert/strict'
import { apiGet, apiPost, apiUpload, ApiError, setAuthToken, resolveMediaUrl } from '../app/utils/api.js'

function mockFetch(t, handler) {
  const original = globalThis.fetch
  globalThis.fetch = handler
  t.after(() => { globalThis.fetch = original; setAuthToken('') })
}

test('authenticated requests preserve the HTTP method, JSON body and token', async (t) => {
  mockFetch(t, async (url, options) => {
    assert.equal(url, '/api/posts')
    assert.equal(options.method, 'POST')
    assert.equal(options.headers.Authorization, 'Bearer test-token')
    assert.equal(options.body, JSON.stringify({ text: '日本語の投稿' }))
    return Response.json({ post: { id: 1 } })
  })
  setAuthToken('test-token')
  assert.equal((await apiPost('/posts', { text: '日本語の投稿' })).post.id, 1)
})

test('HTML returned with HTTP 200 is an error, not an empty timeline', async (t) => {
  mockFetch(t, async () => new Response('<html>proxy fallback</html>'))
  await assert.rejects(apiGet('/posts'), (e) => e instanceof ApiError && /正しいデータ/.test(e.message))
})

test('an empty successful response cannot masquerade as valid data', async (t) => {
  mockFetch(t, async () => new Response(null, { status: 204 }))
  await assert.rejects(apiGet('/posts'), ApiError)
})

test('FastAPI field validation is converted to readable text', async (t) => {
  mockFetch(t, async () => Response.json({ detail: [{ msg: '入力が必要です' }] }, { status: 422 }))
  await assert.rejects(apiPost('/register', {}), (e) => e.status === 422 && e.message === '入力が必要です')
})

test('proxy failures and offline errors have actionable messages', async (t) => {
  mockFetch(t, async () => new Response('Bad Gateway', { status: 502 }))
  await assert.rejects(apiGet('/posts'), (e) => e.status === 502 && /接続できません/.test(e.message))
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  await assert.rejects(apiGet('/posts'), (e) => e.status === 0 && /再試行/.test(e.message))
})

test('hung requests time out and abort the underlying fetch', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  mockFetch(t, (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  }))
  const request = apiGet('/posts')
  const rejection = assert.rejects(request, (e) => e.status === 0 && /時間がかかっています/.test(e.message))
  t.mock.timers.tick(20000)
  await rejection
})

test('uploads allow the browser to set multipart boundaries', async (t) => {
  const form = new FormData()
  form.append('text', '添付のある投稿')
  mockFetch(t, async (_url, options) => {
    assert.equal(options.headers['Content-Type'], undefined)
    assert.equal(options.body, form)
    return Response.json({ post: { id: 2 } })
  })
  assert.equal((await apiUpload('/posts', form)).post.id, 2)
})

test('media URLs work on deep routes and subdirectory deployments', (t) => {
  const original = globalThis.window
  globalThis.window = { __FLOPPY_API_BASE__: '/floppy.io/api' }
  t.after(() => { if (original === undefined) delete globalThis.window; else globalThis.window = original })
  assert.equal(resolveMediaUrl('./uploads/image.png'), '/floppy.io/uploads/image.png')
  assert.equal(resolveMediaUrl('/uploads/image.png'), '/floppy.io/uploads/image.png')
  assert.equal(resolveMediaUrl('/floppy.io/uploads/image.png'), '/floppy.io/uploads/image.png')
  assert.equal(resolveMediaUrl('https://example.com/a.png'), 'https://example.com/a.png')
})
