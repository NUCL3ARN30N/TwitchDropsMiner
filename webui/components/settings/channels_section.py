from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from translate import _

if TYPE_CHECKING:
    from nicegui.elements.input import Input
    from webui.manager import WebUIManager


class ChannelsSection:
    """
    Settings section for the channel-points-mining priority list: channels
    the user wants watched (and their points mined) whenever no drop
    campaign currently needs the watch slot. Unlike games, there's no fixed
    catalog of channels to validate against, so adding one resolves it
    against Twitch first.
    """

    def __init__(self, manager: "WebUIManager") -> None:
        self._manager = manager
        self._selected: int | None = None

    @property
    def _settings(self):
        return self._manager._twitch.settings

    def build(self) -> None:
        with (
            ui.card()
            .props("flat bordered")
            .classes("q-pa-sm flex flex-col grow shrink basis-60 min-w-0")
        ):
            ui.label(_("webui", "channels", "title")).classes("font-bold text-sm")
            ui.label(_("webui", "channels", "empty_hint")).classes("text-xs opacity-70")
            self._input_content()
            with ui.row().classes("w-full gap-1 items-start min-h-[200px]"):
                self._list_content()
                with ui.column().classes("gap-1"):
                    ui.button("⏫", on_click=lambda: self._move("top")).props(
                        "flat"
                    ).classes("text-xl p-0 min-h-0")
                    ui.button("⬆️", on_click=lambda: self._move("up")).props(
                        "flat"
                    ).classes("text-xl p-0 min-h-0")
                    ui.button("⬇️", on_click=lambda: self._move("down")).props(
                        "flat"
                    ).classes("text-xl p-0 min-h-0")
                    ui.button("⏬", on_click=lambda: self._move("bottom")).props(
                        "flat"
                    ).classes("text-xl p-0 min-h-0")
                    ui.button("❌", on_click=self._on_delete).props("flat").classes(
                        "text-red-500 text-xl p-0 min-h-0"
                    )

    @ui.refreshable
    def _input_content(self) -> None:
        with ui.row().classes("w-full gap-1 items-center"):
            input_el = (
                ui.input(label=_("webui", "channels", "channel_login"))
                .classes("flex-1 text-xs")
                .props("dense")
                .on("keydown.enter", lambda: self._add_channel(input_el))
            )
            ui.button("+", on_click=lambda: self._add_channel(input_el)).props(
                "dense flat"
            ).classes("text-xl p-0 min-h-0")

    @ui.refreshable
    def _list_content(self) -> None:
        twitch = self._manager._twitch
        with (
            ui.list()
            .props("dense bordered")
            .classes("flex-1 text-xs overflow-y-auto min-h-[200px]")
        ):
            for idx, login in enumerate(self._settings.point_channels):
                active = idx == self._selected
                channel = twitch._points_channels.get(login)
                if channel is not None:
                    label = channel.name
                    status = (
                        _("webui", "channels", "live")
                        if channel.online
                        else _("webui", "channels", "offline")
                    )
                else:
                    label = login
                    status = ""
                with (
                    ui.item()
                    .props(f"clickable {'active' if active else ''}")
                    .classes("bg-primary text-white" if active else "")
                    .on("click", lambda _e, i=idx: self._on_select(i))
                ):
                    with ui.item_section():
                        ui.item_label(label).classes("text-xs")
                    if status:
                        with ui.item_section().props("side"):
                            ui.item_label(status).classes("text-xs opacity-70")

    def _on_select(self, idx: int) -> None:
        self._selected = None if self._selected == idx else idx
        self._list_content.refresh()

    def _on_delete(self) -> None:
        if self._selected is None:
            return
        channels = self._settings.point_channels
        if 0 <= self._selected < len(channels):
            del channels[self._selected]
            self._settings.save(force=True)
        self._selected = None
        self._list_content.refresh()

    def _move(self, direction: str) -> None:
        idx = self._selected
        channels = self._settings.point_channels
        if idx is None or not channels or idx < 0 or idx >= len(channels):
            return
        max_idx = len(channels) - 1
        if direction == "top":
            new_idx = 0
        elif direction == "up":
            new_idx = max(0, idx - 1)
        elif direction == "down":
            new_idx = min(max_idx, idx + 1)
        else:
            new_idx = max_idx
        if new_idx == idx:
            return
        item = channels.pop(idx)
        channels.insert(new_idx, item)
        self._settings.save(force=True)
        self._selected = new_idx
        self._list_content.refresh()

    async def _add_channel(self, input_el: "Input") -> None:
        login = (input_el.value or "").strip().lstrip("@").lower()
        if not login:
            return
        if login in self._settings.point_channels:
            ui.notify(_("webui", "channels", "already_added"), type="warning")
            return
        channel = await self._manager._twitch.resolve_channel_login(login)
        if channel is None:
            ui.notify(
                _("webui", "channels", "invalid_channel").format(login=login),
                type="negative",
            )
            return
        self._settings.point_channels.append(login)
        self._settings.save(force=True)
        input_el.set_value("")
        self._list_content.refresh()
