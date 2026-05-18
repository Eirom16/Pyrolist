from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorScheme:
    bg_base: str
    bg_surface: str
    bg_elevated: str
    bg_high: str
    bg_overlay: str
    accent: str
    accent_bright: str
    accent_dim: str
    secondary: str
    secondary_dim: str
    text_primary: str
    text_secondary: str
    text_disabled: str
    text_on_accent: str
    border: str
    border_focus: str
    success: str
    warning: str
    error: str
    info: str
    like_color: str


DARK = ColorScheme(
    bg_base="#0A0A14",
    bg_surface="#10101E",
    bg_elevated="#16162A",
    bg_high="#1E1E38",
    bg_overlay="rgba(10,10,20,0.85)",
    accent="#A78BFA",
    accent_bright="#8B5CF6",
    accent_dim="rgba(167,139,250,0.15)",
    secondary="#22D3EE",
    secondary_dim="rgba(34,211,238,0.15)",
    text_primary="#F1F0FF",
    text_secondary="#9B9BC0",
    text_disabled="#4A4A6A",
    text_on_accent="#0A0A14",
    border="rgba(167,139,250,0.12)",
    border_focus="rgba(167,139,250,0.50)",
    success="#34D399",
    warning="#FBBF24",
    error="#F87171",
    info="#60A5FA",
    like_color="#F472B6",
)


LIGHT = ColorScheme(
    bg_base="#F3F3F9",
    bg_surface="#FFFFFF",
    bg_elevated="#E8E8F0",
    bg_high="#DFDFE8",
    bg_overlay="rgba(243,243,249,0.85)",
    accent="#A78BFA",
    accent_bright="#8B5CF6",
    accent_dim="rgba(167,139,250,0.15)",
    secondary="#06B6D4",
    secondary_dim="rgba(6,182,212,0.15)",
    text_primary="#121224",
    text_secondary="#5C5C8A",
    text_disabled="#9E9EBF",
    text_on_accent="#FFFFFF",
    border="rgba(167,139,250,0.12)",
    border_focus="rgba(167,139,250,0.50)",
    success="#10B981",
    warning="#F59E0B",
    error="#EF4444",
    info="#3B82F6",
    like_color="#EC4899",
)

CURRENT = DARK
