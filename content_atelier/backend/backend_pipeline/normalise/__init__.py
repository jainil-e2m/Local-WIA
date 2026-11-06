"""Normalisation (plan Phase 1, section 4.7): one normaliser per source, then classification, speakers and dates.

sources    the one normaliser per source: a Fathom call (from the API or from native JSON), a Slack thread, a text file
classify   what kind of call a document is, and whether it is included (rules, then a fast model for what rules cannot place)
speakers   speaker labels resolved to people and roles, stored beside the immutable passage map
dates      occurrence dates from evidence only
segment    chunks with a header, a one-turn overlap and speaker roles
glossary   product, staff and client names and their common mis-transcriptions, for a search copy

A document's text and passage map are immutable once stored. Everything here that learns something later (a call type, a
role, a date) writes beside them, never into them.
"""
NORMALISER_VERSION = "normalise-v1"
