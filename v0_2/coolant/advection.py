from dataclasses import dataclass
from math import fsum

import numpy as np

from v0_2.coolant.volume import CoolantVolumeState
from v0_2.thermal.validity import ThermalError, ValidityStatus, finite, require


@dataclass(frozen=True)
class AdvectiveLink:
    link_id: str
    from_id: str
    to_id: str
    mass_flow_kg_s: float
    owner_id: str
    reverse_supported: bool = False

    def __post_init__(self):
        require(
            bool(self.link_id and self.from_id and self.to_id and self.owner_id), "ADVECTION", "ID"
        )
        require(self.from_id != self.to_id, "ADVECTION", "self link")
        finite(self.mass_flow_kg_s, "mass flow")
        require(
            self.mass_flow_kg_s >= 0 or self.reverse_supported,
            "REVERSE_FLOW",
            self.link_id,
            ValidityStatus.MODEL_INVALID,
        )

    @property
    def donor_id(self):
        return self.from_id if self.mass_flow_kg_s >= 0 else self.to_id

    @property
    def receiver_id(self):
        return self.to_id if self.mass_flow_kg_s >= 0 else self.from_id

    @property
    def magnitude(self):
        return abs(self.mass_flow_kg_s)


@dataclass(frozen=True)
class AdvectiveEnergy:
    link_id: str
    donor_id: str
    receiver_id: str
    mass_kg: float
    energy_j: float
    owner_id: str

    @property
    def postings(self):
        return ((self.donor_id, -self.energy_j), (self.receiver_id, self.energy_j))


@dataclass(frozen=True)
class TransportResult:
    volumes: tuple[CoolantVolumeState, ...]
    transfers: tuple[AdvectiveEnergy, ...]
    volume_mass_residual_kg_s: tuple[tuple[str, float], ...]
    volume_energy_residual_j: tuple[tuple[str, float], ...]


def solve_implicit(volumes, links, dt_s, boundary_enthalpy=None, heat_w=None):
    """One coupled backward-Euler step; external ports are zero-storage declared boundaries."""
    boundary_enthalpy = boundary_enthalpy or {}
    heat_w = heat_w or {}
    require(dt_s > 0, "INVALID_TIME", "positive transport step")
    ids = [v.volume_id for v in volumes]
    require(len(ids) == len(set(ids)), "VOLUME_OWNERSHIP_DUPLICATE", "volume IDs")
    require(
        len({v.storage_owner_id for v in volumes}) == len(volumes),
        "VOLUME_OWNERSHIP_DUPLICATE",
        "storage owners",
    )
    require(len({l.link_id for l in links}) == len(links), "DUPLICATE_FLUX", "advection IDs")
    by_id = {v.volume_id: v for v in volumes}
    require(not set(by_id) & set(boundary_enthalpy), "BOUNDARY_STORAGE_CONFLICT", "fluid port")
    require(set(heat_w) <= set(by_id), "HEAT_RECEIVER", "unknown volume")
    for link in links:
        require(
            link.donor_id in by_id or link.donor_id in boundary_enthalpy,
            "MISSING_ENDPOINT",
            link.donor_id,
        )
        require(
            link.receiver_id in by_id or link.receiver_id in boundary_enthalpy,
            "MISSING_ENDPOINT",
            link.receiver_id,
        )
        if link.donor_id in by_id and link.receiver_id in by_id:
            require(
                by_id[link.donor_id].coolant_ref == by_id[link.receiver_id].coolant_ref,
                "COOLANT_MISMATCH",
                link.link_id,
            )
    mass = {name: 0.0 for name in ids}
    incident = {name: 0.0 for name in ids}
    for link in links:
        q = link.magnitude
        if link.donor_id in by_id:
            mass[link.donor_id] -= q
            incident[link.donor_id] += q
        if link.receiver_id in by_id:
            mass[link.receiver_id] += q
            incident[link.receiver_id] += q
    for name in ids:
        require(
            abs(mass[name]) <= 1e-9 + 1e-8 * incident[name],
            "MASS_BALANCE_FAIL",
            name,
            ValidityStatus.MODEL_INVALID,
        )
    index = {name: i for i, name in enumerate(ids)}
    matrix = np.diag([v.mass_kg.value for v in volumes]).astype(float)
    rhs = np.array([v.mass_kg.value * v.specific_enthalpy_j_kg for v in volumes])
    for name, watts in heat_w.items():
        finite(watts, "volume heat")
        rhs[index[name]] += dt_s * watts
    for link in links:
        qdt = link.magnitude * dt_s
        if link.receiver_id in index:
            r = index[link.receiver_id]
            if link.donor_id in index:
                matrix[r, index[link.donor_id]] -= qdt
            else:
                rhs[r] += qdt * boundary_enthalpy[link.donor_id]
        if link.donor_id in index:
            matrix[index[link.donor_id], index[link.donor_id]] += qdt
    try:
        h_new = np.linalg.solve(matrix, rhs)
        next_volumes = tuple(v.at_h(h_new[index[v.volume_id]]) for v in volumes)
    except (np.linalg.LinAlgError, FloatingPointError, ValueError) as error:
        if isinstance(error, ThermalError):
            raise
        raise ThermalError("SOLVER_FAILED", str(error), ValidityStatus.MODEL_INVALID) from error
    transfers = tuple(
        AdvectiveEnergy(
            l.link_id,
            l.donor_id,
            l.receiver_id,
            l.magnitude * dt_s,
            l.magnitude
            * dt_s
            * (h_new[index[l.donor_id]] if l.donor_id in index else boundary_enthalpy[l.donor_id]),
            l.owner_id,
        )
        for l in links
    )
    residuals = []
    for old, new in zip(volumes, next_volumes):
        name = old.volume_id
        change = new.energy_j - old.energy_j
        incoming = fsum(t.energy_j for t in transfers if t.receiver_id == name)
        outgoing = fsum(t.energy_j for t in transfers if t.donor_id == name)
        residual = change - (incoming - outgoing + dt_s * heat_w.get(name, 0.0))
        scale = abs(change) + abs(incoming) + abs(outgoing) + abs(dt_s * heat_w.get(name, 0.0))
        require(
            abs(residual) <= 1e-6 + 1e-6 * scale,
            "ENERGY_BALANCE_FAIL",
            name,
            ValidityStatus.MODEL_INVALID,
        )
        residuals.append((name, residual))
    return TransportResult(next_volumes, transfers, tuple(mass.items()), tuple(residuals))
