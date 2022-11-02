from typing import List, Dict
import numpy as np
from logic.stamping.lagrangestamper import SKIP, LagrangeStamper
from logic.stamping.matrixbuilder import MatrixBuilder
from models.wellknownvariables import tx_factor

def build_stamp_instances(stamper: LagrangeStamper, constant_vals):
    stamps = []

    primal_indexes = []
    for primal in stamper.lsegment.primals:
        primal_indexes.append(stamper.var_map[primal])

    dual_indexes = []
    for dual in stamper.lsegment.duals:
        dual_indexes.append(stamper.var_map[dual])

    input = StampInput(constant_vals, primal_indexes, dual_indexes)

    for derivative in stamper.lsegment.get_derivatives().values():
        for (variable, func, expr) in derivative.get_evals():

            expression = StampExpression(
                expr,
                func,
                stamper.lsegment.parameters,
                derivative.variable in stamper.lsegment.primals,
                any([(x in expr.free_symbols) for x in stamper.lsegment.variables]),
                variable == None,
                tx_factor in stamper.lsegment.constants
                )

            stamp = StampInstance(
                expression,
                input,
                stamper.get_variable_row_index(derivative.variable),
                stamper.var_map[variable]
                )
            
            stamps.append(stamp)
        
    return stamps

#All of the constants and variables that will be used to calculate a stamp. The set of parameters
#will be different for each instance of a model, but the shape will be the same based on the expression.
#If multiple expressions are all derived from the same underlying equation, then
#the expressions can utilize the same set of inputs (because they will share constants and variables).
class StampInput():
    def __init__(
        self,
        constant_vals: List,
        primal_indexes: List[int],
        dual_indexes: List[int]
        ):

        #Inputs are assumed to be ordered as: constants | primals | duals in list order supplied.
        self.constant_vals = constant_vals
        self.primal_indexes = primal_indexes
        self.dual_indexes = dual_indexes
        
        self.key = str(constant_vals) + str(primal_indexes) + str(dual_indexes)

#A stamp expression is shared across all instances of a model, and constains details about the equation actually being computed.
class StampExpression():
    def __init__(
        self,
        expression,
        evalf,
        parameters,
        is_primal_expr: bool,
        is_linear: bool,
        is_constant_expr: bool,
        tx_factor_index: int
        ):

        self.expression = expression
        self.evalf = evalf
        self.parameters = parameters
        self.param_count = len(parameters)
        self.is_primal_expr = is_primal_expr
        self.is_linear = is_linear
        self.is_constant_expr = is_constant_expr
        self.tx_factor_index = tx_factor_index

        self.parameters_key = str(parameters)
        self.key = str(expression) + self.parameters_key + str(is_primal_expr) + str(is_linear) + str(is_constant_expr) + str(tx_factor_index)

# Multiple stamp instances exist for every single model instance, based on the number of expressions to compute,
# e.g. each load instance will share the expressions/equations being computed with all other loads, 
# but each will have their own variable values and target location in the Y or J where the result will be placed.
class StampInstance():
    def __init__(
        self,
        expression: StampExpression,
        input: StampInput,
        row_index: int,
        col_index: int
        ):

        self.expression = expression
        self.input = input
        self.row_index = row_index
        #Column index will be ignored if the expression gets put in the J vector.
        self.col_index = col_index

