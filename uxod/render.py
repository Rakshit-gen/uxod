"""Turns runs into something to look at."""

from . import sim


def timeline(results: list[sim.Result]):
    """Every run's frames joined end to end, over every body that appeared."""
    names: list[str] = []
    for r in results:
        names += [n for n in r.names if n not in names]
    frames, years, offset = [], [], 0.0
    for r in results:
        for f, y in zip(r.frames, r.frame_years):
            where = dict(zip(r.names, f))
            frames.append([where.get(n) for n in names])
            years.append(round(offset + y, 3))
        offset += r.years
    return names, frames, years

