class DCGMSource:
    """Future adapter boundary. Importing DCGM is intentionally deferred."""

    def next_step(self, t_s: float):
        raise NotImplementedError("DCGM integration is scheduled after V0.1 model validation")
