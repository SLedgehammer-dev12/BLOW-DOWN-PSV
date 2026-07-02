# Blowdown Studio v2.4.3 Release Notes

**Release Date:** July 2, 2026  
**Version:** v2.4.3  
**Previous Version:** v2.4.2

## Overview

This release focuses on **user interface improvements** and **usability enhancements** for different screen resolutions and monitor configurations. The update addresses key feedback from users regarding scrollability, column resizing, and input field visibility.

## Key Features

### 1. Enhanced Scroll Support

**Horizontal and Vertical Scrollbars**
- Added horizontal scrollbar to the Blowdown Analysis tab
- Vertical scrollbar improved with better region management
- Content now properly scrolls in both directions when exceeding viewport

**Cross-Platform Mouse Wheel Support**
- macOS trackpad compatibility with proper delta normalization
- Linux mouse wheel support via Button-4/Button-5 events
- Shift+MouseWheel for horizontal scrolling (Windows, macOS, Linux)
- Mouse wheel only active when hovering over scrollable areas (prevents conflicts with other widgets)

### 2. Resizable Interface Columns

**PanedWindow Implementation**
- Main settings and gas composition sections now separated by a draggable sash
- Users can resize columns by dragging the divider left or right
- Initial ratio maintained at 7:3 (main settings : gas composition)
- Resizing persists during session

### 3. Improved Input Field Visibility

**Automatic Scroll Region Refresh**
- Scroll region now automatically updates after mode changes (Blowdown ↔ PSV)
- Input fields under "Temel Girdiler" section remain visible after switching modes
- No more hidden or clipped input boxes

### 4. Update Mechanism Improvements

**Smarter Version Checking**
- GitHub update check now filters out draft releases
- Prerelease versions no longer trigger update notifications
- Only stable, published releases are considered for updates

## Technical Changes

### Modified Files

| File | Changes |
|------|---------|
| `ui_builders.py` | Added horizontal scrollbar, PanedWindow, mousewheel handlers |
| `ui_state_actions.py` | Added scrollregion refresh after mode changes |
| `update_actions.py` | Added draft/prerelease filtering in `fetch_latest_release()` |
| `app_metadata.py` | Updated version to v2.4.3, added release history |
| `blowdown_studio_version_info.txt` | Updated Windows version metadata |
| `github_update_release.py` | Updated TAG and EXE_PATH to v2.4.3 |

### Test Coverage

**7 New Tests Added:**

1. `test_fetch_latest_release_filters_draft()` - Verifies draft releases are filtered
2. `test_fetch_latest_release_filters_prerelease()` - Verifies prereleases are filtered
3. `test_fetch_latest_release_returns_stable()` - Verifies stable releases pass through
4. `test_build_application_shell_ui_has_horizontal_scrollbar()` - Verifies horizontal scrollbar exists
5. `test_build_application_shell_ui_scrollregion_refresh()` - Verifies refresh function is callable
6. `test_build_left_pane_ui_paned_window()` - Verifies PanedWindow structure
7. `test_apply_mode_change_triggers_scrollregion_refresh()` - Verifies scrollregion updates on mode change

**1 Test Updated:**
- `test_build_left_pane_ui_smoke()` - Updated to check PanedWindow instead of grid weights

**All 24 tests passing** across 4 test files.

## Upgrade Instructions

### From v2.4.2

1. Download `Blowdown_Studio_v2.4.3.exe` from the release assets
2. Replace your existing installation
3. No settings migration required - all settings files remain compatible

### From Earlier Versions

1. Download the latest release
2. Backup your settings files (`.json`) if you have custom configurations
3. Install v2.4.3
4. Restore your settings files if needed

## Known Limitations

- PanedWindow sash position is not persisted between sessions (resets to default on restart)
- Horizontal scrolling requires content wider than viewport (normal behavior)
- macOS users: Natural scrolling direction is respected

## System Requirements

- **OS:** Windows 10/11 (primary), macOS (secondary), Linux (tertiary)
- **Python:** 3.8+ (for source builds)
- **Dependencies:** CoolProp, matplotlib, numpy, pandas, tkinter

## Bug Fixes

- ✅ Input fields no longer disappear after mode changes
- ✅ Update notifications no longer appear for draft/prerelease versions
- ✅ Mouse wheel no longer interferes with other scrollable widgets
- ✅ Scroll region properly updates when fields are shown/hidden

## Compatibility

- **Settings Files:** Fully compatible with v2.4.0, v2.4.1, v2.4.2
- **Vendor Catalogs:** Compatible with all previous versions
- **Export Formats:** CSV/PDF exports unchanged

## Next Steps (Roadmap)

See `STANDARD_ALIGNMENT_ROADMAP.md` for upcoming features:
- Persist PanedWindow sash position in settings
- Additional UI customization options
- Performance optimizations for large datasets

## Support

For issues, questions, or feedback:
- GitHub Issues: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/issues
- Documentation: See `PROJE_DURUMU.md` and `GELISIM_OZETI.md`

## Checksums

SHA256 checksums for release assets will be provided after build.

---

**Full Changelog:** See `CHANGELOG.md` for complete version history.
