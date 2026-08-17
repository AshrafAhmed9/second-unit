"""Deliberately no eager imports here.

second_unit.agent pulls in google-adk, which isn't needed to run the pure
logic (schedule.py, tools/shotlist.py) or its tests. Import second_unit.agent
directly where the full graph is actually needed (server.py, adk web/run).
"""
