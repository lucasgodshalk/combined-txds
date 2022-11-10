import numpy as np

class ResidualDetails():
    def __init__(self, residual_contributions, v_len):
        self.residual_contributions = residual_contributions

        self.residuals = np.zeros(v_len)
        for (_, index, value) in residual_contributions:
            self.residuals[index] += value

        self.max_residual = np.amax(np.abs(self.residuals))
        self.max_residual_idx = int(np.argmax(np.abs(self.residuals)))
