"""What the agent can do to the solar system. Each public method is a tool;
TOOLS describes them to the model."""

from . import sim


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



def _tool(name, description, /, **params):
    required = [k for k, v in params.items() if not v.pop("optional", False)]
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": params, "required": required}}}



TOOLS = [
    _tool("list_bodies", "Every body now, with its orbit: semi-major axis a in AU, eccentricity e, period."),
    _tool("remove_body", "Deletes a body, the Sun included.", name={"type": "string"}),
    _tool("scale_mass", "Multiplies a body's mass by factor.", name={"type": "string"},
          factor={"type": "number"}),
]
TOOLS_BY_NAME = {t["function"]["name"]: t for t in TOOLS}
