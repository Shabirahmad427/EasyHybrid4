#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Compatibility name for the GTK4 RMSD analysis window.

The old RMSD tool duplicated the RMSD analysis interface and depended on a
missing legacy Glade file. The application menu now opens the
maintained GTK4 implementation directly.
"""
from gui.windows.analysis.RMSD_analysis_window import RMSDAnalysisWindow


class RMSDToolWindow(RMSDAnalysisWindow):
    """Backward-compatible class name backed by the native GTK4 window."""
