# Graph Visualizer

Interactive directed graph editor with a step-by-step Generic Max Flow algorithm visualizer. Built with tkinter + matplotlib.

## Usage

```bash
python3 run.py
```

## Controls

- **Click empty space**: Add node
- **Drag node**: Move
- **Click node → Click node**: Create edge
- **Left-click edge label**: Edit flux/capacity
- **Right-click node/label**: Delete
- **Escape**: Deselect
- **Ctrl+S/O/N**: Save/Open/New

## Features

- Interactive node/edge creation and editing
- Generic Max Flow algorithm (Ford-Fulkerson) with step-by-step visualizer
- Randomized augmenting path selection (different paths each run)
- Winamp-inspired dark theme
- JSON persistence
- Supports parallel edges
