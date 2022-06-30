from logic.lagrangestamper import SKIP
from models.shared.bus import Bus
from models.threephase.edge import Edge

class TransformerPhaseCoil(Edge):
    
    def __init__(self
                # , secondary_node
                # , to_node
                , phase
                , r = None # compensator r
                , x = None # compensator x
                # , V_primary
                # , V_secondary
                # , I1 # The current which controls
                # , I2 # The current which flows through the node
                , edge_id = None
                ):
        super().__init__(edge_id)
        # self.secondary_node = secondary_node
        # self.to_node = to_node
        self.phase = phase
        self.r = r
        self.x = x
        # self.V = V
        # self.I = I

        self.from_node: Bus
        self.to_node: Bus
        self.secondary_node: Bus

        self.from_node = None
        self.to_node = None
        self.secondary_node = None

        self.real_voltage_idx = -1
        self.imag_voltage_idx = -1

        self.real_lambda_idx = SKIP
        self.imag_lambda_idx = SKIP

        ##### TODO choose correct representation #####

    # def stamp_primal(self, Y, J, v_previous, tx_factor, state):
    #     pass