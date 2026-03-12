"""Reusable UI components — Winamp-inspired warm dark theme."""

import tkinter as tk
from typing import Optional, Callable

from visualization.styles import StyleConfig

# ── Palette (Winamp authentic) ────────────────────────────────────────────────
_BG              = '#131214'   # near-black base
_CARD_BG         = '#2E2A33'   # dark panel
_BTN_BG          = '#3A343F'   # inner panel / button base
_BTN_HOVER       = '#524A45'   # warm bronze hover
_BTN_DISABLED_BG = '#1a1718'
_BTN_DISABLED_FG = '#524A45'
_ACCENT          = '#F1C232'   # yellow — headers / accents
_TEXT            = '#C5AD89'   # warm beige text
_TEXT_DIM        = '#82715B'   # bronze mid-tone
_BORDER          = '#524A45'   # warm bronze border
_INPUT_BG        = '#0e0d0f'   # darkest — inputs


# ── Frames ────────────────────────────────────────────────────────────────────

class ThemedFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('bg', _BG)
        super().__init__(parent, **kwargs)


class Card(tk.Frame):
    """Warm-brown section card."""
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('bg', _CARD_BG)
        super().__init__(parent, **kwargs)


# ── Buttons ───────────────────────────────────────────────────────────────────

class HoverButton(tk.Button):
    """Groove-relief button with hover highlight."""

    def __init__(
        self,
        parent,
        text: str = '',
        command: Optional[Callable] = None,
        bg: Optional[str] = None,
        hover_bg: Optional[str] = None,
        **kwargs,
    ):
        self._normal_bg = bg or _BTN_BG
        self._hover_bg  = hover_bg or _BTN_HOVER

        kwargs.setdefault('font',               ('Segoe UI', 10, 'bold'))
        kwargs.setdefault('padx',               10)
        kwargs.setdefault('pady',               6)
        kwargs.setdefault('relief',             tk.GROOVE)
        kwargs.setdefault('bd',                 2)
        kwargs.setdefault('cursor',             'hand2')
        kwargs.setdefault('disabledforeground', _BTN_DISABLED_FG)

        fg = kwargs.pop('fg', _TEXT)
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=self._normal_bg,
            fg=fg,
            activebackground=self._hover_bg,
            activeforeground=fg,
            **kwargs,
        )
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

    def _on_enter(self, _event) -> None:
        if str(self.cget('state')) != 'disabled':
            tk.Button.config(self, bg=self._hover_bg)

    def _on_leave(self, _event) -> None:
        if str(self.cget('state')) != 'disabled':
            tk.Button.config(self, bg=self._normal_bg)

    def config(self, **kw):
        state = kw.get('state')
        if state == tk.DISABLED:
            kw.setdefault('bg', _BTN_DISABLED_BG)
        elif state == tk.NORMAL:
            kw.setdefault('bg', self._normal_bg)
        super().config(**kw)


ThemedButton = HoverButton   # backward-compat alias


# ── Labels ────────────────────────────────────────────────────────────────────

class ThemedLabel(tk.Label):
    def __init__(self, parent, text: str = '', **kwargs):
        kwargs.setdefault('bg',   _BG)
        kwargs.setdefault('fg',   _TEXT)
        kwargs.setdefault('font', StyleConfig.DEFAULT_FONT)
        super().__init__(parent, text=text, **kwargs)


class SectionHeader(tk.Label):
    """All-caps section title in accent gold."""
    def __init__(self, parent, text: str = '', **kwargs):
        kwargs.setdefault('bg',     _CARD_BG)
        kwargs.setdefault('fg',     _ACCENT)
        kwargs.setdefault('font',   ('Segoe UI', 8, 'bold'))
        kwargs.setdefault('anchor', tk.W)
        kwargs.setdefault('padx',   10)
        kwargs.setdefault('pady',   6)
        super().__init__(parent, text=text.upper(), **kwargs)


class DimLabel(tk.Label):
    """Muted secondary label."""
    def __init__(self, parent, text: str = '', bg: Optional[str] = None, **kwargs):
        kwargs.setdefault('font', ('Segoe UI', 9))
        kwargs['bg'] = bg or _BG
        kwargs['fg'] = _TEXT_DIM
        super().__init__(parent, text=text, **kwargs)


# ── Inputs ────────────────────────────────────────────────────────────────────

class ThemedEntry(tk.Entry):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=_INPUT_BG,
            fg=_TEXT,
            insertbackground=_TEXT,
            font=StyleConfig.INPUT_FONT,
            relief=tk.GROOVE,
            bd=1,
            **kwargs,
        )


# ── Decorative ────────────────────────────────────────────────────────────────

class Separator(tk.Frame):
    """1-px divider line."""
    def __init__(self, parent, color: str = _BORDER, **kwargs):
        kwargs['bg']     = color
        kwargs['height'] = 1
        super().__init__(parent, **kwargs)


class ProgressBar(tk.Canvas):
    """Thin progress bar."""
    _TRACK = '#524A45'
    _FILL  = '#F1C232'

    def __init__(self, parent, height: int = 5, **kwargs):
        kwargs.setdefault('bg', _CARD_BG)
        kwargs['highlightthickness'] = 0
        kwargs['height'] = height
        super().__init__(parent, **kwargs)
        self._frac = 0.0
        self.bind('<Configure>', lambda _: self._draw())

    def set(self, current: int, total: int) -> None:
        denom = max(1, total - 1)
        self._frac = max(0.0, min(1.0, current / denom))
        self._draw()

    def _draw(self) -> None:
        self.delete('all')
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2:
            return
        self.create_rectangle(0, 0, w, h, fill=self._TRACK, outline='')
        fw = max(0, int(w * self._frac))
        if fw:
            self.create_rectangle(0, 0, fw, h, fill=self._FILL, outline='')


class PhaseBadge(tk.Label):
    """Coloured badge showing the current algorithm phase."""

    _CONFIGS = {
        'init':       ('#1a2015', '#9BCB2F', 'INITIAL STATE'),
        'found_path': ('#1e1a08', '#F1C232', 'PATH FOUND'),
        'augmented':  ('#152015', '#9BCB2F', 'AUGMENTED'),
        'final':      ('#2E2A33', '#C5AD89', 'COMPLETE'),
    }

    def __init__(self, parent, **kwargs):
        kwargs.setdefault('font',   ('Segoe UI', 9, 'bold'))
        kwargs.setdefault('padx',   14)
        kwargs.setdefault('pady',   7)
        kwargs.setdefault('anchor', tk.CENTER)
        kwargs.setdefault('relief', tk.GROOVE)
        kwargs.setdefault('bd',     1)
        cfg = self._CONFIGS['init']
        kwargs.setdefault('bg', cfg[0])
        kwargs.setdefault('fg', cfg[1])
        super().__init__(parent, text=cfg[2], **kwargs)

    def set_phase(self, phase: str) -> None:
        cfg = self._CONFIGS.get(phase, self._CONFIGS['init'])
        self.config(bg=cfg[0], fg=cfg[1], text=cfg[2])
