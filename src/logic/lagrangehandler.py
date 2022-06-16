from sympy import diff, lambdify, Eq, simplify

def is_linear(expr, vars):
    for x in vars:
        for y in vars:
            try: 
                if not Eq(diff(expr, x, y), 0):
                    return False
            except TypeError:
                return False
    return True 

def return_zero(*args):
    return 0

class LagrangeHandler:
    def __init__(self, lagrange, constant_symbols, primal_symbols, dual_symbols) -> None:
        self.lagrange = lagrange
        self.constants = constant_symbols
        self.primals = primal_symbols
        self.duals = dual_symbols
        self.is_nonlinear = False

        self.first_order_eqns = {}
        self.first_order_evals = {}

        #For non-linear equations:
        self.second_order_eqns = {}
        self.second_order_evals = {}
        self.kth_sum_eqns = {}
        self.kth_sum_evals = {}

        self.variables = primal_symbols + dual_symbols

        for first_order in self.variables:
            dL_first = diff(lagrange, first_order)

            self.first_order_eqns[first_order] = dL_first
            self.first_order_evals[first_order] = lambdify(constant_symbols + self.variables, dL_first)

            if not is_linear(dL_first, self.variables):
                self.is_nonlinear = True

                kth_sum = -dL_first

                for second_order in self.variables:
                    dL_second = diff(dL_first, second_order) 
                    self.second_order_eqns[(first_order, second_order)] = dL_second
                    if dL_second == 0:
                        self.second_order_evals[(first_order, second_order)] = return_zero
                    else:
                        self.second_order_evals[(first_order, second_order)] = lambdify(constant_symbols + self.variables, dL_second)

                    kth_sum += dL_second * second_order
                
                #Sometimes the kth sum can be simplified down after appending together.
                kth_sum = simplify(kth_sum)

                self.kth_sum_eqns[first_order] = kth_sum
                self.kth_sum_evals[first_order] = lambdify(constant_symbols + self.variables, kth_sum)

    def evaluate_primals(self, constant_vals, primal_vals, dual_vals):
        values = constant_vals + primal_vals + dual_vals
        return self.__evaluate_set(self.duals, values)

    def evaluate_duals(self, constant_vals, primal_vals, dual_vals):
        values = constant_vals + primal_vals + dual_vals
        return self.__evaluate_set(self.primals, values)

    def __evaluate_set(self, set, values):
        components = {}

        for primal in set:
            if self.is_nonlinear:
                second_order_results = {}
                for second_order in self.variables:
                    second_order_results[second_order] = self.second_order_evals[(primal, second_order)](*values)
                
                kth_sum = self.kth_sum_evals[primal](*values)

                components[primal] = (kth_sum, second_order_results)
            else:
                val = self.first_order_evals[primal](*values)
                components[primal] = val
        
        return components
