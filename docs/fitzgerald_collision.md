# Fitzgerald / ACX Crystal 衝突・記録航跡の再生

**2017年6月17日 01:15:12〜01:30:34 JST、15分22秒。**
自船は USS FITZGERALD、相手船は ACX CRYSTAL、WAN HAI 266、MAERSK EVORA。
日本の運輸安全委員会（JTSB）の公開AIS／ARPA記録表を基にした、衝突に至る接近の再生。
船体の衝突、損傷、衝突後の運動を計算するシミュレーターではない。

## 再生する

プロジェクトのルートで実行する。生成済みJSONLを同梱しているので、ビルドなしでも再生できる。

```powershell
python .\tools\ais_scenario_player.py --timeline .\timeline\fitzgerald_collision.jsonl --nmea-tcp-server 127.0.0.1:10110 --replay-speed 5
```

OpenCPNの入力接続をTCP `127.0.0.1:10110`に設定してからプレイヤーを起動する。
5倍速なら約3分4秒。接続待ちで時計は止まらないため、途中接続になった場合はプレイヤーを再起動する。
表示範囲の目安は北緯34.44〜34.62度、東経138.97〜139.12度。
自船にはRMC/GGA/HDT、他船にはAIS位置・船名情報を出力する。
NMEAの日付時刻は再生開始時の現在時刻。事故の日本時間はイベントCSVとプレビューで確認する。

`timeline/fitzgerald_collision_preview.html` をブラウザーで開くと、再生・一時停止・時刻スライダーで航跡を確認できる。
外部ライブラリーやネット接続は不要。図は等縮尺の局所座標であり、海図や海岸線は表示しない。

## 再生成する

```powershell
python .\tools\build_fitzgerald.py
```

入力は `scenarios/fitzgerald_collision.json`。原表の度分秒、対地速力、対地針路、船首方位、出典を保存する。
**この入力は `observed_tracks/1` 形式で、通常の `ais_scenario_compile.py` の入力形式とは異なる。**
記録位置と対地針路・船首方位を独立して保持するため、専用ビルダーから既存プレイヤー互換のJSONL/CSVへ変換する。
既存の合成シナリオやコンパイラーは変更していない。

生成物：

- `timeline/fitzgerald_collision.jsonl`：1秒刻み、923時刻、合計3,065レコード。
- `timeline/fitzgerald_collision.csv`：同じデータの表形式。
- `timeline/fitzgerald_collision_events.csv`：日本時間・相対秒・出来事・出典。
- `timeline/fitzgerald_collision_preview.html`：同じ1秒データを使った航跡プレビュー。

## 資料と採用範囲

主資料は[JTSB訂正版報告書](https://jtsb.mlit.go.jp/ship/rep-acci/2019/MA2019-8-1_2017tk0009.pdf)（2019年9月26日の正誤表反映版）。
表のページ番号はPDF通し番号ではなく本文の印刷ページ。入力には再生範囲を挟む点も含む。

| 船 | 資料 | 入力点数 | 位置の性質 |
|---|---|---:|---|
| ACX CRYSTAL（A船） | 表1、p.3 | 23 | AISのGPSアンテナ位置 |
| USS FITZGERALD（B船） | 表2、p.4 | 26 | D船のARPAが追跡したレーダー反射位置 |
| WAN HAI 266（D船） | 表4、pp.6–7 | 17 | AISのGPSアンテナ位置 |
| MAERSK EVORA（E船） | 表5、p.7 | 7 | AISのGPSアンテナ位置 |

D/E船の名前は[NTSB MAR-20/02](https://www.ntsb.gov/investigations/AccidentReports/Reports/MAR2002.pdf)の図7と照合した。
JTSB表6（p.8）の信号灯関連音・舵角表示・衝撃音をイベントに採用した。
NTSBの変針指令は注記だけに使用し、JTSBの位置をその指令に合わせて変形していない。
NTSB図7・10の再構成航跡とJTSBの原表は同じ精度・処理のデータではない。

事故時刻はJTSBの **01:30:34** を終端とする。NTSB本文は **01:30:32**。
両方をイベントに記載し、個別機器の時計を2秒ずらすような同期操作は行わない。
地図基準点はJTSBの事故概位、北緯34°31.3′・東経139°04.3′。

## 補間と限界

1. 記録点そのものの緯度経度を保持し、間の位置を線形補間する。COG/SOG/船首方位は別に補間する。
   方位は0°をまたぐ最短方向で補間する。位置差から得る速度と、記録SOG/COGは必ずしも一致しない。
   特にARPAにはばらつきがあり、位置の逆行や速力変化を「実際の操船」と解釈しない。
2. Fitzgeraldの船首方位は表にないため、表示・HDTにCOGを代用する。`source` に `heading_proxy` を付ける。
   ACXではCOGと船首方位を区別するため、旋回中は船の向きと移動方向が異なる。
3. 当事船2隻の最後の衝突前記録は01:30:27。以後7秒はそのCOG/SOGで外挿し、`source` に `extrapolated` を付ける。
   事故後の点を使って衝突前を補間しない。最後の左転・加速、ACXの旋回の継続は正確に復元できない。
4. **終端の当事船の表示基準点間距離は約304m。** GPSアンテナとレーダー反射位置という基準点の違いに加え、
   追跡誤差・時刻差・補間／外挿の影響が含まれうる。304m全部をアンテナ位置の違いで説明したとはしていない。
   この値は船体間の空き距離ではなく、「衝突しなかった」という意味でもない。点を一致させる補正はしていない。
5. Maersk Evoraは01:25:39（相対627秒）に公開データが始まるため、その時刻から出力する。
   その時刻に海域へ到着したという意味ではない。記録のない前10分間の航跡は作らない。
   それ以外の船や、期間外の記録しかないC船は省略した。
6. CPA/TCPAは記録のCOG/SOGを用いた等速直線予測。既存の警報閾値を使用し、当時の装置表示・乗員の認識を再現しない。
   船体形状の判定や自動回避はない。イベントの舵角15°を針路15°として入力することもない。
7. MMSIは `999170601`〜`999170604` の仮想値、AISは再生用Class B形式。当時の受信電文の復元ではない。
   Fitzgeraldは自船NMEAであり、当時AISを送信していたという表現にはしていない。

## 確認

```powershell
python -m pytest -q
python .\tools\ais_scenario_player.py --timeline .\timeline\fitzgerald_collision.jsonl --dry-run --replay-speed 10000 > $null
```

記録点保持、記録範囲・外挿上限、船首方位の区別、船の出現時刻、CPA、NMEA/AIS出力を検証する。
これらはデータ処理の整合性の検査であり、実船の運動を秒単位で正確に復元できたことの証明ではない。
