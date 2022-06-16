from logic.lagrangehandler import LagrangeHandler
from logic.matrixbuilder import MatrixBuilder

class LagrangeStamper:
    def __init__(self, handler: LagrangeHandler, index_row_map: dict, index_col_map: dict) -> None:
        self.handler = handler
        self.index_row_map = index_row_map
        self.index_col_map = index_col_map
    
    def stamp_primal(self, Y: MatrixBuilder, J, constant_vals, v_prev):
        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_prev)
        derivatives = self.handler.evaluate_primals(constant_vals, primal_vals, dual_vals)
        self.__stamp_set(Y, J, self.handler.duals, derivatives)

    def stamp_dual(self, Y: MatrixBuilder, J, constant_vals, v_prev):
        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_prev)
        derivatives = self.handler.evaluate_duals(constant_vals, primal_vals, dual_vals)
        self.__stamp_set(Y, J, self.handler.primals, derivatives)
    
    def __extract_kth_primals_duals(self, v_prev):
        primal_vals = []
        for primal in self.handler.primals:
            primal_vals.append(v_prev[self.index_col_map[primal]])

        dual_vals = []
        for dual in self.handler.duals:
            dual_vals.append(v_prev[self.index_col_map[dual]])

        return (primal_vals, dual_vals)

    def __stamp_set(self, Y: MatrixBuilder, J, variable_set, derivatives):
        for target_variable in variable_set:
            if self.handler.is_nonlinear:
                J[self.index_row_map[target_variable]] += derivatives[target_variable][0]

                for variable in self.handler.variables:
                    Y.stamp(self.index_row_map[target_variable], self.index_col_map[variable], derivatives[target_variable][1][variable])
            else:
                raise Exception("Not implemented")