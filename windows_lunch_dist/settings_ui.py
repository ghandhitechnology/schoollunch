# -*- coding: utf-8 -*-
"""Compatibility wrapper for the full application UI."""
from app_ui import show_app


def show_settings(on_save=None) -> bool:
    return show_app(on_save=on_save)


if __name__ == "__main__":
    print("저장됨:", show_settings())
