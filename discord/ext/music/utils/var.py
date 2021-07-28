from typing import Any

class ContextVar:
    """
    like tkinter.StringVar,
    but with get() and set() only

    you can store any type in this thing

    """
    def __init__(self, context=None):
        self._ctx = context

    def set(self, context: Any=None):
        self._ctx = context

    def get(self):
        return self._ctx