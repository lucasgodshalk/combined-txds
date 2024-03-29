from typing import List, Dict
import numpy as np
from logic.residualdetails import ResidualDetails
from logic.stamping.lagrangestampdetails import SKIP, LagrangeStampDetails
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.matrixbuilder import MatrixBuilder
from models.wellknownvariables import tx_factor

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

class ResidualExpression():
    def __init__(self, first_order, first_order_str, expr, expr_eval):
        self.first_order = first_order
        self.first_order_str = first_order_str
        self.expr = expr
        self.expr_eval = expr_eval

#A stamp expression is shared across all instances of a model, and constains details about the equation actually being computed.
class StampExpression():
    def __init__(
        self,
        lsegment: LagrangeSegment,
        first_order,
        first_order_str,
        expression,
        evalf,
        yth_variable,
        is_linear: bool,
        tx_factor_index: int,
        is_constant_expr: bool
        ):

        self.lsegment = lsegment
        self.first_order = first_order
        self.first_order_str = first_order_str
        self.expression = expression
        self.evalf = evalf
        self.parameters = lsegment.parameters
        self.param_count = len(self.parameters)
        self.is_linear = is_linear
        self.yth_variable = yth_variable
        self.tx_factor_index = tx_factor_index
        self.is_constant_expr = is_constant_expr

        if is_constant_expr:
            self.yth_variable_str = None
        else:
            self.yth_variable_str = str(yth_variable)

        self.parameters_key = lsegment.parameters_key

        self.key = lsegment.lagrange_key + str(first_order) + str(yth_variable) + str(is_linear) + str(tx_factor_index)

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

class ResidualInstance():
    def __init__(
        self,
        lsegment: LagrangeSegment,
        first_order,
        first_order_str: str,
        row_index: int,
        input: StampInput,
        expr,
        expr_eval
        ):
        
        self.lsegment = lsegment
        self.first_order = first_order
        self.first_order_str = first_order_str
        self.row_index = row_index
        self.input = input
        self.expr = expr
        self.expr_eval = expr_eval

class StampCollection():
    def __init__(self, 
        model,
        lsegment,
        stamps: List[StampInstance], 
        residuals: List[ResidualInstance]
        ):

        self.model = model
        self.lsegment = lsegment
        self.stamps = stamps
        self.residuals = residuals


def build_matrix_stamper(network):
    stamps = []
    for element in network.get_all_elements():
        stamps += element.get_stamps()
    
    if network.optimization != None:
        stamps += network.optimization.get_stamps()

    return MatrixStamper(stamps, network.optimization != None)

def build_stamps_from_stampers(model, *args):
    stamps = []
    for (stamper, constantvals) in args:
        if stamper == None:
            continue
        stamps.append(__build_stampcollection_from_stamper(model, stamper, constantvals))
    
    return stamps

def build_stamps_from_stamper(model, stamper: LagrangeStampDetails, constant_vals):
    return [__build_stampcollection_from_stamper(model, stamper, constant_vals)]

lagrange_cache = {}

def get_or_build_stamp_expressions(lsegment: LagrangeSegment, optimization_enabled):
    key = lsegment.lagrange_key + str(optimization_enabled)

    if key in lagrange_cache:
        return lagrange_cache[key]

    residual_exprs = []
    residual_exprs: List[ResidualExpression]
    stamp_exprs = []
    stamp_exprs: List[StampExpression]
    if optimization_enabled:
        first_order_variables = lsegment.variables
    else:
        first_order_variables = lsegment.duals

    for first_order in first_order_variables:
        derivative = lsegment.get_derivatives()[first_order]

        residual_exprs.append(ResidualExpression(derivative.variable, derivative.variable_str, derivative.expr, derivative.expr_eval))

        for entry in derivative.get_evals():
            expression = StampExpression(
                lsegment,
                derivative.variable,
                derivative.variable_str,
                entry.expr,
                entry.func,
                entry.yth_variable,
                entry.is_linear,
                lsegment.tx_factor_index,
                entry.is_constant_expr
                )
            
            stamp_exprs.append(expression)
    
    lagrange_cache[key] = (stamp_exprs, residual_exprs)
    
    return stamp_exprs, residual_exprs

