<script setup>
// ヘルプページ（静的な説明）
const faqs = [
  {
    q: 'floppy.io とは？',
    a: '「現代の Web はリソースを消費しすぎている」というアンチテーゼから生まれた、レトロコンピューティング趣味のミニマル SNS です。1 投稿あたりの容量上限はフロッピーディスク 1 枚分（1.44MB = 1,474,560 バイト）です。',
  },
  {
    q: '容量はどうやって数えている？',
    a: '1 投稿ごとに「本文の UTF-8 バイト数」と「ドット絵 256 バイト」を合算します。その投稿の合計が 1.44MB を超えると投稿できません（HTTP 403）。累計では制限していません。日本語は 1 文字 3 バイトとして数えます。',
  },
  {
    q: 'ドット絵はどう保存される？',
    a: '16×16 = 256 マスを、1 マス 1 桁の 16 進文字（0-9 / A-F）で表した 256 文字の文字列として保存します。画像ファイルには変換しないので、わずか 256 バイトで済みます。',
  },
  {
    q: '「フォーマット」って？',
    a: '自分の投稿を削除するボタンです。フロッピーディスクを初期化するイメージで「フォーマット」と呼んでいます。削除できるのは自分の投稿だけです。',
  },
  {
    q: 'フォロー中タイムラインって？',
    a: '自分がフォローしているユーザー（と自分）の投稿だけを新しい順に表示します。フォローするには、相手のプロフィールの「フォローする」を押します。フォロー中タイムラインを見るにはログインが必要です。',
  },
  {
    q: '共有ボタンは？',
    a: '各投稿の「共有」を押すと、共有リンクと外部サイトに貼り付けられる HTML スニペットが表示されます。共有リンクは投稿ごとのページ（/p/ID）を開きます。HTML はプレビュー API（/api/preview）が生成しています。',
  },
]
</script>

<template>
  <div>
    <section class="panel">
      <p class="section-kicker">MANUAL / FLOPPY.IO</p>
      <h2 class="panel-title">floppy.io の使い方</h2>
      <p class="panel-note">
        1 投稿＝フロッピー 1 枚。容量と相談しながら書いてください。
      </p>

      <div class="manual-stats">
        <div class="manual-stat">
          <b>1.44 MB</b>
          <span>PER POST</span>
        </div>
        <div class="manual-stat">
          <b>256 B</b>
          <span>16 × 16 PIXEL</span>
        </div>
        <div class="manual-stat">
          <b>16</b>
          <span>COLORS</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <p class="section-kicker">FAQ</p>
      <h2 class="panel-title">よくある質問</h2>

      <div class="faq">
        <details v-for="item in faqs" :key="item.q" class="faq-item">
          <summary>
            <span>{{ item.q }}</span>
            <span class="faq-icon" aria-hidden="true"></span>
          </summary>
          <p>{{ item.a }}</p>
        </details>
      </div>
    </section>

    <section class="panel">
      <p class="section-kicker">ACCOUNT</p>
      <h2 class="panel-title">アカウント</h2>
      <ul class="help-list">
        <li>ユーザー名は半角英数字とアンダースコア（_）の 3〜20 文字です。</li>
        <li>パスワードは 6 文字以上。ハッシュ化して保存されます。</li>
        <li>表示名と bio は <NuxtLink to="/settings">設定</NuxtLink> から変更できます。</li>
        <li>ログアウトは <NuxtLink to="/settings">設定</NuxtLink> から行えます。</li>
      </ul>
    </section>
  </div>
</template>
