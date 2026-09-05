# Home Assistant — Dino Media Player

<p align="center">
  <img src="logo.svg" width="160" height="160" alt="Green Sinclair-style dinosaur on light gray">
</p>

Custom integration that exposes the outdoor Raspberry Pi player as a **device** in Home Assistant. Motion on the Sinclair dino (Wyze / YoLink) can set volume and start a clip; the Pi does the actual playback.

Companion service: [dino-media-player](https://github.com/rbridal/dino-media-player).

HACS custom repo. Current integration version: **2.6.0**.

## Credits

**THE SHOP / rbridal** specified the product: a real HA device, HACS from day one, motion-triggered yard audio, volume and output in the UI, and an automation that is just “set volume, pick the file.” They ran every test against live hardware.

**Grok** implemented the integration (config flow, device, entities, MQTT hub, availability/heartbeat, branding) and kept the HA contract aligned with the Pi player as the yard setup evolved.

## Logo

Green Sinclair-style sauropod on a solid light gray background.

Home Assistant serves brand images as PNG from:

`custom_components/dino_media_player/brand/`

- `icon.png` / `icon@2x.png`
- `dark_icon.png` / `dark_icon@2x.png`
- `logo.png` / `logo@2x.png`
- `dark_logo.png` / `dark_logo@2x.png`

SVGs (`logo.svg`, `brand/icon.svg`) are for GitHub only.

## Device entities

| Entity | Purpose |
| --- | --- |
| Availability | On when MQTT says online **and** a heartbeat arrived in the last 45 s. When off, the other entities go unavailable. |
| Last heartbeat | Timestamp of the last Pi heartbeat (noisy in Activity — safe to disable). |
| Media | Select. Idle option is `none`. Choosing a file **plays it**. Choosing `none` stops. |
| Output | `3.5mm jack` or `BT-WUZHI` |
| Volume | Number 0–100 |
| Playback state | `playing` / `stopped` |
| Current media | Filename while playing |
| Position / Duration | Seconds |
| Bluetooth connected | On when A2DP to BT-WUZHI is up |
| Bluetooth status | `connected` / `disconnected` / `reconnecting` / `not_required` |
| Stop | Stop playback |
| Reconnect Bluetooth | Force `bluetoothctl connect` |

There is no Play button and no `media_player` entity. Play is “select the file.”

## Alerts (built in)

Settings → Devices & Services → Dino Media Player → **Configure**:

- **Notify when offline or Bluetooth is down**
- **Minutes before notify** — default 5
- **Notifier** — dropdown of every `notify.*` service, including groups such as Rob’s iPhone

The same notifier and delay apply to both conditions:

1. The player stays unavailable.
2. Output is Bluetooth (`BT-WUZHI`) and the amp stays disconnected. This does not fire while the player itself is offline, or when the 3.5mm jack is selected.

Reminders repeat every 30 minutes until the condition clears. A recovery message uses the same iOS notification tag so the banner replaces itself.

## Install (HACS)

1. HACS → Integrations → Custom repositories
2. Add `https://github.com/rbridal/ha-dino-media-player` as **Integration**
3. Download, restart Home Assistant
4. Settings → Devices & Services → Add Integration → **Dino Media Player**
5. Device name and MQTT topic prefix (`dino/player` unless you changed the Pi)

Reconfigure later from the integration → Configure. Requires the MQTT integration and a reachable broker.

## Automation example

```yaml
alias: Dino motion — play theme
triggers:
  - trigger: state
    entity_id: binary_sensor.YOUR_MOTION
    to: "on"
actions:
  - action: number.set_value
    target:
      entity_id: number.dino_media_player_volume
    data:
      value: 75
  - action: select.select_option
    target:
      entity_id: select.dino_media_player_media
    data:
      option: dino_theme.wav
```

Entity IDs follow the device name you enter in the GUI. Stop with Stop, or set Media to `none`.

## License

MIT
