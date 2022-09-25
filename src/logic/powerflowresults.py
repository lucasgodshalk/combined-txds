import cmath
import math
from pathlib import Path
from typing import List
import numpy as np
import pandas as pd
from logic.networkmodel import NetworkModel
from logic.powerflowsettings import PowerFlowSettings
from models.optimization.L2infeasibility import L2InfeasibilityOptimization
from models.singlephase.bus import Bus

class GENTYPE:
    PV = "PV"
    Slack = "Slack"
    Inf = "Inf"
    PQ = "PQ"

class GeneratorResult:
    def __init__(self, generator, P, Q, type_str):
        self.generator = generator
        self.P = P
        self.Q = Q
        self.type_str = type_str

    def __str__(self) -> str:
        name = self.type_str
        return f'{name} @ bus {self.generator.bus.Bus} P (MW): {"{:.2f}".format(self.P)}, Q (MVar): {"{:.2f}".format(self.Q)}'

    def csv_string(self) -> str:
        name = self.type_str
        return f'{self.generator.bus.Bus},{name},{"{:.2f}".format(self.P)},{"{:.2f}".format(self.Q)}\n'

class BusResult:
    def __init__(self, bus: Bus, V_r, V_i, lambda_r, lambda_i):
        self.bus = bus

        self.V_r = V_r
        self.V_i = V_i
        self.V = complex(V_r, V_i)

        self.lambda_r = lambda_r
        self.lambda_i = lambda_i

        self.V_mag = abs(self.V)
        if self.V_mag < 1e-8:
            self.V_deg = 0
        else:
            #Voltage angle in radians
            self.V_ang = cmath.phase(self.V)
            #Voltage angle in degrees
            self.V_deg = math.degrees(self.V_ang)
    
    def get_infeasible(self):
        return (self.I_inf_r, self.I_inf_i)

    def __str__(self) -> str:
        v_mag_str = "{:.3f}".format(self.V_mag)
        v_ang_str = "{:.3f}".format(self.V_deg)
        return f'Bus {self.bus.Bus} ({self.bus.NodeName}:{self.bus.NodePhase}) V mag: {v_mag_str}, V ang (deg): {v_ang_str}'

    def __repr__(self):
        v_mag_str = "{:.3f}".format(self.V_mag)
        v_ang_str = "{:.3f}".format(self.V_deg)
        return f'Bus {self.bus.Bus} ({self.bus.NodeName}:{self.bus.NodePhase}) V mag: {v_mag_str}, V ang (deg): {v_ang_str}'

    def csv_string(self) -> str:
        v_mag_str = "{:.3f}".format(self.V_mag)
        v_ang_str = "{:.3f}".format(self.V_deg)
        return f'{self.bus.Bus},{self.bus.NodeName}:{self.bus.NodePhase},{v_mag_str},{v_ang_str}\n'

class LoadResult:
    def __init__(self, load, P, Q, type_str):
        self.load = load
        self.P = P
        self.Q = Q
        self.type_str = type_str

    def __str__(self) -> str:
        name = self.type_str
        return f'{name} from bus {self.load.from_bus} P: {"{:.2f}".format(self.P)}, Q: {"{:.2f}".format(self.Q)}'

    def csv_string(self) -> str:
        name = self.type_str
        return f'{self.load.from_bus.Bus},{name},{"{:.2f}".format(self.P)},{"{:.2f}".format(self.Q)}\n'

