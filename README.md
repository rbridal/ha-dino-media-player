# Home Assistant - Dino Media Player

Custom integration that creates a `media_player` entity for the outdoor Dino media player running on a Raspberry Pi.

Controlled via MQTT. Designed to work with the companion repo: [dino-media-player](https://github.com/rbridal/dino-media-player).

## Features
- Full `media_player` entity
- Play / Pause / Resume / Stop
- Source selector (lists available media files from the Pi)
- Works over ZeroTier / Nabu Casa
- HACS custom repository ready from day one

## Installation (HACS)

1. HACS → Integrations → Custom repositories
2. Add repository: `https://github.com/rbridal/ha-dino-media-player`
3. Category: Integration
4. Download / Install
5. Restart Home Assistant
6. Settings → Devices & Services → Add Integration → search for **Dino Media Player**

## Configuration

You will be asked for:
- MQTT topic prefix (default: `dino/player`)
- Friendly name (default: `Dino Media Player`)

## MQTT Topics expected from the Pi

The Pi service must publish:
- `dino/player/state` → `playing` | `paused` | `stopped` | `idle`
- `dino/player/source` → current filename
- `dino/player/sources` → JSON array of available filenames
- `dino/player/available` → `online` | `offline`

And accept commands on:
- `dino/player/command` with JSON payload

## Automation Example

```yaml
automation:
  - alias: "Dino Motion - Play Theme"
    trigger:
      - platform: state
        entity_id: binary_sensor.wyze_cam_duo_motion  # adjust to your entity
        to: "on"
    action:
      - service: media_player.play_media
        target:
          entity_id: media_player.dino_media_player
        data:
          media_content_id: "jurassic_park_theme.mp3"
          media_content_type: "music"
      # or simply:
      # - service: media_player.media_play
      #   target:
      #     entity_id: media_player.dino_media_player
```

## License
MIT
