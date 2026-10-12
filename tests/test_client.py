"""Tests for AIS ONT Telnet parsing."""

import asyncio
from importlib import util
from pathlib import Path
import sys

CLIENT_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "ais_ont_status"
    / "client.py"
)
SPEC = util.spec_from_file_location("ais_ont_status_client", CLIENT_PATH)
assert SPEC is not None
client = util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = client
SPEC.loader.exec_module(client)


def test_parse_optical_power() -> None:
    """Parse the observed restricted menu output."""
    output = """
    RxPower = -23.01 dbm
    TxPower = 2.24  dbm
    """

    assert client.parse_optical_power(output) == (-23.01, 2.24)


def test_parse_optical_power_raises_for_missing_values() -> None:
    """Reject output without both RX and TX power."""
    try:
        client.parse_optical_power("No optical data")
    except client.UnexpectedResponse:
        return

    raise AssertionError("Expected UnexpectedResponse")


def test_extract_hwonttoken() -> None:
    """Extract the ACL token from the modem web form."""
    html = """
    <input type="hidden" name="x.X_HW_Token" id="hwonttoken" value="abc123">
    """

    assert client.extract_hwonttoken(html) == "abc123"


def test_normalize_cookie_header() -> None:
    """Accept either a raw header value or a copied Cookie header line."""
    raw = "body:Language:english:id=-1; CookieHttp=sid=abc"

    assert client.normalize_cookie_header(raw) == raw
    assert client.normalize_cookie_header(f"Cookie: {raw}") == raw


def test_status_fields_for_modem_unreachable() -> None:
    """Document the unavailable modem state model."""
    status = client.AisOntStatus(
        modem_reachable=False,
        telnet_ok=None,
        authenticated=False,
        optical_signal_ok=False,
        rx_power_dbm=None,
        tx_power_dbm=None,
        poll_duration_ms=10000,
        checked_at=client.datetime.now(client.timezone.utc),
        error="Modem is not reachable",
    )

    assert status.modem_reachable is False
    assert status.telnet_ok is None
    assert status.rx_power_dbm is None


def test_telnet_stays_on_when_optical_power_is_unavailable() -> None:
    """A working Telnet menu is separate from readable optical values."""

    class Client(client.AisOntTelnetClient):
        async def _async_check_modem_reachable(self) -> bool:
            return True

        async def _async_read_optical_power(self) -> tuple[float, float]:
            raise client.OpticalPowerUnavailable("Could not parse optical RX/TX power")

    status = asyncio.run(
        Client(
            host="192.168.1.1",
            port=23,
            username="root",
            password="admin",
            timeout=10,
            rx_power_min_dbm=-30.0,
            modem_reachability_port=80,
        ).async_get_status()
    )

    assert status.modem_reachable is True
    assert status.telnet_ok is True
    assert status.authenticated is True
    assert status.rx_power_dbm is None
    assert status.tx_power_dbm is None