class PowerFlowResults:
    def __init__(
        self, 
        is_success: bool, 
        iterations: int, 
        tx_percent,
        duration_sec, 
        network: NetworkModel,
         v_final, 
         settings: PowerFlowSettings
         ):
        self.is_success = is_success
        self.iterations = iterations
        self.tx_percent = tx_percent
        self.duration_sec = duration_sec
        self.network = network
        self.v_final = v_final
        self.settings = settings

        self.bus_results: List[BusResult]
        self.bus_results = []

        self.generator_results: List[GeneratorResult]
        self.generator_results = []

        self.load_results: List[LoadResult]
        self.load_results = []

        for bus in network.buses:
            V_r = v_final[bus.node_Vr]
            V_i = v_final[bus.node_Vi]

            if settings.infeasibility_analysis:
                lambda_r = v_final[bus.node_lambda_Vr]
                lambda_i = v_final[bus.node_lambda_Vi]
            else:
                lambda_r = None
                lambda_i = None
            
            self.bus_results.append(BusResult(bus, V_r, V_i, lambda_r, lambda_i))

        for generator in self.network.generators:
            Q = v_final[generator.bus.node_Q]
            P = generator.P

            self.generator_results.append(GeneratorResult(generator, P, Q, GENTYPE.PV))

        for load in self.network.loads:
            P = load.P
            Q = load.Q
            
            self.load_results.append(LoadResult(load, P, Q, GENTYPE.PQ))

        for slack in self.network.slack:
            Vr = v_final[slack.bus.node_Vr]
            Vi = v_final[slack.bus.node_Vi]
            slack_Ir = v_final[slack.slack_Ir]
            slack_Ii = v_final[slack.slack_Ii]
            P = Vr * slack_Ir
            Q = Vi * slack_Ii
            self.generator_results.append(GeneratorResult(slack, P, Q, GENTYPE.Slack))

        if self.network.optimization != None and isinstance(self.network.optimization, L2InfeasibilityOptimization):
            total_P = 0
            total_Q = 0
            for infeasibility_current in self.network.optimization.infeasibility_currents:
                Vr = v_final[infeasibility_current.bus.node_Vr]
                Vi = v_final[infeasibility_current.bus.node_Vi]
                inf_Ir = v_final[infeasibility_current.node_Ir_inf]
                inf_Ii = v_final[infeasibility_current.node_Ii_inf]
                P = Vr * inf_Ir
                if P < 1e-5:
                    P = 0
                Q = Vi * inf_Ii
                if Q < 1e-5:
                    Q = 0

                total_P += P
                total_Q += Q
                self.generator_results.append(GeneratorResult(infeasibility_current, P, Q, GENTYPE.Inf))

            self.infeasibility_totals = (total_P, total_Q)    

        self.max_residual, self.max_residual_index, self.residuals = self.calculate_residuals()        

    def display(self, verbose=False):
        print("=====================")
        print("=====================")
        print("Powerflow Results:")

        print(f'Successful: {self.is_success}')
        print(f'Iterations: {self.iterations}')
        print(f'Duration: {"{:.3f}".format(self.duration_sec)}(s)')

        print(f'Max Residual: {self.max_residual:.3g} [Index: {self.max_residual_index}]')

        if verbose:
            for idx in range(len(self.residuals)):
                print(f'Residual {idx}: {self.residuals[idx]:.3g}')

        if self.settings.infeasibility_analysis:
            results = self.report_infeasible()
            P_sum = sum([result.P for result in results])
            Q_sum = sum([result.Q for result in results])
            print(f'Inf P: {P_sum:.3g}')
            print(f'Inf Q: {Q_sum:.3g}')

        if verbose:
            self.__display_verbose()

        print("=====================")

    def __display_verbose(self):
        print("Buses:")

        for bus in self.bus_results:
            print(bus)

        print("Generators:")

        for gen in self.generator_results:
            print(gen)

        print("Loads:")

        for load in self.load_results:
            print(load)

    def calculate_residuals(self):
        all_elements = self.network.get_NR_invariant_elements() + self.network.get_NR_variable_elements()

        residual_contributions = []
        for element in all_elements:
            element_residuals = element.calculate_residuals(self.network, self.v_final)
            for (index, value) in element_residuals.items():
                residual_contributions.append((element, index, value))

        if self.network.optimization != None:
            element_residuals = self.network.optimization.calculate_residuals(self.network, self.v_final)
            for (index, value) in element_residuals.items():
                residual_contributions.append((self.network.optimization, index, value))

        residuals = np.zeros(len(self.v_final))
        for (element, index, value) in residual_contributions:
            residuals[index] += value

        max_residual = np.amax(np.abs(residuals))
        max_residual_idx = int(np.argmax(np.abs(residuals)))

        return (max_residual, max_residual_idx, residuals)

    def report_infeasible(self):
        results = []

        for gen_result in self.generator_results:
            (P, Q) = gen_result.P, gen_result.Q
            if abs(P) < 1e-5 and abs(Q) < 1e-5:
                continue

            if gen_result.type_str == GENTYPE.Inf:
                results.append(gen_result)

        return results

    def output(self, outputfilepath):
        if not outputfilepath:
            return

        voltagefilepath=Path(f"{outputfilepath}_voltage.csv")
        powerfilepath=Path(f"{outputfilepath}_power.csv")
        
        voltagefilepath.parent.mkdir(parents=True, exist_ok=True)

        with open(voltagefilepath, "w+") as f:
            f.write("bus,name,v_magnitude,v_ang_degrees\n")
            for bus in self.bus_results:
                f.write(bus.csv_string())

        powerfilepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(powerfilepath, "w+") as f:
            f.write("bus,name,P(MW),Q(MVar)\n")
            for gen in self.generator_results:
                f.write(gen.csv_string())
            for load in self.load_results:
                f.write(load.csv_string())

class QuasiTimeSeriesResults:
    def __init__(self):
        self.powerflow_snapshot_results: dict[int, PowerFlowResults]
        self.powerflow_snapshot_results = dict()
    
    def add_powerflow_snapshot_results(self, hour:int, pf_results : PowerFlowResults):
        self.powerflow_snapshot_results[hour] = pf_results

    def display(self, verbose=False):
        for hour, pf_result in self.powerflow_snapshot_results.items():
            print("---------------------")
            print(f"HOUR {hour}")
            pf_result.display(verbose)
            print("---------------------")
    
    def output(self, outputfilepath):
        if not outputfilepath:
            return

        for hour, pf_result in self.powerflow_snapshot_results.items():
            pf_result.output(f"{outputfilepath}_{hour}")