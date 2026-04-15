"""Retailer Pitcher agent — second agent in the Sedge pipeline.

Consumes Brand Scout output from shared memory, drafts a buyer-specific
outreach email and a 1-page sell sheet (HTML), and persists artifacts
back to Supabase for downstream agents.
"""
from agents.retailer_pitcher.graph import graph

__all__ = ["graph"]
