from logic.lagrangehandler import LagrangeHandler
from logic.matrixbuilder import MatrixBuilder

class LagrangeStamper:
    def __init__(self, handler: LagrangeHandler, index_row_map: dict, index_col_map: dict) -> None:
        self.handler = handler
        self.index_row_map = index_row_map
        self.index_col_map = index_col_map
    
    def stamp_primal(self, Y: MatrixBuilder, J, constant_vals, v_prev):
        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_prev)
        results = self.handler.evaluate_primals(constant_vals, primal_vals, dual_vals)
        self.__stamp_set(Y, J, results)

    def stamp_dual(self, Y: MatrixBuilder, J, constant_vals, v_prev):
        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_prev)
        results = self.handler.evaluate_duals(constant_vals, primal_vals, dual_vals)
        self.__stamp_set(Y, J, results)
    
    def __extract_kth_primals_duals(self, v_prev):
        if v_prev is None:
            primal_vals = [None] * len(self.handler.primals)
            dual_vals = [None] * len(self.handler.duals)
            return (primal_vals, dual_vals)

        primal_vals = []
        
        for primal in self.handler.primals:
            primal_vals.append(v_prev[self.index_col_map[primal]])

        dual_vals = []
        for dual in self.handler.duals:
            dual_vals.append(v_prev[self.index_col_map[dual]])

        return (primal_vals, dual_vals)

    def __stamp_set(self, Y: MatrixBuilder, J, results):
        for (row_var, column_var, value) in results:
            if column_var == None:
                J[self.index_row_map[row_var]] += value
            else:
                Y.stamp(self.index_row_map[row_var], self.index_col_map[column_var], value)