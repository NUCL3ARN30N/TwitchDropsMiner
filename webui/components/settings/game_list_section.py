from __future__ import annotations

from abc import ABC, abstractmethod
import re
from typing import TYPE_CHECKING

from nicegui import ui

from translate import _

if TYPE_CHECKING:
    from nicegui.elements.input import Input
    from webui.manager import WebUIManager


class GameListSection(ABC):
    """
    Abstract base for the List and Exclude sections.

    Both sections show a filterable, selectable list of game names backed by
    a settings collection. Subclasses supply the data model (_options, _items,
    selection logic, add/delete) and their own build() layout with buttons;
    this base provides the shared input row, list UI, and game-name helpers.
    """

    def __init__(self, manager: "WebUIManager") -> None:
        self._manager = manager
        self._game_names: set[str] = set()

    @property
    def _settings(self):
        return self._manager._twitch.settings

    def set_games(self, games: set) -> None:
        self._game_names = {game.name for game in games}
        self._input_content.refresh()

    # -------------------------------------------------------------------------
    # Abstract — subclasses supply the data model
    # -------------------------------------------------------------------------

    @abstractmethod
    def _options(self) -> list[str]:
        """Games available to add (not already in the list)."""
        ...

    @abstractmethod
    def _items(self) -> list:
        """Current items to render in the list."""
        ...

    @abstractmethod
    def _item_label(self, item) -> str:
        """Display text for a list item."""
        ...

    @abstractmethod
    def _is_selected(self, item) -> bool: ...

    @abstractmethod
    def _on_select(self, item) -> None: ...

    @abstractmethod
    def _on_delete(self) -> None: ...

    @abstractmethod
    def _do_add(self, name: str, input_el: "Input") -> None:
        """Persist the addition and refresh the UI."""
        ...

    # -------------------------------------------------------------------------
    # Shared refreshable UI
    # -------------------------------------------------------------------------

    @ui.refreshable
    def _input_content(self) -> None:
        with ui.row().classes("w-full gap-1 items-center"):
            input_el = (
                ui.input(
                    label=_("gui", "settings", "game_name"),
                    autocomplete=self._options(),
                )
                .classes("flex-1 text-xs")
                .props("dense")
                .on("keydown.enter", lambda: self._add_game(input_el))
            )
            with (
                ui.button(icon="expand_more").props("dense flat").classes("p-0 min-h-0")
            ):
                with ui.menu():
                    for name in self._options():
                        ui.menu_item(
                            name, on_click=lambda _, n=name: input_el.set_value(n)
                        ).classes("text-xs")
            ui.button("+", on_click=lambda: self._add_game(input_el)).props(
                "dense flat"
            ).classes("text-xl p-0 min-h-0")
            ui.button(icon="playlist_add", on_click=self._open_bulk_dialog).props(
                "dense flat"
            ).classes("text-lg p-0 min-h-0")

    @ui.refreshable
    def _list_content(self) -> None:
        with (
            ui.list()
            .props("dense bordered")
            .classes("flex-1 text-xs overflow-y-auto min-h-[200px]")
        ):
            for item in self._items():
                active = self._is_selected(item)
                with (
                    ui.item()
                    .props(f"clickable {'active' if active else ''}")
                    .classes("bg-primary text-white" if active else "")
                    .on("click", lambda _, i=item: self._on_select(i))
                ):
                    with ui.item_section():
                        ui.item_label(self._item_label(item)).classes("text-xs")

    # -------------------------------------------------------------------------
    # Shared helpers
    # -------------------------------------------------------------------------

    def _add_game(self, input_el: "Input") -> None:
        name = input_el.value
        if not name or not str(name).strip():
            return
        name = self._correct_game_case(str(name).strip())
        if name not in self._game_names:
            self._confirm_unknown_game(name, lambda: self._do_add(name, input_el))
            return
        self._do_add(name, input_el)

    def _open_bulk_dialog(self) -> None:
        with ui.dialog().props("transition-show=none transition-hide=none") as dialog, ui.card().classes("q-pa-sm gap-2"):
            ui.label(_("webui", "game_list", "bulk_add_title")).classes(
                "text-sm font-bold"
            )
            ui.label(_("webui", "game_list", "bulk_add_hint")).classes("text-xs")
            textarea = (
                ui.textarea(
                    placeholder=_("webui", "game_list", "bulk_add_placeholder"),
                )
                .classes("w-full text-xs")
                .props("dense outlined rows=8")
            )
            with ui.row().classes("gap-2 justify-end w-full"):

                def _cancel():
                    dialog.close()
                    dialog.delete()

                def _confirm():
                    raw = textarea.value or ""
                    names = [n.strip() for n in re.split(r"[,\n]", raw) if n.strip()]
                    dialog.close()
                    dialog.delete()
                    self._add_bulk(names)

                ui.button(
                    _("webui", "game_list", "cancel"), on_click=_cancel
                ).props("dense flat").classes("text-xs")
                ui.button(
                    _("webui", "game_list", "add"), on_click=_confirm
                ).props("dense").classes("text-xs")
        dialog.open()

    def _add_bulk(self, names: list[str]) -> None:
        unknown: list[str] = []
        for raw_name in names:
            name = self._correct_game_case(raw_name)
            if name not in self._game_names:
                unknown.append(name)
                continue
            self._do_add(name, None)
        if unknown:
            def _add_unknown() -> None:
                for name in unknown:
                    self._do_add(name, None)

            self._confirm_unknown_game(", ".join(unknown), _add_unknown)

    def _correct_game_case(self, value: str) -> str:
        lower = value.lower()
        for name in self._game_names:
            if name.lower() == lower:
                return name
        return value

    def _confirm_unknown_game(self, name: str, on_confirm) -> None:
        with ui.dialog().props("transition-show=none transition-hide=none") as dialog, ui.card().classes("q-pa-sm"):
            ui.label(_("webui", "game_list", "no_campaigns").format(name=name)).classes(
                "text-sm font-bold"
            )
            ui.label(_("webui", "game_list", "add_anyway")).classes("text-xs")
            with ui.row().classes("gap-2 justify-end w-full"):

                def _cancel():
                    dialog.close()
                    dialog.delete()

                def _confirm():
                    dialog.close()
                    dialog.delete()
                    on_confirm()

                ui.button(_("webui", "game_list", "cancel"), on_click=_cancel).props(
                    "dense flat"
                ).classes("text-xs")
                ui.button(_("webui", "game_list", "add"), on_click=_confirm).props(
                    "dense"
                ).classes("text-xs")
        dialog.open()
