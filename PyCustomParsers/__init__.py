import inspect, os, sys
sys.path.append(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
#A requirement for portray
# sys.path.append(
#     f"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))}"
#     f"/PyCustomCollections")

__version__ = "0.9.0"