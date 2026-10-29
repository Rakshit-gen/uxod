"""What the agent can do to the solar system. Each public method is a tool;
TOOLS describes them to the model."""

import numpy as np

from . import sim

DIRECTIONS = ("prograde", "retrograde", "outward", "inward", "north", "south")


class Universe:
    def __init__(self):
        self.bodies = sim.solar_system()
        self.results: list[sim.Result] = []
        self.log: list[dict] = []  # every call, so the plan can be replayed without a model

    def call(self, tool: str, args: dict):
        if tool not in TOOLS_BY_NAME:
            return {"error": f"no tool called {tool}"}
        self.log.append({"tool": tool, "args": args})
        try:
            return getattr(self, tool)(**args)
        except (TypeError, ValueError, KeyError) as e:
            return {"error": str(e)}

    def body(self, name: str) -> sim.Body:
        for b in self.bodies:
            if b.name.lower() == name.lower():
                return b
        raise KeyError(f"no body called {name}; there are {', '.join(b.name for b in self.bodies)}")

    def list_bodies(self):
        return sim.snapshot(self.bodies)

    def remove_body(self, name: str):
        b = self.body(name)
        self.bodies.remove(b)
        return {"removed": b.name}

    def scale_mass(self, name: str, factor: float):
        if factor <= 0:
            raise ValueError("factor must be positive; use remove_body to delete a body")
        b = self.body(name)
        b.mass *= factor
        return {"name": b.name, "mass_msun": b.mass}

    def kick(self, name: str, delta_v_kms: float, direction: str):
        """Changes a body's velocity relative to the body it orbits."""
        b = self.body(name)
        b.vel = b.vel + delta_v_kms * sim.KMS * self._direction(b, direction)
        return {"name": b.name, "now": sim.orbit(self.bodies, b)}

    def _direction(self, b: sim.Body, direction: str) -> np.ndarray:
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {', '.join(DIRECTIONS)}")
        host = sim.primary(self.bodies, b)
        r, v = b.pos - host.pos, b.vel - host.vel
        unit = {"prograde": v, "retrograde": -v, "outward": r, "inward": -r,
                "north": np.cross(r, v), "south": -np.cross(r, v)}[direction]
        return unit / np.linalg.norm(unit)


def _tool(name, description, /, **params):
    required = [k for k, v in params.items() if not v.pop("optional", False)]
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": params, "required": required}}}


_dir = {"type": "string", "enum": list(DIRECTIONS), "description": "relative to the body's orbit"}

TOOLS = [
    _tool("list_bodies", "Every body now, with its orbit: semi-major axis a in AU, eccentricity e, period."),
    _tool("remove_body", "Deletes a body, the Sun included.", name={"type": "string"}),
    _tool("scale_mass", "Multiplies a body's mass by factor.", name={"type": "string"},
          factor={"type": "number"}),
    _tool("kick", "Instantly changes a body's velocity by delta_v_kms in a direction.",
          name={"type": "string"}, delta_v_kms={"type": "number"}, direction=_dir),
]
TOOLS_BY_NAME = {t["function"]["name"]: t for t in TOOLS}
