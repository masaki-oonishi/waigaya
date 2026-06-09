# MoJiMoJi 育成ノート アプリケーション

階層型記憶システム（短期・中期・長期メモリ）を搭載した、LINE風UIの生徒伴走型育成AIチャットアプリです。

## 📁 フォルダ構成の準備
解凍後、アプリを動かす前に以下の通りにLottie用のアニメーションJSONを配置してください。

mojimoji_app/
  ├── app.py
  ├── services.py
  ├── models.py
  ├── requirements.txt
  ├── .env
  └── resource/
        ├── egg.json         (レベル5までの卵のアニメーション)
        └── mojimoji.json    (レベル10以降のキャラクターアニメーション)

## 🚀 起動方法
1. 必要ライブラリのインストール:
   pip install -r requirements.txt

2. .env ファイルを開き、ご自身の GEMINI_API_KEY を設定します。

3. アプリケーションの起動:
   streamlit run app.py
