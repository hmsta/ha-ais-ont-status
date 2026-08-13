"""Telnet client for the restricted AIS/Huawei ONT menu."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
import re
import time
from typing import Final

IAC: Final = 255
DONT: Final = 254
DO: Final = 253
WONT: Final = 252
WILL: Final = 251
SB: Final = 250
SE: Final = 240

RX_RE = re.compile(r"RxPower\s*=\s*([-+]?\d+(?:\.\d+)?)\s*d?bm", re.IGNORECASE)
TX_RE = re.compile(r"TxPower\s*=\s*([-+]?\d+(?:\.\d+)?)\s*d?bm", re.IGNORECASE)


class AisOntError(Exception):
    """Base AIS ONT error."""


class CannotConnect(AisOntError):
    """The ONT could not be reached."""


class InvalidAuth(AisOntError):
    """The ONT rejected the Telnet credentials."""


class UnexpectedResponse(AisOntError):
    """The ONT returned an unexpected Telnet menu response."""


@dataclass(slots=True, frozen=True)
class AisOntStatus:
    """Current ONT optical status."""

    modem_reachable: bool
    telnet_ok: bool | None
    authenticated: bool
    optical_signal_ok: bool
    rx_power_dbm: float | None
    tx_power_dbm: float | None
    poll_duration_ms: int | None
    checked_at: datetime
    error: str | None = None


def parse_optical_power(output: str) -> tuple[float, float]:
    """Parse RX/TX optical power from the restricted Telnet menu output."""
    rx_match = RX_RE.search(output)
    tx_match = TX_RE.search(output)
    if rx_match is None or tx_match is None:
        raise UnexpectedResponse("Could not parse optical RX/TX power")
    return float(rx_match.group(1)), float(tx_match.group(1))


class AisOntTelnetClient:
    """Client for reading optical power from the ONT Telnet menu."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: int,
        rx_power_min_dbm: float,
        modem_reachability_port: int,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.rx_power_min_dbm = rx_power_min_dbm
        self.modem_reachability_port = modem_reachability_port

    async def async_get_status(self) -> AisOntStatus:
        """Connect to the ONT and read optical RX/TX power."""
        started = time.monotonic()
        modem_reachable = await self._async_check_modem_reachable()
        if not modem_reachable:
            return AisOntStatus(
                modem_reachable=False,
                telnet_ok=None,
                authenticated=False,
                optical_signal_ok=False,
                rx_power_dbm=None,
                tx_power_dbm=None,
                poll_duration_ms=int((time.monotonic() - started) * 1000),
                checked_at=datetime.now(timezone.utc),
                error="Modem is not reachable",
            )

        try:
            rx_power, tx_power = await self._async_read_optical_power()
        except InvalidAuth:
            raise
        except AisOntError as err:
            return self._error_status(started, str(err), modem_reachable)
        except (OSError, asyncio.TimeoutError) as err:
            return self._error_status(
                started, str(err) or err.__class__.__name__, modem_reachable
            )

        return AisOntStatus(
            modem_reachable=True,
            telnet_ok=True,
            authenticated=True,
            optical_signal_ok=rx_power >= self.rx_power_min_dbm,
            rx_power_dbm=rx_power,
            tx_power_dbm=tx_power,
            poll_duration_ms=int((time.monotonic() - started) * 1000),
            checked_at=datetime.now(timezone.utc),
        )

    async def async_test_auth(self) -> AisOntStatus:
        """Read status and surface auth/connectivity failures to config flow."""
        status = await self.async_get_status()
        if not status.modem_reachable:
            raise CannotConnect(status.error or "Cannot connect")
        if not status.telnet_ok:
            raise CannotConnect(status.error or "Telnet status path is not usable")
        return status

    def _error_status(
        self, started: float, error: str, modem_reachable: bool
    ) -> AisOntStatus:
        """Build an unavailable status for polling errors."""
        return AisOntStatus(
            modem_reachable=modem_reachable,
            telnet_ok=False if modem_reachable else None,
            authenticated=False,
            optical_signal_ok=False,
            rx_power_dbm=None,
            tx_power_dbm=None,
            poll_duration_ms=int((time.monotonic() - started) * 1000),
            checked_at=datetime.now(timezone.utc),
            error=error,
        )

    async def _async_check_modem_reachable(self) -> bool:
        """Return whether the modem answers a simple TCP connect probe."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.modem_reachability_port),
                timeout=self.timeout,
            )
        except (OSError, asyncio.TimeoutError):
            return False

        writer.close()
        with suppress(Exception):
            await writer.wait_closed()
        del reader
        return True

    async def _async_read_optical_power(self) -> tuple[float, float]:
        """Open Telnet, select menu option 3, and parse RX/TX power."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
        except (OSError, asyncio.TimeoutError) as err:
            raise CannotConnect(str(err) or err.__class__.__name__) from err

        logged_in = False
        try:
            await self._read_until(reader, writer, ["login:"])
            writer.write(f"{self.username}\r\n".encode())
            await writer.drain()

            await self._read_until(reader, writer, ["password:"])
            writer.write(f"{self.password}\r\n".encode())
            await writer.drain()

            login_output = await self._read_until(
                reader,
                writer,
                ["select one command", "user name or password is wrong", "login failed"],
            )
            lowered = login_output.lower()
            if (
                "user name or password is wrong" in lowered
                or "login failed" in lowered
            ):
                raise InvalidAuth("Invalid Telnet username or password")
            if "select one command" not in lowered:
                raise UnexpectedResponse("Telnet menu prompt not found")

            logged_in = True
            writer.write(b"3\r\n")
            await writer.drain()
            power_output = await self._read_until(
                reader,
                writer,
                ["select one command"],
            )
            return parse_optical_power(power_output)
        finally:
            if logged_in:
                writer.write(b"4\r\n")
                with suppress(Exception):
                    await writer.drain()
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()

    async def _read_until(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        markers: list[str],
    ) -> str:
        """Read Telnet output until one marker appears."""
        deadline = time.monotonic() + self.timeout
        buffer = ""
        marker_lc = [marker.lower() for marker in markers]

        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                raw = await asyncio.wait_for(reader.read(256), timeout=remaining)
            except asyncio.TimeoutError as err:
                raise UnexpectedResponse(
                    f"Timed out waiting for {', '.join(markers)}"
                ) from err

            if not raw:
                raise CannotConnect("Connection closed by ONT")

            buffer += _decode_telnet(raw, writer)
            lowered = buffer.lower()
            if any(marker in lowered for marker in marker_lc):
                return buffer

        raise UnexpectedResponse(f"Timed out waiting for {', '.join(markers)}")


def _decode_telnet(data: bytes, writer: asyncio.StreamWriter) -> str:
    """Strip basic Telnet negotiation and reject options we do not need."""
    output = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        if byte != IAC:
            output.append(byte)
            i += 1
            continue

        if i + 1 >= len(data):
            break

        command = data[i + 1]
        if command in (DO, DONT, WILL, WONT):
            if i + 2 >= len(data):
                break
            option = data[i + 2]
            if command == DO:
                writer.write(bytes([IAC, WONT, option]))
            elif command == WILL:
                writer.write(bytes([IAC, DONT, option]))
            i += 3
            continue

        if command == SB:
            i += 2
            while i + 1 < len(data) and not (data[i] == IAC and data[i + 1] == SE):
                i += 1
            i += 2
            continue

        i += 2

    return output.decode("utf-8", errors="ignore")
