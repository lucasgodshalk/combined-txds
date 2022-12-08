from itertools import count
from typing import Dict, List
from sympy import Add, diff, lambdify, expand, Pow, Symbol
from logic.stamping.lagrangepickler import LagrangePickler
from models.wellknownvariables import Lr_from, Li_from, Lr_to, Li_to

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

        self.expr_eval = lambdify(self.lambda_inputs, self.expr, "numpy")
        self.constant_eval = lambdify(self.lambda_inputs, self.constant_expr, "numpy")
        self.variable_evals = {}
        for var, variable_eqn in self.variable_exprs.items():
            if variable_eqn != 0:
                self.variable_evals[var] = lambdify(self.lambda_inputs, variable_eqn, "numpy")

        self.evals = []

        if self.constant_expr != 0:
            self.evals.append((None, self.constant_eval, self.constant_expr, True))

        for (variable, func) in self.variable_evals.items():
            self.evals.append((variable, func, self.variable_exprs[variable], False))

    def get_evals(self):
        return self.evals

    def __repr__(self) -> str:
        return f"Entry {self.variable}: {self.expr}"

#This class manages individual segments of the lagrange equation that is supplied by different models.
#You can think of all the segments as summing together to make the full Lagrange equation,
#but in reality we map individual segments straight onto the matrix (see: LagrangeStamper)
class LagrangeSegment:
    VERSION = 4 #Increment if changes have been made to bust the derivative cache.
    _pickler = LagrangePickler()

    def __init__(self, lagrange, constant_symbols, primal_symbols, dual_symbols):
        self.lagrange = lagrange
        self.constants = tuple(constant_symbols)
        self.primals = tuple(primal_symbols)
        self.duals = tuple(dual_symbols)
        self.lagrange_key = f"{LagrangeSegment.VERSION},{lagrange},{self.constants},{self.primals},{self.duals}"

        self.variables = self.primals + self.duals

        self.parameters = self.constants + self.variables

        self.parameters_key = str(self.parameters)

        self._derivatives = None
        self._derivatives: Dict[Symbol, DerivativeEntry]

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

        for first_order in self.variables:
            derivative = diff(self.lagrange, first_order)

            constant_expr, variable_exprs = split_expr(derivative, self.variables)

            self._derivatives[first_order] = DerivativeEntry(first_order, derivative, constant_expr, variable_exprs, self.parameters)

        LagrangeSegment._pickler.try_pickle(self.lagrange_key, self._derivatives)

#Basic equality constraint for an optimization
class Eq():
    def __init__(self, equality) -> None:
        self.constraint_eqn = equality

#KCL real contribution of a model
class KCL_r(Eq):
    def __init__(self, kcl_r) -> None:
        super().__init__(kcl_r)

#KCL imaginary contribution of a model
class KCL_i(Eq):
    def __init__(self, kcl_i) -> None:
        super().__init__(kcl_i)    

#An objective function for an optimization
class Objective():
    def __init__(self, obj_eqn) -> None:
        self.eqn = obj_eqn

class ModelEquations(LagrangeSegment):
    _ids = count(0)

    def __init__(self, variables: List, constants: List, kcl_r: KCL_r, kcl_i: KCL_i, equalities: List[Eq] = [], objective: Objective = None):
        if kcl_r == None or kcl_i == None:
            raise Exception("KCL real/imginary must be supplied")
        
        self.kcl_r = kcl_r
        self.kcl_i = kcl_i
        self.equalities = equalities
        self.obj = objective

        lambdas = []
        lagrange = 0

        declared_symbols = constants + variables
        
        if objective != None:
            self.check_missing_symbols(declared_symbols, objective.eqn)
            lagrange += objective.eqn

        lambdas.append(Lr_from)
        lagrange += Lr_from * kcl_r.constraint_eqn
        lambdas.append(Li_from)
        lagrange += Li_from * kcl_i.constraint_eqn

        lambdas.append(Lr_to)
        lagrange += Lr_to * -kcl_r.constraint_eqn
        lambdas.append(Li_to)
        lagrange += Li_to * -kcl_i.constraint_eqn
        
        for equality in equalities:
            self.check_missing_symbols(declared_symbols, equality.constraint_eqn)
            lambda_sym = Symbol(f"lambda_{next(self._ids)}")
            lambdas.append(lambda_sym)
            lagrange += lambda_sym * equality.constraint_eqn
        
        super().__init__(lagrange, constants, variables, lambdas)
        
    def check_missing_symbols(declared_symbols, eqn):
        for symbol in eqn.free_symbols:
            if symbol not in declared_symbols:
                raise Exception(f"The symbol ({symbol}) in equation {eqn} was not supplied as a variable or constant.")


