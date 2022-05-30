from anoeds.models.edge import Edge

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

        ##### TODO choose correct representation #####

    # def stamp_primal(self, Y, J, v_previous, tx_factor, state):
    #     pass