from collections import defaultdict
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.matrixbuilder import MatrixBuilder

SKIP = None

class LagrangeStamper:
    def __init__(self, lsegment: LagrangeSegment, var_map: dict, optimization_enabled: bool, eqn_map: dict = None) -> None:
        self.lsegment = lsegment

        #The equation map is really the row index lookup, and the variable map is really the column index lookup.
        self.var_map = var_map
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

    def calc_residuals(self, constant_vals, v_result):
        residuals = defaultdict(lambda: 0)

        primal_vals, dual_vals = self.__extract_kth_primals_duals(v_result)
        args = constant_vals + primal_vals + dual_vals

        for dual in self.lsegment.duals:
            derivative = self.lsegment.get_derivatives()[dual]
            row_idx = self.get_variable_row_index(dual)
            if row_idx == SKIP:
                continue
            residuals[row_idx] += derivative.expr_eval(*args)

        if self.optimization_enabled:
            for primal in self.lsegment.primals:
                derivative = self.lsegment.get_derivatives()[primal]
                row_idx = self.get_variable_row_index(primal)
                if row_idx == SKIP:
                    continue
                residuals[row_idx] += derivative.expr_eval(*args)

        return residuals

    def __extract_kth_primals_duals(self, v_prev):
        if v_prev is None:
            return (self.empty_primals, self.empty_duals)

        primal_vals = []
        for primal in self.lsegment.primals:
            index = self.var_map[primal]
            if index == SKIP:
                primal_vals.append(0)
            else:
                primal_vals.append(v_prev[index])

        if self.optimization_enabled:
            dual_vals = []
            for dual in self.lsegment.duals:
                index = self.var_map[dual]
                if index == SKIP:
                    dual_vals.append(0)
                else:
                    dual_vals.append(v_prev[index])
        else:
            dual_vals = self.empty_duals

        return (primal_vals, dual_vals)
    
