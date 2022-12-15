from logic.stamping.lagrangesegment import LagrangeSegment, SKIP

SKIP = SKIP

class LagrangeStampDetails:
    def __init__(self, lsegment: LagrangeSegment, var_map: dict, optimization_enabled: bool, eqn_map: dict = None) -> None:
        self.lsegment = lsegment

        #The equation map is really the row index lookup, and the variable map is really the column index lookup.
        self.__var_map = var_map
        self.var_str_map = {str(x[0]): x[1] for x in var_map.items()}
        if eqn_map == None:
            self.__eqn_map = self.__var_map
            self.__eqn_map_str = self.var_str_map
        else: 
            self.__eqn_map = eqn_map
            self.__eqn_map_str = {str(x[0]): x[1] for x in eqn_map.items()}

        self.optimization_enabled = optimization_enabled
    
    def get_eqn_row_index_str(self, variable_str):
        if self.optimization_enabled:
            return self.__eqn_map_str[variable_str]
        else:
            return self.__eqn_map_str[self.lsegment.get_duals_corresponding_primal(variable_str)]

    def get_var_col_index(self, variable):
        return self.__var_map[variable]