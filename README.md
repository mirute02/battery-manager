# battery-manager

**日本語** | [English](README.en.md)

**TP-Link Tapo P110M** スマートプラグのON/OFFで、ノートPCのバッテリー残量を一定の範囲に保つ。

リチウムイオン電池は100%付近に長く留まるほど劣化が進む。ファームウェアに充電上限の設定があるPCならBIOSで抑えられるが、無い機種も多い（LinuxをインストールしたMacはその代表）。このスクリプトはその隙間を反対側から埋める。電池側の制御ではなく、**壁のコンセントで給電そのものを止める**。

```
battery >= battery_max  →  プラグ OFF（放電）
battery <= battery_min  →  プラグ ON （充電）
それ以外                →  何もしない
```

スクリプトは状態を持たない。実行のたびに現在の残量を読んで判断するので、定期実行しても、途中で止めても安全。

## 動作条件

- `/sys/class/power_supply/BAT*` のある Linux（`capacity` が読めない場合は `upower` にフォールバック）
- **Python 3.11 以上**（`tapo` ライブラリの要件）
- LAN 内から到達できる Tapo P110M / P110 / P115
- [`tapo`](https://github.com/mihai-dinculescu/tapo) 0.8.8 以上（MIT）— 唯一のサードパーティ依存

## セットアップ

```bash
git clone https://github.com/mirute02/battery-manager.git
cd battery-manager
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

mkdir -p ~/.config/battery-manager
cp config.example.json ~/.config/battery-manager/config.json
chmod 600 ~/.config/battery-manager/config.json
$EDITOR ~/.config/battery-manager/config.json
```

## 設定

`~/.config/battery-manager/config.json` — **リポジトリの外**に置くので、認証情報がコミットされることはない（万一チェックアウト内にコピーしても `.gitignore` の `config.json` で弾かれる）。

| キー | 必須 | 既定値 | 意味 |
|---|---|---|---|
| `tapo_email` | ✅ | — | Tapo アカウントのメールアドレス |
| `tapo_password` | ✅ | — | Tapo アカウントのパスワード |
| `device_ip` | ✅ | — | プラグの LAN アドレス（DHCP で固定しておく） |
| `battery_max` | | `80` | この%以上で給電を止める |
| `battery_min` | | `40` | この%以下で給電を再開する |
| `battery_name` | | `BAT0` | `/sys/class/power_supply` 配下のディレクトリ名 |

`device_ip` は**プライベートアドレスのリテラル**でなければならない。ホスト名や公開アドレスは拒否するので、打ち間違いで Tapo の認証情報が外部へ送られることはない。[docs/security.md](docs/security.md) を参照。

バッテリー名は `ls /sys/class/power_supply/` で確認できる。`BAT1` の機種もある。

設定ファイルが無い、値が `YOUR_…` のまま、必須キーが欠けている、閾値が整数でない、`battery_name` が空でない文字列でない、`0 < battery_min < battery_max <= 100` を満たさない — いずれの場合も**プラグに触れる前に**終了する。

## 実行

```bash
.venv/bin/python battery-manager.py
# Battery: 75% | Status: Full | Plug: unchanged
```

### 定期実行

`~/.config/systemd/user/battery-manager.service`

```ini
[Unit]
Description=Battery charge manager

[Service]
Type=oneshot
ExecStart=%h/battery-manager/.venv/bin/python %h/battery-manager/battery-manager.py
```

`~/.config/systemd/user/battery-manager.timer`

```ini
[Unit]
Description=Run battery-manager every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now battery-manager.timer
```

## 設計上の判断

**失敗したら止まる。** 残量が読めなければ、プラグに接続する前に非ゼロ終了する。以前の版は失敗時に `-1` を返しており、これが「下限以下」と判定されて充電を**ON**にしてしまっていた。`BAT0` が存在しない機種では最悪の動作になる。

**認証情報はリポジトリに入れない。** Tapo アカウントのパスワードは本物の認証情報なので、`~/.config/battery-manager/config.json` にだけ置く。パーミッションは `600` にすること。

**プラグは充電コントローラではない。** 給電を切れば充電は止まるが、その後PCはバッテリーで動く。`battery_min` を低くしすぎると深い放電サイクルを繰り返すことになる。既定の 40/80 はそれを避ける値。

**残量が範囲内ならプラグに接続しない。** `battery_min` と `battery_max` の間にあるときは、プラグへ接続せずそのまま終了する。定期実行の大半はこのパスを通るため、プラグが一時的にオフラインでも無用な失敗を出さない。

**自分のネットワークとしか通信しない。** `device_ip` はプライベートアドレスのリテラルに限定し、ホスト名は拒否する。DNS を信頼の経路に入れないため。

**操作する相手を確かめる。** `on`/`off` を送る前に機種を問い合わせ、P110 / P110M / P115 以外なら何もしない。`device_ip` を打ち間違えて電球や別のプラグに当たっても動かさない。

**接続はタイムアウトする。** 操作が必要でプラグに接続する場合、`tapo` クライアントは30秒で諦める。プラグがネットワークから消えていても、スケジューラが固まることはなく、その回がクリーンなエラーで失敗するだけで済む。

## テスト

```bash
pip install pytest
python -m pytest tests/ -q
```

34件。いずれもプラグにもネットワークにも接続しない。CI で Python 3.11〜3.13 上を通している。

## セキュリティ

[docs/security.md](docs/security.md) に、何が守られていて何が守られていないか（Tapo のパスワードは平文保存であり、それが最大の制約）、および意図的にやっていないことを書いてある。

## 関連プロジェクト

- [tvremocon](https://github.com/mirute02/tvremocon) — Tapo の赤外線ハブ経由でテレビを操作する Android ウィジェット。同じ LAN 完結の KLAP プロトコルを使う。

## ライセンス

MIT — [LICENSE](LICENSE) を参照。依存のライセンスは [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) に記載。

`tapo` は MIT ライセンス。Tapo は TP-Link の商標であり、本プロジェクトは TP-Link と無関係で、承認も受けていない。
