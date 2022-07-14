from collections import defaultdict
from logic.lagrangehandler import LagrangeHandler
from logic.matrixbuilder import MatrixBuilder

SKIP = None

class StampEntry:
    def __init__(self, row_index, col_index, eval_func) -> None:
        self.row_index = row_index
        self.col_index = col_index
        self.eval_func = eval_func

class LagrangeStamper:
    def __init__(self, handler: LagrangeHandler, index_map: dict, optimization_enabled: bool) -> None:
        self.handler = handler
        self.index_map = index_map
        self.optimization_enabled = optimization_enabled

        self.empty_primals = [None] * len(self.handler.primals)
        self.empty_duals = [None] * len(self.handler.duals)

        #The 'primal' contributions are really the first derivative of the dual variables.
        self.primal_components = self.build_component_set(self.handler.duals)

        if self.optimization_enabled:
            self.dual_components = self.build_component_set(self.handler.primals)

    def build_component_set(self, variables):
        components = []
        for variable in variables:
            row_index = self.get_variable_row_index(variable)
            if row_index == SKIP:
                continue

            entry = self.handler.derivatives[variable]

            for (yth_variable, eval, expr) in entry.get_evals():

                if yth_variable == None:
                    components.append((row_index, None, eval, expr))
                else:
                    col_index = self.index_map[yth_variable]
                    if col_index == SKIP:
                        continue
                    components.append((row_index, col_index, eval, expr))
        
        return components
    
    def get_variable_row_index(self, variable):
        if self.optimization_enabled:
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
        residuals = defaultdict(lambda: 0)

        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_result)
        args = constant_vals + primal_vals + dual_vals

        for dual in self.handler.duals:
            derivative = self.handler.derivatives[dual]
            row_idx = self.get_variable_row_index(dual)
            if row_idx == SKIP:
                continue
            residuals[row_idx] += derivative.derivative_eval(*args)

        if self.optimization_enabled:
            for primal in self.handler.primals:
                derivative = self.handler.derivatives[primal]
                row_idx = self.get_variable_row_index(primal)
                if row_idx == SKIP:
                    continue
                residuals[row_idx] += derivative.derivative_eval(*args)

        return residuals

    def __extract_kth_primals_duals(self, v_prev):
        if v_prev is None:
            return (self.empty_primals, self.empty_duals)

        primal_vals = []
        for primal in self.handler.primals:
            index = self.index_map[primal]
            if index == SKIP:
                primal_vals.append(0)
            else:
                primal_vals.append(v_prev[index])

        if self.optimization_enabled:
            dual_vals = []
            for dual in self.handler.duals:
                dual_vals.append(v_prev[self.index_map[dual]])
        else:
            dual_vals = self.empty_duals

        return (primal_vals, dual_vals)

    def __stamp_set(self, Y: MatrixBuilder, J, components, args):
        for (row_index, col_index, eval_func, _) in components:
            if col_index == None:
                J[row_index] += eval_func(*args)
            else:
                Y.stamp(row_index, col_index, eval_func(*args))

    def stamp_primal_symbols(self, Y: MatrixBuilder, J):
        self.__stamp_symbol_set(Y, J, self.primal_components)

    def stamp_dual_symbols(self, Y: MatrixBuilder, J):
        self.__stamp_symbol_set(Y, J, self.dual_components)

    def __stamp_symbol_set(self, Y: MatrixBuilder, J, components):
        for (row_index, col_index, _, expr) in components:
            if col_index == None:
                J[row_index] += expr
            else:
                Y.stamp(row_index, col_index, expr)