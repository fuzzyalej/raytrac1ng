"""Add src/ to sys.path so tests can import modules without installation."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
