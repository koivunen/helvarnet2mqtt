# helvar2mqtt

**WORK IN PROGRESS:** *Awaiting time to test demo in https://aistikattila.fi/* 

Bridge between Helvar lighting systems and MQTT specifically for input logging and interactivity bypassing Helvar scene based modes. 
Polls device inputs and publishes state changes to MQTT, while also accepting load level commands via MQTT.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- A Helvar router accessible over the network
- An MQTT broker


## Configuration

Copy `.env.example` to `.env` and adjust:

## Usage

### Normal operation

Starts polling device inputs and publishing changes to MQTT. Listens for load commands.

```bash
uv run python main.py
```

### Dump devices

Exports all discovered devices to `devices.json`:

```bash
uv run python main.py --dump-devices-on-start
```

The output includes address, name, etc...

## MQTT

### State changes (published)

Topic: `helvar/device/<address>/input`

Payload:
```json
{
  "device": "Sensor Name",
  "address": "@0.1.1.14",
  "new_state": "[True, False, False]",
  "old_state": "[False, False, False]",
  "timestamp": "2026-05-05T21:00:00+00:00"
}
```

### Load level (subscribed)

Topic: `helvar/device/<address>/load/command`

Payload:
```json
{
  "level": 100,
  "fade_time": 100
}
```

- `level`: 0–100 (float)
- `fade_time`: milliseconds to transition (int, default 100)

## Architecture

- Uses `aiomqtt` for fully async MQTT communication
- Uses `asyncio.TaskGroup` for structured concurrency (polling loop + command handler run concurrently)
- Uses `aiodebug` to log slow callbacks (>100ms) for debugging
- Device polling distributes evenly across the poll interval to avoid burst requests

## Disclaimer

*Helvar™ is a registered trademark of Helvar Ltd.*

> [!CAUTION]
> This software is an unofficial project by a third party and not supported by Helvar Ltd. in any capacity. 
> The use of the Helvar™ name is only for identifying compatibility with Helvar routers, which this project is solely being used for.
>
>Polling happens every `POLL_INTERVAL` seconds for every device with inputs. This may slow down the router or cause unwanted side effects in large installations.

*This project was generated with the help of [OpenCode](https://github.com/anomalyco/opencode), an AI-powered coding assistant. Use at your own risk. Review all code before deploying to any production or critical lighting system. Improper use could affect lighting installations.*

## License

Apache

## Acknowledgements

_We gratefully acknowledge the [Flavoria® Multidisciplinary Research Platform](https://www.flavoria.fi/en/) for letting us explore HelvarNet with the Aistikattila's lighting system. Special thanks also goes to [AleksiPapalitsas](https://github.com/AleksiPapalitsas) for helping with the aiohelvar integration of Aistikattila._
