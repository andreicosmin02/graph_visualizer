"""UI styling and theming configuration."""

from dataclasses import dataclass


@dataclass
class ColorScheme:
    """Color scheme definition."""
    background: str
    foreground: str
    primary: str
    secondary: str
    accent: str
    success: str
    error: str
    warning: str
    text: str
    text_secondary: str
    border: str


# VS Code Dark Theme
DARK_THEME = ColorScheme(
    background="#1e1e1e",
    foreground="#e0e0e0",
    primary="#007acc",
    secondary="#264f78",
    accent="#ce9178",
    success="#6a9955",
    error="#f48771",
    warning="#dcdcaa",
    text="#e0e0e0",
    text_secondary="#858585",
    border="#3e3e42"
)

# Light theme
LIGHT_THEME = ColorScheme(
    background="#ffffff",
    foreground="#333333",
    primary="#0078d4",
    secondary="#e5f0ff",
    accent="#f08000",
    success="#107c10",
    error="#d13438",
    warning="#ffb900",
    text="#333333",
    text_secondary="#666666",
    border="#cccccc"
)


class StyleConfig:
    """UI styling configuration."""
    
    # Graph rendering
    CANVAS_BACKGROUND = DARK_THEME.background
    CANVAS_SIZE = (1000, 600)
    
    # Node styling
    NODE_RADIUS = 30
    NODE_COLOR = DARK_THEME.primary
    NODE_SELECTED_COLOR = DARK_THEME.accent
    NODE_HOVER_COLOR = DARK_THEME.secondary
    NODE_TEXT_COLOR = DARK_THEME.text
    NODE_BORDER_WIDTH = 2
    NODE_BORDER_COLOR = DARK_THEME.border
    
    # Edge styling
    EDGE_COLOR = DARK_THEME.text_secondary
    EDGE_SELECTED_COLOR = DARK_THEME.accent
    EDGE_WIDTH = 2
    EDGE_LABEL_COLOR = DARK_THEME.text
    EDGE_LABEL_SIZE = 10
    
    # Button styling
    BUTTON_COLOR = DARK_THEME.primary
    BUTTON_HOVER_COLOR = DARK_THEME.secondary
    BUTTON_TEXT_COLOR = DARK_THEME.text
    BUTTON_PADDING = 10
    BUTTON_FONT = ("Segoe UI", 10)
    
    # Input styling
    INPUT_BACKGROUND = DARK_THEME.background
    INPUT_TEXT_COLOR = DARK_THEME.text
    INPUT_BORDER_COLOR = DARK_THEME.border
    INPUT_BORDER_WIDTH = 1
    INPUT_FONT = ("Segoe UI", 10)
    
    # Font settings
    DEFAULT_FONT = ("Segoe UI", 10)
    TITLE_FONT = ("Segoe UI", 14, "bold")
    MONO_FONT = ("Courier New", 9)
    
    # Animation
    ANIMATION_DURATION_MS = 200
    
    @classmethod
    def get_color_scheme(cls) -> ColorScheme:
        """Get current color scheme."""
        return DARK_THEME
