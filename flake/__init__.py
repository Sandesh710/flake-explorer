"""A Python implementation of FLake."""
from .configuration import Lake, ModelOptions, InitialConditions
from .model import simulate, Simulation
__version__ = '2.0.0'
__all__ = ['Lake', 'ModelOptions', 'InitialConditions', 'simulate', 'Simulation']
