# src/tools/enricher/__init__.py
"""
Enricher Tool for Obsidian Notes

This module provides tools for enriching Obsidian notes in two modes:
1. Simple Enrichment: Enhances the content of a single note directly
2. Advanced Enrichment: Uses the Researcher tool to generate a hierarchy of new 
   research notes based on an existing note's content
"""

from src.tools.enricher.assistant import EnricherAssistant

__all__ = ["EnricherAssistant"]