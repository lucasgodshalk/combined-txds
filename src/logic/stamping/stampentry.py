from typing import List, Dict
from logic.stamping.matrixbuilder import MatrixBuilder
import numpy as np

#All of the constants and variables that will be used to calculate an expression. The set of parameters
#will be different for each instance of a model, but the shape will be the same.
#If multiple expressions are all derived from the same underlying equation, then
#the expressions can utilize the same set of inputs (because they will share constants and variables).
class ExpressionInput():
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
        variables,
        is_primal_expr: bool,
        is_nr_invariant: bool,
        is_constant_expr: bool,
        tx_factor_index: int
        ):

        self.expression = expression
        self.evalf = evalf
        self.variables = variables
        self.arg_count = len(variables)
        self.is_primal_expr = is_primal_expr
        self.is_nr_invariant = is_nr_invariant
        self.is_constant_expr = is_constant_expr
        self.tx_factor_index = tx_factor_index

        self.variables_key = str(variables)
        self.key = str(expression) + self.variables_key + str(is_primal_expr) + str(is_nr_invariant) + str(is_constant_expr) + str(tx_factor_index)

# Multiple stamp instances exist for every single model instance, based on the number of expressions to compute,
# e.g. each load instance will share the expressions/equations being computed with all other loads, 
# but each will have their own variable values and target location in the Y or J where the result will be placed.
class StampInstance():
    def __init__(
        self,
        expression: StampExpression,
        input: ExpressionInput,
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
        self.inputs: Dict[str, ExpressionInput]
    
    def add_input(self, input: ExpressionInput):
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

    def stamp(self, Y: MatrixBuilder, J, tx_factor):
        args = self.input_builder.build(tx_factor)

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
        self.input_builders = {}
        self.input_builders: Dict[str, InputBuilder]

        stamp_sets = {}
        stamp_sets: Dict[str, StampSet]

        for stamp in stamps:
            if stamp.expression.variables_key not in self.input_builders:
                self.input_builders[stamp.expression.variables_key] = InputBuilder(stamp.expression.variables, self.optimization_enabled)
            self.input_builders[stamp.expression.variables_key].add_input(stamp.input)

            if stamp.expression.key not in self.stamp_sets:
                self.stamp_sets[stamp.expression.key] = StampSet(stamp.expression, self.input_builders[stamp.expression.variables_key])
            
            stamp_sets[stamp.expression.key].add_stamp(stamp)

        self.linear_primals = []
        self.linear_duals = []
        self.nonlinear_primals = []
        self.nonlinear_duals = []

        for stamp_set in stamp_sets.values():
            if stamp_set.expression.is_primal_expr:
                if stamp_set.expression.is_nr_invariant:
                    self.linear_primals.append(stamp_set)
                else:
                    self.linear_duals.append(stamp_set)
            else:
                if stamp_set.expression.is_nr_invariant:
                    self.nonlinear_primals.append(stamp_set)
                else:
                    self.nonlinear_duals.append(stamp_set)

    def stamp_linear_primal(self, Y: MatrixBuilder, J, v_prev, tx_factor):
        for set in self.linear_primals:
            set.stamp(Y, J, tx_factor)

    def stamp_linear_dual(self, Y: MatrixBuilder, J, v_prev, tx_factor):
        for set in self.linear_duals:
            set.stamp(Y, J, tx_factor)

    def stamp_nonlinear_primal(self, Y: MatrixBuilder, J, v_prev, tx_factor):
        for set in self.nonlinear_primals:
            set.stamp(Y, J, tx_factor)

    def stamp_nonlinear_dual(self, Y: MatrixBuilder, J, v_prev, tx_factor):
        for set in self.nonlinear_duals:
            set.stamp(Y, J, tx_factor)