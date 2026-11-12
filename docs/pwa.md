# PWA

`frontend` は PWA としてインストールできます。Android / PC の Chrome・Edge は
ブラウザのインストールメニュー、iPhone / iPad の Safari は共有メニューの
「ホーム画面に追加」を使用してください。HTTPS（ローカル確認は localhost）が必要です。

## ビルド

```sh
cd frontend
npm run build          # / に配信
npm run build:subdir   # /floppy.io/ に配信
```

`npm run generate` も `.output/public/sw.js` を生成します。
`nuxt generate` の直接実行では Service Worker の生成処理が走らないため、npm のスクリプトを使ってください。
開発用の `npm run dev` では Service Worker を登録しません。

## オフラインと更新

- オンラインで一度起動すると、オフライン案内ページを保存します。
- オフラインで開いたページは案内を表示し、「もう一度読み込む」で同じ URL を再試行できます。
- 投稿の閲覧・送信はオンライン専用です。API・認証情報・投稿・添付ファイルは Service Worker に保存しません。送信の自動再試行も行いません。
- 更新された Service Worker は、既存のアプリウィンドウとタブをすべて閉じてから有効になります。編集中のページを強制再読み込みしません。
- 公開ゲートウェイと Apache 設定は `sw.js`、マニフェスト、オフラインページを再検証させます。別の配信環境でもこれらを長期キャッシュしないよう設定してください。

## 確認

ビルドを配信し、Chrome DevTools の Application で Manifest と Service Workers を確認します。
Service Worker の有効化後、Network を Offline にして投稿ページなどを再読み込みすると案内が表示されます。
Online に戻して「もう一度読み込む」を押すと元のページに戻ります。
Cache Storage に保存されるのは `offline.html` だけです。
