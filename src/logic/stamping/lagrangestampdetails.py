from logic.stamping.lagrangesegment import LagrangeSegment, SKIP, ModelEquations
from models.components.bus import Bus
from models.wellknownvariables import Vr_from, Vi_from, Vr_to, Vi_to, Lr_from, Li_from, Lr_to, Li_to

SKIP = SKIP

class LagrangeStampDetails():
    def __init__(self, lsegment: LagrangeSegment, var_map: dict, optimization_enabled: bool, eqn_map: dict = None) -> None:
        self.lsegment = lsegment
        self.optimization_enabled = optimization_enabled

        #The equation map is really the row index lookup, and the variable map is really the column index lookup.
        self._var_map = var_map
        self._var_str_map = {str(x[0]): x[1] for x in var_map.items()}
        if eqn_map == None:
            self._eqn_map = self._var_map
            self._eqn_map_str = self._var_str_map
        else: 
            self._eqn_map = eqn_map
            self._eqn_map_str = {str(x[0]): x[1] for x in eqn_map.items()}
    
    def get_eqn_row_index_str(self, variable_str):
        if self.optimization_enabled:
            return self._eqn_map_str[variable_str]
        else:
            return self._eqn_map_str[self.lsegment.get_duals_corresponding_primal(variable_str)]

    def get_var_col_index_str(self, variable_str):
        return self._var_str_map[variable_str]

    def get_var_col_index(self, variable):
        return self._var_map[variable]

    def get_var_value(self, v, variable):
        return v[self._var_map[variable]]

    def get_lambda_index(self, lambda_index):
        #A bit weird, we have to refer to the lambda as the index of the
        #associated constraint...
        return self._var_map[self.lsegment.duals[lambda_index]]

def build_model_stamp_details(model_eqns: ModelEquations, from_bus: Bus, to_bus: Bus, node_index, optimization_enabled: bool, index_map = None):
    if index_map == None:
        index_map = {}
    index_map[Vr_from] = from_bus.node_Vr
    index_map[Vi_from] = from_bus.node_Vi
    index_map[Lr_from] = from_bus.node_lambda_Vr
    index_map[Li_from] = from_bus.node_lambda_Vi
    index_map[Vr_to] = to_bus.node_Vr
    index_map[Vi_to] = to_bus.node_Vi
    index_map[Lr_to] = to_bus.node_lambda_Vr
    index_map[Li_to] = to_bus.node_lambda_Vi

    for variable in model_eqns.primals:
        if variable not in index_map:
            index_map[variable] = next(node_index)
    
    for dual in model_eqns.duals:
        if dual not in index_map:
            if optimization_enabled:
                index_map[dual] = next(node_index)
            else:
                index_map[dual] = SKIP

    return LagrangeStampDetails(model_eqns, index_map, optimization_enabled)

