from collections import defaultdict
import typing
from sympy import Add, diff, lambdify, expand, Pow, Symbol
from logic.stamping.lagrangepickler import LagrangePickler

def is_constant(expr, vars):
    for symbol in expr.free_symbols:
        if symbol in vars:
            return False
    return True

def is_linear(expr, vars):
    if is_constant(expr, vars):
        return False

    var_found = False
    for symbol in expr.free_symbols:
        if symbol in vars:
            if var_found:
                return False
            elif len(expr.atoms(Pow)) > 0:
                return False
            var_found = True
    return True 

def get_linear_term(expr, vars):
    if not is_linear(expr, vars):
        raise Exception("Expression is not linear")

    result = None
    for symbol in expr.free_symbols:
        if symbol in vars:
            result = symbol
    return result

def linearize_expr(expr, variables):
    kth_sum = -expr
    Y_components = {}

    for variable in variables:
        derivative = diff(expr, variable) 
        Y_components[variable] = derivative
        kth_sum += derivative * variable
    
    return (kth_sum, Y_components)

def split_expr(eqn, vars):
    eqn = expand(eqn)

    constant_expr = 0
    variable_expr_dict = {}

    if isinstance(eqn, Add):
        expressions = eqn.args
    else:
        expressions = [eqn]

    for expr in expressions:
        if is_constant(expr, vars):
            constant_expr += -expr
        elif is_linear(expr, vars):
            term = get_linear_term(expr, vars)
            if not term in variable_expr_dict:
                variable_expr_dict[term] = 0
            variable_expr_dict[term] += diff(expr, term)
        else:
            (J_expr, Y_expr_dict) =  linearize_expr(expr, vars)

            constant_expr += J_expr
            for key, value in Y_expr_dict.items():
                if not key in variable_expr_dict:
                    variable_expr_dict[key] = 0
                variable_expr_dict[key] += value
    
    return (constant_expr, variable_expr_dict)

class DerivativeEntry:
    def __init__(self, variable, expr, constant_expr, variable_exprs, lambda_inputs) -> None:
        self.variable = variable
        self.expr = expr
        
        #The constant expression will end up in the J vector
        self.constant_expr = constant_expr
        #Any variable expressions will end up in the Y matrix, based on the variable the expression is for.
        self.variable_exprs = variable_exprs

        #All variables that need to be supplied to the evaluation functions. We assume all expressions take the same inputs.
        self.lambda_inputs = lambda_inputs

        self.eqn_eval = lambdify(self.lambda_inputs, self.expr)
        self.constant_eval = lambdify(self.lambda_inputs, self.constant_expr)
        self.variable_evals = {}
        for var, variable_eqn in self.variable_exprs.items():
            if variable_eqn != 0:
                self.variable_evals[var] = lambdify(self.lambda_inputs, variable_eqn)

    def get_evals(self):
        if self.constant_expr != 0:
            yield (None, self.constant_eval, self.constant_expr)

        for (variable, func) in self.variable_evals.items():
            yield(variable, func, self.variable_exprs[variable])

    def __repr__(self) -> str:
        return f"Entry {self.variable}: {self.expr}"

#This class manages individual segments of the lagrange equation that is supplied by different models.
#You can think of all the segments as summing together to make the full Lagrange equation,
#but in reality we map individual segments straight onto the matrix (see: LagrangeStamper)
class LagrangeSegment:
    VERSION = 1 #Increment if changes have been made to bust the derivative cache.
    _pickler = LagrangePickler()

    def __init__(self, lagrange, constant_symbols, primal_symbols, dual_symbols) -> None:
        self.lagrange = lagrange
        self.constants = constant_symbols
        self.primals = primal_symbols
        self.duals = dual_symbols
        self.lagrange_key = f"{LagrangeSegment.VERSION},{lagrange},{constant_symbols},{primal_symbols},{dual_symbols}"

        self.variables = self.primals + self.duals

        self._derivatives = None
        self._derivatives: typing.Dict[Symbol, DerivativeEntry]

    def get_derivatives(self):
        if self._derivatives != None:
            return self._derivatives

        if LagrangeSegment._pickler.has_pickle(self.lagrange_key):
            try:
                self._derivatives = LagrangeSegment._pickler.try_unpickle(self.lagrange_key)
            except:
                self._generate_derivatives()
        else:
            self._generate_derivatives()

        return self._derivatives
    
    def _generate_derivatives(self):
        self._derivatives = {}

        lambda_inputs = self.constants + self.variables

        for first_order in self.variables:
            derivative = diff(self.lagrange, first_order)

            constant_expr, variable_exprs = split_expr(derivative, self.variables)

            self._derivatives[first_order] = DerivativeEntry(first_order, derivative, constant_expr, variable_exprs, lambda_inputs)

        LagrangeSegment._pickler.try_pickle(self.lagrange_key, self._derivatives)

