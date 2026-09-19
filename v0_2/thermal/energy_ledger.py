from dataclasses import dataclass
from math import fsum

from .source_mapping import ThermalSourceReceipt
from .validity import require


@dataclass(frozen=True)
class InterfaceEnergy:
    interface_id: str
    hot_node_id: str
    cold_node_id: str | None
    external_boundary_id: str | None
    energy_j: float
    start_ns: int
    end_ns: int
    owner_id: str
    mechanism: str
    boundary_medium: str | None

    @property
    def node_postings(self):
        # One stored transfer, never independently recomputed heat on the second side.
        return ((self.hot_node_id, -self.energy_j),) + (
            ((self.cold_node_id, self.energy_j),) if self.cold_node_id else ()
        )


@dataclass(frozen=True)
class CVBalance:
    cv_id: str
    stored_change_j: float
    source_energy_j: float
    exported_energy_j: float
    residual_j: float
    scale_j: float

    @property
    def tolerance_j(self):
        return 1e-6 + 1e-6 * self.scale_j

    @property
    def passed(self):
        return abs(self.residual_j) <= self.tolerance_j


@dataclass(frozen=True)
class EnergyLedger:
    sources: tuple[ThermalSourceReceipt, ...]
    interfaces: tuple[InterfaceEnergy, ...]
    balances: tuple[CVBalance, ...]

    @classmethod
    def build(cls, before, after, receipts, fluxes, device_cvs):
        require(
            len({f.interface_id for f in fluxes}) == len(fluxes),
            "DUPLICATE_FLUX",
            "interval interface ownership",
        )
        old, new = before.by_id(), after.by_id()
        cvs = (*device_cvs, *((f"node:{n}", (n,)) for n in old), ("subsystem", tuple(old)))
        balances = []
        for cv_id, members in cvs:
            members = set(members)
            storage = fsum(new[n].energy_j - old[n].energy_j for n in members)
            source = fsum(r.energy_j for r in receipts if r.thermal_node_id in members)
            crossings = []
            for f in fluxes:
                hot, cold = f.hot_node_id in members, f.cold_node_id in members
                if hot != cold:
                    crossings.append(f.energy_j if hot else -f.energy_j)
            exported = fsum(crossings)
            scale = abs(storage) + abs(source) + fsum(abs(q) for q in crossings)
            balances.append(
                CVBalance(cv_id, storage, source, exported, storage - (source - exported), scale)
            )
        return cls(tuple(receipts), tuple(fluxes), tuple(balances))

    def balance(self, cv="subsystem"):
        return next(b for b in self.balances if b.cv_id == cv)


def cumulative_balances(ledgers):
    require(bool(ledgers), "EMPTY_LEDGER", "no accepted intervals")
    result = {}
    for cv_id in [b.cv_id for b in ledgers[0].balances]:
        values = [ledger.balance(cv_id) for ledger in ledgers]
        signed = fsum(v.residual_j for v in values)
        absolute = fsum(abs(v.residual_j) for v in values)
        tolerance = 1e-6 + 1e-6 * fsum(v.scale_j for v in values)
        result[cv_id] = {
            "signed_residual_j": signed,
            "absolute_residual_j": absolute,
            "tolerance_j": tolerance,
            "passed": abs(signed) <= tolerance and absolute <= tolerance,
        }
    return result
