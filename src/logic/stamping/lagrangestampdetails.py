from logic.stamping.lagrangesegment import LagrangeSegment

SKIP = None

class LagrangeStampDetails:
    def __init__(self, lsegment: LagrangeSegment, var_map: dict, optimization_enabled: bool, eqn_map: dict = None) -> None:
        self.lsegment = lsegment

        #The equation map is really the row index lookup, and the variable map is really the column index lookup.
        self.var_map = var_map
        self.var_str_map = {str(x[0]): x[1] for x in var_map.items()}
        if eqn_map == None:
            self.eqn_map = var_map
        else: 
            self.eqn_map = eqn_map

        self.optimization_enabled = optimization_enabled

        self.empty_primals = [None] * len(self.lsegment.primals)
        self.empty_duals = [None] * len(self.lsegment.duals)
    
    def get_variable_row_index(self, variable):
        if self.optimization_enabled:
            return self.eqn_map[variable]
        else:
            #For the optimization disabled case, we can't use the dual variable's index
            #for the matrix row. Instead, we commandeer the index of it's corresponding primal variable.
            return self.eqn_map[self.lsegment.primals[self.lsegment.duals.index(variable)]]
