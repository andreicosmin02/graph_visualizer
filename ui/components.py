"""Reusable UI components with theming support."""

import tkinter as tk
from typing import Optional, Callable
from visualization.styles import DARK_THEME, StyleConfig


class ThemedFrame(tk.Frame):
    """Frame with theme support."""
    
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('bg', DARK_THEME.background)
        super().__init__(parent, **kwargs)


class ThemedButton(tk.Button):
    """Button with theme support."""
    
    def __init__(self, parent, text: str = "", command: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=StyleConfig.BUTTON_COLOR,
            fg=StyleConfig.BUTTON_TEXT_COLOR,
            activebackground=StyleConfig.BUTTON_HOVER_COLOR,
            activeforeground=StyleConfig.BUTTON_TEXT_COLOR,
            font=StyleConfig.BUTTON_FONT,
            relief=tk.FLAT,
            padx=StyleConfig.BUTTON_PADDING,
            pady=StyleConfig.BUTTON_PADDING,
            **kwargs
        )


class ThemedLabel(tk.Label):
    """Label with theme support."""
    
    def __init__(self, parent, text: str = "", **kwargs):
        kwargs.setdefault('bg', DARK_THEME.background)
        kwargs.setdefault('fg', DARK_THEME.text)
        kwargs.setdefault('font', StyleConfig.DEFAULT_FONT)
        super().__init__(parent, text=text, **kwargs)


class ThemedEntry(tk.Entry):
    """Entry with theme support."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=StyleConfig.INPUT_BACKGROUND,
            fg=StyleConfig.INPUT_TEXT_COLOR,
            insertbackground=StyleConfig.INPUT_TEXT_COLOR,
            font=StyleConfig.INPUT_FONT,
            relief=tk.SOLID,
            borderwidth=StyleConfig.INPUT_BORDER_WIDTH,
            **kwargs
        )
