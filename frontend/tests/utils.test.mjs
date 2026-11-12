import test from 'node:test'
import assert from 'node:assert/strict'
import {
  formatClock,
  formatDate,
  formatDateParts,
  formatDateTime,
  formatMonth,
  formatNumber,
} from '../app/utils/format.js'
import { hasPixelArt, postKindOf, youtubeThumbnail } from '../app/utils/post.js'

test('formatNumber inserts thousands separators and treats null as 0', () => {
  assert.equal(formatNumber(3388), '3,388')
  assert.equal(formatNumber(null), '0')
  assert.equal(formatNumber('1234'), '1,234')
})

test('formatDateTime uses the MySQL timestamp as local time', () => {
  assert.equal(formatDateTime('2026-11-06 15:19:00'), '2026/11/06 15:19')
  assert.equal(formatDateTime(''), '')
  assert.equal(formatDateTime('not-a-date'), 'not-a-date')
})

test('formatDate and formatClock return empty strings for invalid values', () => {
  assert.equal(formatDate('2026-11-06 15:19:00'), '2026/11/06')
  assert.equal(formatDate('bad'), '')
  assert.equal(formatClock('2026-11-06 15:19:00'), '15:19')
  assert.equal(formatClock('bad'), '')
})

test('formatDateParts splits date and time for the share card', () => {
  assert.deepEqual(formatDateParts('2026-11-06 15:19:00'), {
    time: '15:19',
    date: '2026/11/06',
  })
  assert.deepEqual(formatDateParts(''), { time: '', date: '' })
})

test('formatMonth renders the Japanese year/month used on profiles', () => {
  assert.equal(formatMonth('2026-09-21 10:00:00'), '2026年9月')
})

test('hasPixelArt ignores blank and transparent pixel data', () => {
  assert.equal(hasPixelArt({ pixel_data: '0'.repeat(256) }), false)
  assert.equal(hasPixelArt({ pixel_data: '' }), false)
  assert.equal(hasPixelArt({ pixel_data: '0000300000' }), true)
})

test('postKindOf follows the same priority as the site cards', () => {
  assert.equal(postKindOf({ youtube_id: 'abc', image_url: '/x.png' }), 'YOUTUBE')
  assert.equal(postKindOf({ image_url: '/x.png' }), 'IMAGE')
  assert.equal(postKindOf({ floppy_url: '/a.bin', floppy_kind: 'audio' }), 'AUDIO')
  assert.equal(postKindOf({ floppy_url: '/a.bin' }), 'FILE')
  assert.equal(postKindOf({ pixel_data: 'F' }), 'PIXEL')
  assert.equal(postKindOf({ text: 'hello' }), 'TEXT')
})

test('youtubeThumbnail falls back to hqdefault', () => {
  assert.equal(
    youtubeThumbnail({ youtube_id: 'abc' }),
    'https://i.ytimg.com/vi/abc/hqdefault.jpg',
  )
  assert.equal(
    youtubeThumbnail({ youtube_id: 'abc', youtube_thumbnail: 'https://x/t.jpg' }),
    'https://x/t.jpg',
  )
  assert.equal(youtubeThumbnail({}), '')
})
