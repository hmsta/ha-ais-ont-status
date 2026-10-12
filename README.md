# AIS ONT Status

Home Assistant custom integration for polling optical status from an AIS/Huawei ONT over the restricted Telnet menu.

Tested with:

- AIS / Huawei `HG8045B7N-52`
- Firmware `V5R024C10S128`
- Restricted Telnet menu with `Retrieve Optical RX/TX Power`

The integration only reads menu option `3` for optical RX/TX power. It does not modify PLOAM settings or retrieve PLOAM passwords. During reconfiguration it can optionally use a freshly copied modem web session cookie once to re-enable LAN Telnet after a modem reboot.

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

## Re-enable LAN Telnet

Some ONTs disable Telnet again after a reboot. The integration reconfigure form has an optional advanced field named `Temporary modem web Cookie header` for this case.

Flow:

1. Log in to the modem web UI and solve the CAPTCHA.
2. Open browser developer tools and copy a fresh request `Cookie` header from the modem page.
3. In Home Assistant, open the AIS ONT Status integration and select reconfigure.
4. Paste the cookie into `Temporary modem web Cookie header`.
5. Submit the form.

When the field is provided, the integration:

1. Fetches `/html/bbsp/acl/aclsmart.asp` with the temporary cookie.
2. Extracts the hidden `hwonttoken` value.
3. Posts `TELNETLanEnable=1`, `TELNETWifiEnable=0`, and `HTTPWifiEnable=1`.
4. Verifies that Telnet works with the configured Telnet credentials.
5. Discards the cookie without saving it to the Home Assistant config entry.

The modem web session expires quickly. If reconfigure reports that the web session was rejected, log in to the modem again and paste a fresh cookie. The manual DevTools command remains the fallback if the modem rejects cookie reuse from the Home Assistant host.

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

If RX power is below the threshold, `Fiber link` turns off. If RX/TX power cannot be read, `Fiber link` and the power sensors become unavailable. `Modem reachable` shows whether the modem answers the lightweight TCP probe. `Telnet` shows whether the Telnet login and restricted menu are usable.

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

Optical values unavailable after Telnet login:
modem_reachable = on
telnet = on
fiber_link = unavailable

Telnet disabled, auth failure, or wrong menu:
modem_reachable = on
telnet = off
fiber_link = unavailable

Modem down or LAN path broken:
modem_reachable = off
telnet = unavailable
fiber_link = unavailable
```
