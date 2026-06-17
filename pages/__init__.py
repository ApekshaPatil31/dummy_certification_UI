"""Page modules for the HITL certification wireframe.

Each module exposes a single `show_*()` function the app.py router calls. They are
plain functions (no top-level Streamlit calls), so Streamlit's native multipage
nav — which is hidden via CSS in app.py — never executes them directly.
"""