def __build_stampcollection_from_stamper(model, stamper: LagrangeStampDetails, constant_vals):
    primal_indexes = [stamper.get_var_col_index(primal) for primal in stamper.lsegment.primals]
    dual_indexes = [stamper.get_var_col_index(dual) for dual in stamper.lsegment.duals]

    stamp_exprs, residuals_exprs = get_or_build_stamp_expressions(stamper.lsegment, stamper.optimization_enabled)

    input = StampInput(constant_vals, primal_indexes, dual_indexes)

    stamps = __build_stamps(stamper, stamp_exprs, input)

    residuals = __build_residuals(stamper, residuals_exprs, input)

    return StampCollection(model, stamper.lsegment, stamps, residuals)

def __build_stamps(stamper: LagrangeStampDetails, expressions: List[StampExpression], input: StampInput):
    stamps = []
    for expression in expressions:
        row_index = stamper.get_eqn_row_index_str(expression.first_order_str)
        if row_index == SKIP:
            continue
        
        if expression.is_constant_expr:
            col_index = None
        else:
            col_index = stamper.get_var_col_index_str(expression.yth_variable_str)
            if col_index == SKIP:
                continue

        stamp = StampInstance(
            expression,
            input,
            row_index,
            col_index
            )
        
        stamps.append(stamp)
    
    return stamps


def __build_residuals(stamper: LagrangeStampDetails, residual_exprs: List[ResidualExpression], input: StampInput):
    residuals = []
    for residual_expr in residual_exprs:
        row_index = stamper.get_eqn_row_index_str(residual_expr.first_order_str)
        if row_index == SKIP:
            continue
        residual = ResidualInstance(
            stamper.lsegment, 
            residual_expr.first_order, 
            residual_expr.first_order_str, 
            row_index, 
            input, 
            residual_expr.expr, 
            residual_expr.expr_eval
            )
        residuals.append(residual)

    return residuals

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

        # We utilize this to know if we actually need to update our previous iteration information.
        self.iteration_num = -1
    
    def add_input(self, input: StampInput):
        if input.key not in self.inputs:
            self.input_indexes.append(input.key)
            self.inputs[input.key] = (input, len(self.input_indexes) - 1)
        
        return self.inputs[input.key][1]

    def freeze_inputs(self):
        #Somewhat counter-intuitively, the row is the argument index
        #and the column is the stamp instance's index.
        self.args = [np.zeros(len(self.inputs)) for x in range(self.arg_count)]
        self.input_fills = []

        instance_idx = 0
        for input_key in self.input_indexes:
            input, _ = self.inputs[input_key]
            arg_index = 0

            for constant_val in input.constant_vals:
                self.args[arg_index][instance_idx] = constant_val
                arg_index += 1
            
            #The row and column to use for the input array, not to be confused with the row and column of the Y matrix
            for v_idx in input.primal_indexes:
                if v_idx != None:
                    self.input_fills.append((arg_index, instance_idx, v_idx))
                arg_index += 1

            for v_idx in input.dual_indexes:
                if v_idx != None:
                    if self.optimization_enabled:
                        self.input_fills.append((arg_index, instance_idx, v_idx))
                    else:
                        self.args[arg_index][instance_idx] = None
                arg_index += 1
            
            if arg_index != self.arg_count:
                raise Exception("Length mismatch in parameter inputs for stamp")
                
            instance_idx += 1

    def update_vprev(self, v_prev, iteration_num):
        if iteration_num == self.iteration_num:
            return
        
        for arg_index, instance_idx, v_idx in self.input_fills:
            self.args[arg_index][instance_idx] = v_prev[v_idx]
            
        self.iteration_num = iteration_num
        
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

    def add_stamp(self, stamp: StampInstance):
        output_index = self.input_builder.add_input(stamp.input)
        self.stamps.append((stamp, stamp.row_index, stamp.col_index, output_index))

    def stamp(self, Y: MatrixBuilder, J):
        args = self.input_builder.get_args()

        output_v = self.expression.evalf(*args)
        if type(output_v) != np.ndarray:
            output_v = np.full(args[0].shape[0], output_v)

        if self.expression.yth_variable == None:
            for _, row_idx, _, output_idx in self.stamps:
                J[row_idx] += output_v[output_idx]
        else:
            for _, row_idx, col_idx, output_idx in self.stamps:
                Y.stamp(row_idx, col_idx, output_v[output_idx])

