from logic.lagrangehandler import LagrangeHandler
from logic.matrixbuilder import MatrixBuilder

SKIP = -1

class StampEntry:
    def __init__(self, row_index, col_index, eval_func) -> None:
        self.row_index = row_index
        self.col_index = col_index
        self.eval_func = eval_func

class LagrangeStamper:
    def __init__(self, handler: LagrangeHandler, index_map: dict, optimization_enabled: bool) -> None:
        self.handler = handler
        self.index_map = index_map

        self.empty_primals = [None] * len(self.handler.primals)
        self.empty_duals = [None] * len(self.handler.duals)

        #The 'primal' contributions are really the first derivative of the dual variables.
        self.primal_components = self.build_component_set(self.handler.duals, optimization_enabled)

        if optimization_enabled:
            self.dual_components = self.build_component_set(self.handler.primals, True)

    def build_component_set(self, variables, optimization_enabled):
        components = []
        for variable in variables:
            row_index = self.get_variable_row_index(variable, optimization_enabled)
            entry = self.handler.derivatives[variable]

            for (yth_variable, eval) in entry.get_evals():

                if yth_variable == None:
                    components.append((row_index, None, eval))
                else:
                    col_index = self.index_map[yth_variable]
                    components.append((row_index, col_index, eval))
        
        return components
    
    def get_variable_row_index(self, variable, optimization_enabled):
        if optimization_enabled:
            return self.index_map[variable]
        else:
            #For the optimization enabled case, we can't use the dual variable's index
            #for the matrix row. Instead, we commandeer the index of it's corresponding primal variable.
            return self.index_map[self.handler.primals[self.handler.duals.index(variable)]]

    def stamp_primal(self, Y: MatrixBuilder, J, constant_vals, v_prev):
        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_prev)
        args = constant_vals + primal_vals + dual_vals
        self.__stamp_set(Y, J, self.primal_components, args)

    def stamp_dual(self, Y: MatrixBuilder, J, constant_vals, v_prev):
        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_prev)
        args = constant_vals + primal_vals + dual_vals
        self.__stamp_set(Y, J, self.dual_components, args)

    def calc_residuals(self, constant_vals, v_result):
        residuals = {}

        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_result)
        args = constant_vals + primal_vals + dual_vals

        for (variable, derivative) in self.handler.derivatives.items():
            row_idx = self.index_map[variable]
            residuals[row_idx] = derivative.derivative_eval(*args)

        return residuals

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