# AIS ONT Status

Home Assistant custom integration for polling optical status from an AIS/Huawei ONT over the restricted Telnet menu.

Tested with:

- AIS / Huawei `HG8045B7N-52`
- Firmware `V5R024C10S128`
- Restricted Telnet menu with `Retrieve Optical RX/TX Power`

The integration only reads menu option `3` for optical RX/TX power. It does not modify PLOAM settings, retrieve PLOAM passwords, enable Telnet, or use the web UI.

## Entities

- `binary_sensor.<device>_fiber_link`
- `binary_sensor.<device>_modem_reachable`
- `binary_sensor.<device>_telnet`
- `sensor.<device>_rx_power`
- `sensor.<device>_tx_power`
- `sensor.<device>_poll_duration`

`Fiber link` is on when RX optical power is present and above the configured threshold. It is off only when RX power is successfully read and below the threshold. If the ONT cannot be reached or RX/TX power cannot be parsed, the fiber link entity is unavailable. The default threshold is `-30 dBm`.

## Installation

### HACS Custom Repository

1. Open HACS.
2. Open the three-dot menu.
3. Select `Custom repositories`.
4. Add:

   ```text
   https://github.com/hmsta/ha-ais-ont-status
   ```

5. Select category `Integration`.
6. Install `AIS ONT Status`.
7. Restart Home Assistant.

### Manual

Copy `custom_components/ais_ont_status` into your Home Assistant `custom_components` directory and restart Home Assistant.

## Configuration

Add the integration from Home Assistant:

```text
Settings -> Devices & services -> Add integration -> AIS ONT Status
```

Fields:

- Host, usually `192.168.1.1`
- Telnet port, usually `23`
- Telnet username
- Telnet password
- Scan interval, default `30` seconds
- Timeout, default `10` seconds
- Minimum OK RX power, default `-30 dBm`
- Modem reachability TCP port, default `80`

Telnet must already be enabled on the ONT and should be restricted to LAN only.

## Security Notes

Telnet is plaintext. Keep it LAN-only and do not enable Telnet over Wi-Fi or WAN.

Do not use the ONT menu option to modify the PLOAM password unless AIS explicitly instructs you to. Changing the PLOAM password can prevent the ONT from registering on the fiber network.

Do not commit real Telnet credentials, PLOAM passwords, or Home Assistant config entries to GitHub.

## Behavior

Every scan interval the integration:

1. Checks modem reachability using a TCP connect to the configured reachability port.
2. Opens a Telnet connection.
3. Logs in with the configured credentials.
4. Selects menu option `3`.
5. Parses `RxPower` and `TxPower`.
6. Logs out/closes the connection.

If RX power is below the threshold, `Fiber link` turns off. If RX/TX power cannot be read, `Fiber link` and the power sensors become unavailable. `Modem reachable` shows whether the modem answers the lightweight TCP probe. `Telnet` shows whether the Telnet status path works end to end.

Typical states:

```text
Normal:
modem_reachable = on
telnet = on
fiber_link = on

Known optical problem:
modem_reachable = on
telnet = on
fiber_link = off

Telnet disabled, wrong menu, or parser failure:
modem_reachable = on
telnet = off
fiber_link = unavailable

Modem down or LAN path broken:
modem_reachable = off
telnet = unavailable
fiber_link = unavailable
```
