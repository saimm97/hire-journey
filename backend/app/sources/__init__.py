from app.sources.ashby import AshbySource
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource

SOURCES = {
    "greenhouse": GreenhouseSource(),
    "ashby": AshbySource(),
    "lever": LeverSource(),
}