class ResidualSet():
    def __init__(self, residual_expr, residual_eval, input_builder: InputBuilder) -> None:
        self.residual_expr = residual_expr
        self.residual_eval = residual_eval
        self.input_builder = input_builder

        self.residuals = []
    
    def add_residual(self, model, residual: ResidualInstance):
        output_index = self.input_builder.add_input(residual.input)
        self.residuals.append((model, residual, output_index))

    def calc_residuals(self):
        args = self.input_builder.get_args()

        output_v = self.residual_eval(*args)
        if type(output_v) != np.ndarray:
            output_v = np.full(args[0].shape[0], output_v)

        for model, residual, output_index in self.residuals:
            yield (model, residual.row_index, output_v[output_index])

class MatrixStamper():
    def __init__(
        self,
        stampcollections: List[StampCollection],
        optimization_enabled: bool
        ):

        self.optimization_enabled = optimization_enabled

        input_builders = {}
        input_builders: Dict[str, InputBuilder]

        stamp_sets = {}
        stamp_sets: Dict[str, StampSet]

        residual_sets = {}
        residual_sets: Dict[str, ResidualSet]

        for stampcollection in stampcollections:
            for stamp in stampcollection.stamps:
                if stamp.expression.parameters_key not in input_builders:
                    input_builders[stamp.expression.parameters_key] = InputBuilder(stamp.expression.parameters, stamp.expression.tx_factor_index, self.optimization_enabled)

                if stamp.expression.key not in stamp_sets:
                    stamp_sets[stamp.expression.key] = StampSet(stamp.expression, input_builders[stamp.expression.parameters_key])
                
                stamp_sets[stamp.expression.key].add_stamp(stamp)

            for residual in stampcollection.residuals:
                residual_key = residual.lsegment.lagrange_key + residual.first_order_str
                if not residual_key in residual_sets:
                    derivative = residual.lsegment.get_derivatives()[residual.first_order]
                    residual_sets[residual_key] = ResidualSet(
                        derivative.expr,
                        derivative.expr_eval,
                        input_builders[stamp.expression.parameters_key]
                        )
                
                residual_sets[residual_key].add_residual(stampcollection.model, residual)

        for input_builder in input_builders.values():
            input_builder.freeze_inputs()

        self.input_builders = input_builders.values()
        self.linear_sets = []
        self.linear_sets: List[StampSet]
        self.nonlinear_sets = []
        self.nonlinear_sets: List[StampSet]

        for stamp_set in stamp_sets.values():
            if stamp_set.expression.is_linear:
                self.linear_sets.append(stamp_set)
            else:
                self.nonlinear_sets.append(stamp_set)
        
        self.residual_sets = list(residual_sets.values())
        self.residual_sets: List[ResidualSet]

    def stamp_linear(self, Y: MatrixBuilder, J, tx_factor):
        for input_builder in self.input_builders:
            input_builder.update_txfactor(tx_factor)

        for stamp_set in self.linear_sets:
            stamp_set.stamp(Y, J)

    def stamp_nonlinear(self, Y: MatrixBuilder, J, v_prev, iteration_num):
        for input_builder in self.input_builders:
            input_builder.update_vprev(v_prev, iteration_num)
        
        for stamp_set in self.nonlinear_sets:
            stamp_set.stamp(Y, J)

    def __calc_residuals_iter(self, tx_factor, v_result, iteration_num):
        for input_builder in self.input_builders:
            input_builder.update_vprev(v_result, iteration_num)
        
        for input_builder in self.input_builders:
            input_builder.update_txfactor(tx_factor)
        
        for residual_set in self.residual_sets:
            for contribution in residual_set.calc_residuals():
                yield contribution

    def calc_residuals(self, tx_factor, v_result, iteration_num):
        residual_contributions = []
        for contribution in self.__calc_residuals_iter(tx_factor, v_result, iteration_num):
            residual_contributions.append(contribution)
        
        return ResidualDetails(residual_contributions, len(v_result))