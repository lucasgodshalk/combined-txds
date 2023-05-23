import cmath
import math
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from logic.network.networkmodel import NetworkModel
from logic.powerflowsettings import PowerFlowSettings
from logic.residualdetails import ResidualDetails
from models.components.bus import Bus
from models.components.center_tap_transformer import CenterTapTransformer
from models.components.unbalanced_line import UnbalancedLinePhase
from models.optimization.L2infeasibility import L2InfeasibilityOptimization


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
        return f'{self.load.from_bus.NodeName},{name},{"{:.2f}".format(self.P)},{"{:.2f}".format(self.Q)}\n'

class PowerFlowResults:
    def __init__(
        self, 
        is_success: bool, 
        iterations: int, 
        tx_percent,
        duration_sec, 
        network: NetworkModel,
        v_final, 
        settings: PowerFlowSettings,
        residuals: ResidualDetails
        ):
        self.is_success = is_success
        self.iterations = iterations
        self.tx_percent = tx_percent
        self.duration_sec = duration_sec
        self.network = network
        self.v_final = v_final
        self.settings = settings
        self.residuals = residuals

        self.bus_results: List[BusResult]
        self.bus_results = []

        self.generator_results: List[GeneratorResult]
        self.generator_results = []

        self.load_results: List[LoadResult]
        self.load_results = []

        for bus in network.buses:
            if bus.IsVirtual:
                continue
            V_r = v_final[bus.node_Vr]
            V_i = v_final[bus.node_Vi]

            if network.optimization != None:
                lambda_r = v_final[bus.node_lambda_Vr]
                lambda_i = v_final[bus.node_lambda_Vi]
            else:
                lambda_r = None
                lambda_i = None
            
            self.bus_results.append(BusResult(bus, V_r, V_i, lambda_r, lambda_i))

        for generator in self.network.generators:
            Q = v_final[generator.get_Q_index()]
            P = generator.P

            self.generator_results.append(GeneratorResult(generator, P, Q, GENTYPE.PV))

        for load in self.network.loads:
            P = load.P
            Q = load.Q
            
            self.load_results.append(LoadResult(load, P, Q, GENTYPE.PQ))

        for slack in self.network.slack:
            Vr = v_final[slack.bus.node_Vr]
            Vi = v_final[slack.bus.node_Vi]
            slack_Ir = v_final[slack.get_slack_Ir_index()]
            slack_Ii = v_final[slack.get_slack_Ii_index()]
            P = Vr * slack_Ir
            Q = Vi * slack_Ii
            self.generator_results.append(GeneratorResult(slack, P, Q, GENTYPE.Slack)) 

        self.max_residual = self.residuals.max_residual

        self.try_load_infeasibility_data()

    def try_load_infeasibility_data(self):
        self.infeasibility_totals = None

        if self.network.optimization == None or not isinstance(self.network.optimization, L2InfeasibilityOptimization):
            return

        total_P = 0
        total_Q = 0
        for infeasibility_current in self.network.optimization.infeasibility_currents:
            Vr = self.v_final[infeasibility_current.bus.node_Vr]
            Vi = self.v_final[infeasibility_current.bus.node_Vi]
            inf_Ir = self.v_final[infeasibility_current.node_Ir_inf]
            inf_Ii = self.v_final[infeasibility_current.node_Ii_inf]
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

    def display(self, verbose=False):
        print("=====================")
        print("=====================")
        print("Powerflow Results:")

        print(f'Successful: {self.is_success}')
        print(f'Iterations: {self.iterations}')
        print(f'Duration: {"{:.3f}".format(self.duration_sec)}(s)')

        print(f'Max Residual: {self.residuals.max_residual:.3g} [Index: {self.residuals.max_residual_idx}]')

        if verbose:
            for idx in range(len(self.residuals)):
                print(f'Residual {idx}: {self.residuals[idx]:.3g}')

        try:
            results = self.report_infeasible()
            P_sum = sum([result.P for result in results])
            Q_sum = sum([result.Q for result in results])
            print(f'Inf P: {P_sum:.3g}')
            print(f'Inf Q: {Q_sum:.3g}')
        except:
            pass

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
            if not self.is_success:
                f.write("FAILURE")
            else:
                f.write("bus,name,v_magnitude,v_ang_degrees\n")
                for bus in self.bus_results:
                    f.write(bus.csv_string())
                if (hasattr(self,"violates_equipment_ratings") and self.violates_equipment_ratings):
                    f.write("VIOLATED EQUIPMENT RATINGS")

        powerfilepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(powerfilepath, "w+") as f:
            if not self.is_success:
                f.write("FAILURE")
            else:
                f.write("bus,name,P(MW),Q(MVar)\n")
                for gen in self.generator_results:
                    f.write(gen.csv_string())
                for load in self.load_results:
                    f.write(load.csv_string())

                if (hasattr(self,"violates_equipment_ratings") and self.violates_equipment_ratings):
                    f.write("VIOLATED EQUIPMENT RATINGS")

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

