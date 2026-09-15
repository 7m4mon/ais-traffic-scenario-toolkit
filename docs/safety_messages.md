# AIS短文メッセージをシナリオに追加する

通常の合成シナリオJSONの最上位に `messages` 配列を追加します。
`time_sec` はシナリオ開始からの秒数で、小数も指定できます。
位置更新の `time_step_sec` と一致しなくても、その時刻に1回出力します。

```json
"messages": [
  {"time_sec": 10, "message_type": 14, "mmsi": 999510101,
   "text": "TEST - CAUTION CROSSING TRAFFIC"},
  {"time_sec": 30, "message_type": 12, "mmsi": 999510101,
   "destination_mmsi": 999510000, "text": "TEST - KEEP CLEAR"}
]
```

- `mmsi` は送信元。位置報告とは独立したイベントです。
- Message 14 は一斉通知。省略時も14です。
- Message 12 は個別宛て。`destination_mmsi` に受信機の自船MMSIを指定してください。
  `sequence_number` は0～3で省略時0です。受信確認（Message 13）や自動再送は実装していません。
- 本文はAISの6ビット文字集合（英数字・対応記号）。小文字は大文字になります。
  日本語・改行など非対応文字や長すぎる本文はエラーになります。
  上限はMessage 12が156文字、14が161文字です。これは最大形式長で、局種別の無線スロット制限を模擬するものではありません。
- 長文は複数のAIVDM文に分割して出力します。ビット列出力は1メッセージにつき1本です。
- Message 12/14の末尾は0ビットで8ビット境界にそろえてからAIVDM化します。
  本文を4文字単位に変更する必要はありません。AIVDMの6ビット文字化に使うfill bitsとは別の処理です。
  根拠：ITU-R M.1371-6 Annex 2 A2-3.3.7（Message structure）。
- 通常の混合NMEA出力・AIS専用出力に流れます。自船GPS専用出力には流れません。
- ポップアップ・警報音・個別宛てメッセージの表示可否は受信機の対応と設定に依存します。
  このツールから表示や音を強制することはできません。

## サンプル

プロジェクトフォルダーで実行します。

```powershell
python tools/ais_scenario_compile.py --scenario scenarios/safety_messages_demo.json --output timeline/safety_messages_demo.jsonl --csv timeline/safety_messages_demo.csv
python tools/ais_scenario_player.py --timeline timeline/safety_messages_demo.jsonl --nmea-tcp-server 127.0.0.1:10110 --echo-output
```

10秒に一斉通知、30秒に自船宛て、50秒に終了通知を出します。
既存の合成シナリオにも同じ配列を追加できます。
専用ビルダーを使う事故再現シナリオは、この配列を自動では取り込みません。

形式の根拠：USCG [Message 12](https://www.navcen.uscg.gov/ais-addressed-safety-related-message12)、
[Message 14](https://www.navcen.uscg.gov/ais-safety-related-broadcast-message14)。

## exhibition_gauntlet

自船MMSIと個別通知の宛先は仮番号 `999510000` です。実機で個別通知を試す場合は、ローカルで受信機の自船MMSIに合わせてください。
4件とも単一AIVDM文で出力します。8ビット境界への補完後のデータ長は、
順に232・288・248・96ビットです。本文と送信時刻はそのままです。

| 開始から | 種別 | 送信元 | 本文 |
|---|---|---|---|
| 00:30 | 14・一斉 | CROSSING EXPRESS | TEST - CAUTION CROSSING TRAFFIC |
| 04:00 | 12・自船宛て | HEAD ON TRADER | TEST - HEAD ON APPROACH. KEEP CLEAR. |
| 05:05 | 14・一斉 | HEAD ON TRADER | TEST - CAUTION VIRTUAL WRECK AHEAD |
| 06:55 | 14・一斉 | AIS SART TEST | SART TEST |

```powershell
python tools/ais_scenario_compile.py --scenario scenarios/exhibition_gauntlet.json --output timeline/exhibition_gauntlet.jsonl --csv timeline/exhibition_gauntlet.csv
python tools/ais_scenario_player.py --timeline timeline/exhibition_gauntlet.jsonl --nmea-tcp-server 127.0.0.1:10110 --echo-output
```
