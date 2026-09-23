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
    q: '埋め込みプレビューは？',
    a: '各投稿の「埋め込み」を押すと、外部サイトに貼り付けられる HTML スニペットが表示されます。これはプレビュー API（/api/preview.php）が生成しています。',
  },
]
</script>

<template>
  <div>
    <section class="panel">
      <h2 class="panel-title">floppy.io の使い方</h2>
      <p class="panel-note">
        1 投稿＝フロッピー 1 枚。容量と相談しながら書いてください。
      </p>
    </section>

    <section class="panel">
      <h2 class="panel-title">よくある質問</h2>

      <dl class="faq">
        <template v-for="item in faqs" :key="item.q">
          <dt>{{ item.q }}</dt>
          <dd>{{ item.a }}</dd>
        </template>
      </dl>
    </section>

    <section class="panel">
      <h2 class="panel-title">アカウント</h2>
      <ul class="help-list">
        <li>ユーザー名は半角英数字とアンダースコア（_）の 3〜20 文字です。</li>
        <li>パスワードは 6 文字以上。ハッシュ化して保存されます。</li>
        <li>表示名と bio は <a href="#/settings">設定</a> から変更できます。</li>
        <li>ログアウトは <a href="#/settings">設定</a> から行えます。</li>
      </ul>
    </section>
  </div>
</template>
