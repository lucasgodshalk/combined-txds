from logic.lagrangehandler import LagrangeHandler
from logic.matrixbuilder import MatrixBuilder

class StampEntry:
    def __init__(self, row_index, col_index, eval_func) -> None:
        self.row_index = row_index
        self.col_index = col_index
        self.eval_func = eval_func

class LagrangeStamper:
    def __init__(self, handler: LagrangeHandler, index_map: dict) -> None:
        self.handler = handler
        self.index_map = index_map

        self.empty_primals = [None] * len(self.handler.primals)
        self.empty_duals = [None] * len(self.handler.duals)

        self.primal_components = self.build_component_set(self.handler.primals)
        self.dual_components = self.build_component_set(self.handler.duals)

    def build_component_set(self, variables):
        components = []
        for row_var in variables:
            entry = self.handler.derivatives[row_var]

            for (yth_variable, eval) in entry.get_evals():
                if yth_variable == None:
                    components.append((self.index_map[row_var], None, eval))
                else:
                    components.append((self.index_map[row_var], self.index_map[yth_variable], eval))
        
        return components
    
    def stamp_primal(self, Y: MatrixBuilder, J, constant_vals, v_prev):
        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_prev)
        args = constant_vals + primal_vals + dual_vals
        self.__stamp_set(Y, J, self.primal_components, args)

    def stamp_dual(self, Y: MatrixBuilder, J, constant_vals, v_prev):
        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_prev)
        args = constant_vals + primal_vals + dual_vals
        self.__stamp_set(Y, J, self.dual_components, args)
    
    def __extract_kth_primals_duals(self, v_prev):
        if v_prev is None:
            return (self.empty_primals, self.empty_duals)

        primal_vals = []
        for primal in self.handler.primals:
            primal_vals.append(v_prev[self.index_map[primal]])

        dual_vals = []
        for dual in self.handler.duals:
            dual_vals.append(v_prev[self.index_map[dual]])

        return (primal_vals, dual_vals)

    def __stamp_set(self, Y: MatrixBuilder, J, components, args):
        for (row_index, col_index, eval_func) in components:
            if col_index == None:
                J[row_index] += eval_func(*args)
            else:
                Y.stamp(row_index, col_index, eval_func(*args))