#Constructs the input matrix for a particular expression based on the set of stamp inputs.
class InputBuilder():
    def __init__(
        self, 
        variables: int,
        tx_factor_index: int,
        optimization_enabled: bool
        ):
        
        self.variables = variables
        self.tx_factor_index = tx_factor_index
        self.optimization_enabled = optimization_enabled

        self.arg_count = len(variables)

        self.inputs = {}
        self.inputs: Dict[str, StampInput]
    
    def add_input(self, input: StampInput):
        if input.key not in self.inputs:
            self.inputs[input.key] = input

    def load_input(self):
        self.arg_matrix = np.zeros((len(self.inputs), self.arg_count))
        self.input_fills = []

        for input_row in range(len(self.inputs)):
            input = self.inputs[input_row]

            input_col = 0

            for constant_val in input.constant_vals:
                self.arg_matrix[input_row, input_col] = constant_val

                input_col += 1
            
            #The row and column to use for the input array, not to be confused with the row and column of the Y matrix
            for v_idx in input.primal_indexes:
                self.input_fills.append((input_row, input_col, v_idx))
                input_col += 1

            for v_idx in input.dual_indexes:
                if self.optimization_enabled:
                    self.input_fills.append((input_row, input_col, v_idx))
                else:
                    self.arg_matrix[input_row, input_col] = None
                input_col += 1
            
            self.input_fills = [x for x in self.input_fills if (SKIP not in x)]

            if input_col + 1 != self.arg_count:
                raise Exception("Length mismatch in parameter inputs for stamp")
        
    def build(self, v_prev, tx_factor):
        for input_row, input_col, v_idx in self.input_fills:
            self.arg_matrix[input_row, input_col] = v_prev[v_idx]
        
        if self.tx_factor_index != None:
            self.arg_matrix[:, self.tx_factor_index] = tx_factor

        return self.arg_matrix

#Responsible for stamping a set of stamp instances that share an expression
class StampSet():
    def __init__(
        self, 
        expression: StampExpression, 
        input_builder: InputBuilder
        ):

        self.expression = expression
        self.input_builder = input_builder

        self.stamps = []
        self.stamps: List[StampInstance]

        self.output_indexes = []

    def add_stamp(self, stamp: StampInstance):
        self.stamps.append(stamp)
        
        self.output_indexes.append((stamp.row_index, stamp.col_index))

    def stamp(self, Y: MatrixBuilder, J, v_prev, tx_factor):
        args = self.input_builder.build(v_prev, tx_factor)

        output_v = self.expression.evalf(args)

        if self.expression.is_constant_expr:
            for i in range(len(self.output_indexes)):
                (row_idx, _) = self.output_indexes[i]
                J[row_idx] += output_v[i]
        else:
            for i in range(len(self.output_indexes)):
                (row_idx, col_idx) = self.output_indexes[i]
                Y.stamp(row_idx, col_idx, output_v[i])

class MatrixStamper():
    def __init__(
        self,
        optimization_enabled: bool
        ):

        self.optimization_enabled = optimization_enabled

    def register_stamps(self, stamps: List[StampInstance]):
        input_builders = {}
        input_builders: Dict[str, InputBuilder]

        stamp_sets = {}
        stamp_sets: Dict[str, StampSet]

        for stamp in stamps:
            if stamp.expression.parameters_key not in input_builders:
                self.input_builders[stamp.expression.parameters_key] = InputBuilder(stamp.expression.parameters, self.optimization_enabled)
            self.input_builders[stamp.expression.parameters_key].add_input(stamp.input)

            if stamp.expression.key not in self.stamp_sets:
                self.stamp_sets[stamp.expression.key] = StampSet(stamp.expression, input_builders[stamp.expression.parameters_key])
            
            stamp_sets[stamp.expression.key].add_stamp(stamp)

        self.linear_sets = []
        self.nonlinear_sets = []

        for stamp_set in stamp_sets.values():
            if stamp_set.expression.is_linear:
                if self.optimization_enabled or stamp_set.expression.is_primal_expr:
                    self.linear_sets.append(stamp_set)
            else:
                if self.optimization_enabled or stamp_set.expression.is_primal_expr:
                    self.nonlinear_sets.append(stamp_set)

    def stamp_linear(self, Y: MatrixBuilder, J, v_prev, tx_factor):
        for stamp_set in self.linear_sets:
            stamp_set.stamp(Y, J, v_prev, tx_factor)

    def stamp_nonlinear(self, Y: MatrixBuilder, J, v_prev, tx_factor):
        for stamp_set in self.nonlinear_sets:
            stamp_set.stamp(Y, J, v_prev, tx_factor)
