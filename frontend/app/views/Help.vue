<script setup>
// ヘルプページ（静的な説明）
const faqs = [
  {
    q: 'floppy.io とは？',
    a: '「現代の Web はリソースを消費しすぎている」というアンチテーゼから生まれた、レトロコンピューティング趣味のミニマル SNS です。1 投稿あたりの容量上限はフロッピーディスク 1 枚分（1.44MB = 1,474,560 バイト）です。',
  },
  {
    q: '容量はどうやって数えている？',
    a: '1 投稿ごとに本文の UTF-8 バイト数、選択中のドット絵キャンバス、添付画像、添付ファイルを合算します。1 投稿の合計が 1.44MB を超えると投稿できません。累計には制限がありません。日本語の多くは 1 文字 3 バイト、絵文字などはそれ以上になる場合があります。',
  },
  {
    q: 'ドット絵はどう保存される？',
    a: '1 マスを 1 桁の 16 進文字（0-9 / A-F）で保存します。32×32 は 1,024 バイト、32×24 は 768 バイト、16×16 は 256 バイト。16 色のパレットと 3 種類のキャンバスで描けます。',
  },
  {
    q: '「フォーマット」って？',
    a: '自分の投稿を削除するボタンです。フロッピーディスクを初期化するイメージで「フォーマット」と呼んでいます。削除できるのは自分の投稿だけです。',
  },
  {
    q: 'ディスク（コミュニティ）って？',
    a: '1 枚のフロッピーに見立てたコミュニティです。「レトロPC」「ドット絵」など、同じ趣味の書き込みを 1 枚に集めます。/disks から一覧・検索・作成ができ、ディスクを開いて「参加する」と専用の投稿フォームが使えます。書き込みにはログインと参加が必要です。',
  },
  {
    q: '共有ボタンは？',
    a: '各投稿の「共有」を押すと、投稿のプレビューが開きます。X でポスト / LINE で送る / リンクをコピー / 端末の共有メニューから共有できます。共有リンクは投稿ごとのページ（/p/ID）を開きます。「埋め込み HTML」を開くと、ブログなどに貼り付けるコードもコピーできます。',
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
          <b>1,024 B</b>
          <span>32 × 32 PIXEL</span>
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