class TransformerResult:
    def __init__(self, transformer, snapshot_results: PowerFlowResults):
        self.transformer = transformer
        primal_indices = [self.transformer.xfrmr_stamper.var_map[primal] for primal in self.transformer.xfrmr_stamper.lsegment.primals]
        self.Vr_pri_pos, self.Vi_pri_pos, self.Vr_pri_neg, self.Vi_pri_neg, self.Ir_prim, self.Ii_prim, self.Vr_sec_pos, self.Vi_sec_pos, self.Vr_sec_neg, self.Vi_sec_neg = [snapshot_results.v_final[idx] if idx is not None else 0 for idx in primal_indices]

    def get_P(self):
        Vr_pri = self.Vr_pri_pos - self.Vr_pri_neg
        return Vr_pri * self.Ir_prim

    def get_Q(self):
        Vi_pri = self.Vi_pri_pos - self.Vi_pri_neg
        return Vi_pri * self.Ii_prim

    def __str__(self) -> str:
        return f'Transformer from bus {self.transformer.from_bus_pos.Bus} and {self.transformer.from_bus_neg.Bus} to {self.transformer.to_bus_pos.Bus} and {self.transformer.to_bus_neg.Bus} P (MW): {"{:.2f}".format(self.get_P())}, Q (MVar): {"{:.2f}".format(self.get_Q())}'

    def csv_string(self) -> str:
        return f'{self.transformer.from_bus_pos.Bus},Transformer,{"{:.2f}".format(self.get_P())},{"{:.2f}".format(self.get_Q())}\n'

class CenterTapTransformerResult:
    def __init__(self, transformer: CenterTapTransformer, snapshot_results: PowerFlowResults):
        self.transformer = transformer
        primal_indices = [self.transformer.center_tap_xfmr_stamper.var_map[primal] for primal in self.transformer.center_tap_xfmr_stamper.lsegment.primals]
        (self.from_bus, self.to_bus_1), (_, self.to_bus_2) = transformer.get_connections()
        self.Vr_pri, self.Vi_pri, self.Ir_L1, self.Ii_L1, self.Vr_L1, self.Vi_L1, self.Ir_L2, self.Ii_L2, self.Vr_L2, self.Vi_L2 = [snapshot_results.v_final[idx] for idx in primal_indices]

    def get_P(self):
        return self.Vr_L1 * self.Ir_L1 + self.Vi_L1 * self.Ii_L1 + self.Vr_L2 * self.Ir_L2 + self.Vi_L2 * self.Ii_L2

    def get_Q(self):
        return -self.Vr_L1 * self.Ii_L1 + self.Vi_L1 * self.Ir_L1 - self.Vr_L2 * self.Ii_L2 + self.Vi_L2 * self.Ir_L2

    def __str__(self) -> str:
        return f'Center-Tap Transformer from bus {self.from_bus.Bus} to {self.to_bus_1} and {self.to_bus_2} P (MW): {"{:.2f}".format(self.get_P())}, Q (MVar): {"{:.2f}".format(self.get_Q())}'

    def csv_string(self) -> str:
        return f'{self.from_bus.Bus},CenterTapTransformer,{"{:.2f}".format(self.get_P())},{"{:.2f}".format(self.get_Q())}\n'

# BROKEN, THIS HAS TO USE __loop_line_stampers INSTEAD I THINK

class LineResult:
    def __init__(self, line: UnbalancedLinePhase, snapshot_results: PowerFlowResults, g, b):
        self.line = line
        self.v_final = snapshot_results.v_final
        self.from_bus, self.to_bus = line.get_nodes(snapshot_results.network)
        self.g = g
        self.b = b

    def get_Ir(self):
        return (self.v_final[self.from_bus.node_Vr] - self.v_final[self.to_bus.node_Vr]) * self.g - (self.v_final[self.from_bus.node_Vi] - self.v_final[self.to_bus.node_Vi]) * self.b

    def get_Ii(self):
        return (self.v_final[self.from_bus.node_Vr] - self.v_final[self.to_bus.node_Vr]) * self.b + (self.v_final[self.from_bus.node_Vi] - self.v_final[self.to_bus.node_Vi]) * self.g

    def __str__(self) -> str:
        return f'Line from bus {self.from_bus.Bus} to {self.to_bus.Bus} I: complex({"{:.2f}".format(self.get_Ir())}, {"{:.2f}".format(self.get_Ii())})'

    def csv_string(self) -> str:
        return f'{self.from_bus.Bus},Line,{"{:.2f}".format(self.get_Ir())},{"{:.2f}".format(self.get_Ii())}\n'