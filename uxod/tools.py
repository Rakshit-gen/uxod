"""What the agent can do to the solar system. Each public method is a tool;
TOOLS describes them to the model."""

import numpy as np

from . import sim

MASS_UNITS = {"msun": 1.0, "mjup": 9.5479e-4, "mearth": 3.0034e-6}
MAX_YEARS = 5000
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

    def smash(self, target: str, impactor_mass: float, mass_unit: str, speed_kms: float, direction: str):
        """An impactor hits the target and sticks, conserving momentum."""
        b = self.body(target)
        m = impactor_mass * MASS_UNITS[mass_unit]
        hit = speed_kms * sim.KMS * self._direction(b, direction)
        b.vel = (b.mass * b.vel + m * (b.vel + hit)) / (b.mass + m)
        b.mass += m
        return {"name": b.name, "mass_msun": b.mass, "delta_v_kms": round(speed_kms * m / b.mass, 4),
                "now": sim.orbit(self.bodies, b)}

    def add_flyby(self, name: str, mass: float, mass_unit: str, closest_approach_au: float, speed_kms: float,
                  angle_deg: float = 0.0, inclination_deg: float = 0.0, radius_km: float = 0.0):
        """Sends a body in on a hyperbolic path past the Sun, starting far
        enough out that it hasn't disturbed anything yet."""
        if any(b.name.lower() == name.lower() for b in self.bodies):
            raise ValueError(f"there is already a body called {name}")
        if closest_approach_au <= 0 or speed_kms <= 0:
            raise ValueError("closest_approach_au and speed_kms must be positive")
        sun = self.body("Sun")
        m = mass * MASS_UNITS[mass_unit]
        mu = sim.G * (sun.mass + m)
        v_inf = speed_kms * sim.KMS
        a = -mu / v_inf**2
        e = 1 + closest_approach_au * v_inf**2 / mu
        p = a * (1 - e * e)
        start = max(100.0, 5 * closest_approach_au)
        f = -np.arccos((p / start - 1) / e)  # inbound
        r = p / (1 + e * np.cos(f))
        pos = r * np.array([np.cos(f), np.sin(f), 0.0])
        vel = np.sqrt(mu / p) * np.array([-np.sin(f), e + np.cos(f), 0.0])
        w, i = np.radians(angle_deg), np.radians(inclination_deg)
        spin = np.array([[np.cos(w), -np.sin(w), 0], [np.sin(w), np.cos(w), 0], [0, 0, 1]])
        tilt = np.array([[1, 0, 0], [0, np.cos(i), -np.sin(i)], [0, np.sin(i), np.cos(i)]])
        rot = spin @ tilt
        big_f = np.arccosh((1 - start / a) / e)
        arrive_years = (e * np.sinh(big_f) - big_f) / np.sqrt(mu / (-a) ** 3) / sim.DAYS_PER_YEAR
        self.bodies.append(sim.Body(name, m, sun.pos + rot @ pos, sun.vel + rot @ vel,
                                    radius_km / 1.495978707e8))
        sim.to_barycentre(self.bodies)
        return {"name": name, "mass_msun": m, "starts_au": round(start, 1),
                "closest_approach_in_years": round(float(arrive_years), 2)}

    def run(self, years: float):
        """Moves time forward. Later runs carry on from where the last one stopped."""
        if not 0 < years <= MAX_YEARS:
            raise ValueError(f"years must be between 0 and {MAX_YEARS}")
        r = sim.run(self.bodies, years)
        self.results.append(r)
        return {
            "years": years,
            "events": r.events or ["nothing collided or left the system"],
            "energy_error": f"{r.energy_error:.1e}",
            "bodies": {n: {k: v for k, v in o.items() if k != "mass_msun"} for n, o in r.after.items()},
            "lost": [n for n in r.before if n not in r.after],
        }

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


_unit = {"type": "string", "enum": list(MASS_UNITS), "description": "msun, mjup (Jupiters) or mearth (Earths)"}
_dir = {"type": "string", "enum": list(DIRECTIONS), "description": "relative to the body's orbit"}

TOOLS = [
    _tool("list_bodies", "Every body now, with its orbit: semi-major axis a in AU, eccentricity e, period."),
    _tool("remove_body", "Deletes a body, the Sun included.", name={"type": "string"}),
    _tool("scale_mass", "Multiplies a body's mass by factor.", name={"type": "string"},
          factor={"type": "number"}),
    _tool("kick", "Instantly changes a body's velocity by delta_v_kms in a direction.",
          name={"type": "string"}, delta_v_kms={"type": "number"}, direction=_dir),
    _tool("smash", "Hits a body with an impactor that sticks to it, conserving momentum. Earth's orbital "
          "speed is 29.8 km/s for scale.", target={"type": "string"}, impactor_mass={"type": "number"},
          mass_unit=_unit, speed_kms={"type": "number"}, direction=_dir),
    _tool("add_flyby", "Sends a new body (a star, black hole, rogue planet) past the Sun on a hyperbolic path "
          "from 100 AU or more out. Returns how many years until it is closest, so run long enough to see it "
          "pass. A black hole is a point mass: give radius_km 0.",
          name={"type": "string"}, mass={"type": "number"}, mass_unit=_unit,
          closest_approach_au={"type": "number"}, speed_kms={"type": "number", "description": "speed far away"},
          angle_deg={"type": "number", "description": "where in the ecliptic it comes from", "optional": True},
          inclination_deg={"type": "number", "optional": True},
          radius_km={"type": "number", "optional": True}),
    _tool("run", f"Simulates the next `years` years (at most {MAX_YEARS}). With Mercury present this takes "
          "about 3 seconds per 100 years.", years={"type": "number"}),
]
TOOLS_BY_NAME = {t["function"]["name"]: t for t in TOOLS}
