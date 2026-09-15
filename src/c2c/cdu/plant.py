from c2c.cdu.heat_exchanger import CDUExchange, exchange


class CDUPlant:
    def __init__(self, config: dict, density_kg_m3: float, cp_j_kgk: float):
        self.cfg = config
        self.rho = density_kg_m3
        self.cp = cp_j_kgk

    def step(
        self, return_temp_c: float, secondary_flow_m3_s: float, valve_pct: float
    ) -> CDUExchange:
        primary_flow = self.cfg["primary_max_flow_m3_s"] * max(0.0, min(1.0, valve_pct / 100.0))
        return exchange(
            return_temp_c,
            self.cfg["primary_inlet_temp_c"],
            secondary_flow_m3_s * self.rho,
            primary_flow * self.rho,
            self.cp,
            self.cp,
            self.cfg["ua_clean_w_k"] * self.cfg["fouling_factor"],
        )
