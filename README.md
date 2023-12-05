# advent-2023-cloudrun-websocket-app
author: onumasho@google.com

Google Cloud Advent Calendar 2023 の記事で利用するリポジトリです。

本リポジトリをデプロイすることで、簡易なかるたアプリケーションを試すことが出来ます。

## ローカルでの動作確認

仮想環境の作成
```
python3 -m venv py3
source py3/bin/activate
```

依存ライブラリのインストール
```
pip install -r requirements.txt
```

サーバの起動
```
chmod +x run.sh
./run.sh
```

ブラウザから http://localhost:8080 にアクセスします。

## 利用方法

ユーザIDを入力します。
![](https://github.com/shonuma/advent-2023-cloudrun-websocket-app/blob/bb29344a56a8d040bcd3ef26859e0edc3062256b/docs/00_entrance.png)

入室すると以下の画面になります。
![](https://github.com/shonuma/advent-2023-cloudrun-websocket-app/blob/bb29344a56a8d040bcd3ef26859e0edc3062256b/docs/01_room.png)

動作確認のため、二画面を開いておきましょう。
![](https://github.com/shonuma/advent-2023-cloudrun-websocket-app/blob/bb29344a56a8d040bcd3ef26859e0edc3062256b/docs/02_user_and_guest.png)

「出題側」が「かるたゲームを始める」ボタンを押すと、ゲームが開始されます。

「出題側」はアイコンから任意の Google Cloud サービスを選択します。

「回答側」は画面上部に表示される説明文に該当する Google Cloud サービスを選択する、という流れです。
![](https://github.com/shonuma/advent-2023-cloudrun-websocket-app/blob/bb29344a56a8d040bcd3ef26859e0edc3062256b/docs/output.gif)
