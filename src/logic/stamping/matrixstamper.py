from typing import List, Dict
import numpy as np
from logic.stamping.lagrangestamper import SKIP, LagrangeStamper
from logic.stamping.matrixbuilder import MatrixBuilder
from models.wellknownvariables import tx_factor

def build_stamps_from_stampers(*args):
    stamps = []
    for (stamper, constantvals) in args:
        stamps += build_stamps_from_stamper(stamper, constantvals)
    
    return stamps

def build_stamps_from_stamper(stamper: LagrangeStamper, constant_vals):
    stamps = []

    primal_indexes = []
    for primal in stamper.lsegment.primals:
        primal_indexes.append(stamper.var_map[primal])

    dual_indexes = []
    for dual in stamper.lsegment.duals:
        dual_indexes.append(stamper.var_map[dual])

    input = StampInput(constant_vals, primal_indexes, dual_indexes)

    if stamper.optimization_enabled:
        first_order_variables = stamper.lsegment.variables
    else:
        first_order_variables = stamper.lsegment.duals

    for variable in first_order_variables:

        row_index = stamper.get_variable_row_index(variable)
        if row_index == SKIP:
            continue

        derivative = stamper.lsegment.get_derivatives()[variable]

        for (yth_variable, func, expr) in derivative.get_evals():
            if yth_variable == None:
                col_index = None
            else:
                col_index = stamper.var_map[yth_variable]
                if col_index == SKIP:
                    continue

            is_linear = not any([(x in expr.free_symbols) for x in stamper.lsegment.variables])
            tx_factor_index = stamper.lsegment.constants.index(tx_factor) if tx_factor in stamper.lsegment.constants else SKIP

            expression = StampExpression(
                expr,
                func,
                stamper.lsegment.parameters,
                is_linear,
                yth_variable == None,
                tx_factor_index
                )

            stamp = StampInstance(
                expression,
                input,
                row_index,
                col_index
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
        is_linear: bool,
        is_constant_expr: bool,
        tx_factor_index: int
        ):

        self.expression = expression
        self.evalf = evalf
        self.parameters = parameters
        self.param_count = len(parameters)
        self.is_linear = is_linear
        self.is_constant_expr = is_constant_expr
        self.tx_factor_index = tx_factor_index

        self.parameters_key = str(parameters)
        self.key = str(expression) + self.parameters_key + str(is_linear) + str(is_constant_expr) + str(tx_factor_index)

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
        variables,
        tx_factor_index: int,
        optimization_enabled: bool
        ):
        
        self.variables = variables
        self.tx_factor_index = tx_factor_index
        self.optimization_enabled = optimization_enabled

        self.arg_count = len(variables)

        self.inputs = {}
        self.inputs: Dict[str, StampInput]

        self.input_indexes = []
    
    def add_input(self, input: StampInput):
        if input.key not in self.inputs:
            self.inputs[input.key] = input
            self.input_indexes.append(input.key)
        
        return self.input_indexes.index(input.key)

    def freeze_inputs(self, is_linear_only: bool):
        #Somewhat counter-intuitively, the row is the argument index
        #and the column is the stamp instance's index.
        self.args = [np.zeros(len(self.inputs)) for x in range(self.arg_count)]
        self.input_fills = []

        instance_idx = 0
        for input_key in self.input_indexes:
            input = self.inputs[input_key]
            arg_index = 0

            for constant_val in input.constant_vals:
                self.args[arg_index][instance_idx] = constant_val
                arg_index += 1
            
            #If the inputs are only used for linear expressions, then we don't need to touch it at all
            #after the the inputs are formed during the linear step.
            if not is_linear_only:
                #The row and column to use for the input array, not to be confused with the row and column of the Y matrix
                for v_idx in input.primal_indexes:
                    self.input_fills.append((arg_index, instance_idx, v_idx))
                    arg_index += 1

                for v_idx in input.dual_indexes:
                    if self.optimization_enabled:
                        self.input_fills.append((arg_index, instance_idx, v_idx))
                    else:
                        self.args[arg_index][instance_idx] = None
                    arg_index += 1
                
                self.input_fills = [x for x in self.input_fills if (SKIP not in x)]

                if arg_index != self.arg_count:
                    raise Exception("Length mismatch in parameter inputs for stamp")
                
            instance_idx += 1

    def update_vprev(self, v_prev):
        for arg_index, instance_idx, v_idx in self.input_fills:
            self.args[arg_index][instance_idx] = v_prev[v_idx]
        
    def update_txfactor(self, tx_factor):
        if self.tx_factor_index != SKIP:
            self.args[self.tx_factor_index][:] = tx_factor

    def get_args(self):
        return self.args

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
        self.stamps: List[(StampInstance, int, int, int)]

    def add_stamp(self, stamp: StampInstance, output_index: int):
        self.stamps.append((stamp, stamp.row_index, stamp.col_index, output_index))

    def stamp(self, Y: MatrixBuilder, J):
        args = self.input_builder.get_args()

        output_v = self.expression.evalf(*args)
        if type(output_v) != np.ndarray:
            output_v = np.full(args[0].shape[0], output_v)

        if self.expression.is_constant_expr:
            for _, row_idx, _, output_idx in self.stamps:
                J[row_idx] += output_v[output_idx]
        else:
            for _, row_idx, col_idx, output_idx in self.stamps:
                Y.stamp(row_idx, col_idx, output_v[output_idx])

class MatrixStamper():
    def __init__(
        self,
        optimization_enabled: bool
        ):

        self.optimization_enabled = optimization_enabled

    def register_stamps(self, stamps: List[StampInstance]):
        input_builders = {}
        input_builders: Dict[str, InputBuilder]

        nonlinear_inputs = set()

        stamp_sets = {}
        stamp_sets: Dict[str, StampSet]

        for stamp in stamps:
            if stamp.expression.parameters_key not in input_builders:
                input_builders[stamp.expression.parameters_key] = InputBuilder(stamp.expression.parameters, stamp.expression.tx_factor_index, self.optimization_enabled)
            output_index = input_builders[stamp.expression.parameters_key].add_input(stamp.input)

            if not stamp.expression.is_linear:
                nonlinear_inputs.add(stamp.expression.parameters_key)

            if stamp.expression.key not in stamp_sets:
                stamp_sets[stamp.expression.key] = StampSet(stamp.expression, input_builders[stamp.expression.parameters_key])
            
            stamp_sets[stamp.expression.key].add_stamp(stamp, output_index)

        for key, input_builder in input_builders.items():
            input_builder.freeze_inputs(key not in nonlinear_inputs)

        self.input_builders = input_builders.values()
        self.linear_sets = []
        self.nonlinear_sets = []

        for stamp_set in stamp_sets.values():
            if stamp_set.expression.is_linear:
                self.linear_sets.append(stamp_set)
            else:
                self.nonlinear_sets.append(stamp_set)

    def stamp_linear(self, Y: MatrixBuilder, J, tx_factor):
        for input_builder in self.input_builders:
            input_builder.update_txfactor(tx_factor)

        for stamp_set in self.linear_sets:
            stamp_set.stamp(Y, J)

    def stamp_nonlinear(self, Y: MatrixBuilder, J, v_prev):
        for input_builder in self.input_builders:
            input_builder.update_vprev(v_prev)
        
        for stamp_set in self.nonlinear_sets:
            stamp_set.stamp(Y, J,)