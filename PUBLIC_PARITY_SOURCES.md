# Public parity evidence

This harness validates the public Blynk hardware-client contract implemented by this clone. It does not claim to reproduce or inspect proprietary Blynk Cloud internals.

- [Blynk Arduino library](https://github.com/blynkkk/blynk-library) — official client implementation used by the firmware build; PlatformIO pins version 1.4.0.
- [Blynk legacy server protocol](https://github.com/blynkkk/blynk-server/blob/master/PROTOCOL.md) — public description of the hardware frame format and command families. The hardware frame uses a command byte, two-byte message ID, two-byte length/status field, and body; mobile and WebSocket framing are separate.
- [Wokwi CLI](https://docs.wokwi.com/wokwi-ci/cli-installation) — official CLI installation and CI execution guidance, including the `WOKWI_CLI_TOKEN` environment variable.
- [Wokwi ESP32 Wi-Fi guide](https://docs.wokwi.com/guides/esp32-wifi) — documents the `Wokwi-GUEST` network and simulated ESP32 networking.
- [Wokwi local-network access](https://docs.wokwi.com/guides/esp32-wifi#connecting-to-the-internet) — documents access from a simulation to host services, including the `host.wokwi.internal` hostname used by this harness with the Wokwi Private IoT Gateway.

The serial assertions prove that the simulated board joined Wi-Fi, completed Blynk hardware login, and issued a V2 virtual-pin write to this clone. They are client/protocol integration evidence, not evidence of compatibility with Blynk Cloud's private backend.
