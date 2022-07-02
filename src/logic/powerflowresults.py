import math
from typing import List
import numpy as np
import pandas as pd
from logic.networkmodel import NetworkModel
from logic.powerflowsettings import PowerFlowSettings
from models.shared.bus import Bus


class GeneratorResult:
    def __init__(self, generator, P, Q, is_slack):
        self.generator = generator
        self.P = P * 100
        self.Q = Q * 100
        self.is_slack = is_slack

    def __str__(self) -> str:
        name = "Slack" if self.is_slack else "Generator"
        return f'{name} @ bus {self.generator.bus.Bus} P (MW): {"{:.2f}".format(self.P)}, Q (MVar): {"{:.2f}".format(self.Q)}'

class BusResult:
    def __init__(self, bus: Bus, V_r, V_i, lambda_r, lambda_i):
        self.bus = bus
        self.V_r = V_r
        self.V_i = V_i
        self.lambda_r = lambda_r
        self.lambda_i = lambda_i
        self.V_mag = math.sqrt(V_r ** 2 + V_i ** 2)
        self.V_ang = math.atan2(V_i, V_r)  * 180 / math.pi
    
    def get_infeasible(self):
        return (self.I_inf_r, self.I_inf_i)

    def __str__(self) -> str:
        v_mag_str = "{:.3f}".format(self.V_mag)
        v_ang_str = "{:.3f}".format(self.V_ang)
        return f'Bus {self.bus.Bus} ({self.bus.NodeName}:{self.bus.NodePhase}) V mag: {v_mag_str}, V ang (deg): {v_ang_str}'

class PowerFlowResults:
    def __init__(self, is_success: bool, iterations: int, duration_sec, network: NetworkModel, v_final, settings: PowerFlowSettings):
        self.is_success = is_success
        self.iterations = iterations
        self.duration_sec = duration_sec
        self.network = network
        self.v_final = v_final
        self.settings = settings

        self.bus_results: List[BusResult]
        self.bus_results = []

        self.generator_results: List[GeneratorResult]
        self.generator_results = []

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
            Q = -v_final[generator.bus.node_Q]
            P = -generator.P

            self.generator_results.append(GeneratorResult(generator, P, Q, False))

        for slack in self.network.slack:
            slack_Ir = v_final[slack.slack_Ir]
            slack_Vr = slack.Vr_set
            P = slack_Vr * slack_Ir * math.cos(slack.ang_rad)
            Q = slack_Vr * slack_Ir * math.sin(slack.ang_rad)
            self.generator_results.append(GeneratorResult(slack, P, Q, True))

    def display(self, verbose=False):
        print("=====================")
        print("=====================")
        print("Powerflow Results:")

        print(f'Successful: {self.is_success}')
        print(f'Iterations: {self.iterations}')
        print(f'Duration: {"{:.3f}".format(self.duration_sec)}(s)')

        max_residual, residuals = self.calculate_residuals()

        print(f'Max Residual: {"{:.3f}".format(max_residual)}')

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

        inf_total_r = 0#sum(abs(bus.I_inf_r) for bus in self.bus_results)
        inf_total_i = 0#sum(abs(bus.I_inf_i) for bus in self.bus_results)

        print("Total Infeasibility Current (abs):")
        inf_total_r_str = "{:.3f}".format(inf_total_r)
        inf_total_i_str = "{:.3f}".format(inf_total_i)
        print(f'Real: {inf_total_r_str}, Imag: {inf_total_i_str}')

    def calculate_residuals(self):
        all_elements = self.network.get_NR_invariant_elements() + self.network.get_NR_variable_elements()

        residuals = np.zeros(len(self.v_final))

        for element in all_elements:
            for (index, value) in element.calculate_residuals(self.network, self.v_final).items():
                residuals[index] += value

        max_residual = np.amax(np.abs(residuals))

        return (max_residual, residuals)

    def report_infeasible(self):
        largest = []

        for bus_result in self.bus_results:
            (I_r, I_i) = bus_result.get_infeasible()
            if abs(I_r) < 1e-5 and abs(I_i) < 1e-5:
                continue

            if len(largest) == 0:
                largest.append(bus_result)
                continue

            (I_r_next, I_i_next) = largest[-1].get_infeasible()

            if abs(I_r) >= abs(I_r_next) or abs(I_i) >= abs(I_i_next):
                largest.append(bus_result)

        return largest[-3:]


def display_mat_comparison(mat, results: PowerFlowResults):
    for idx in range(len(mat['sol']['bus'][0][0])):
        bus = mat['sol']['bus'][0][0][idx][0]
        V_mag = mat['sol']['bus'][0][0][idx][7]
        V_ang = mat['sol']['bus'][0][0][idx][8]

        simulator_V_mag = results.bus_results[idx].V_mag
        simulator_V_ang = results.bus_results[idx].V_ang

        print(f'Bus: {int(bus)} V_mag diff: {"{:.4f}".format(simulator_V_mag - V_mag)} V_ang diff: {"{:.4f}".format(simulator_V_ang - V_ang)}')

def assert_mat_comparison(mat, results: PowerFlowResults):
    for idx in range(len(mat['sol']['bus'][0][0])):
        bus = mat['sol']['bus'][0][0][idx][0]
        V_mag = mat['sol']['bus'][0][0][idx][7]
        V_ang = mat['sol']['bus'][0][0][idx][8]

        simulator_V_mag = results.bus_results[idx].V_mag
        simulator_V_ang = results.bus_results[idx].V_ang
        
        mag_diff = abs(V_mag - simulator_V_mag)
        ang_diff = abs(V_ang - simulator_V_ang)

        if mag_diff >= 1e-4:
            raise Exception(f'Bus {results.bus_results[idx].bus.Bus} magnitude is off by {"{:.4f}".format(mag_diff)}')

        if ang_diff >= 1e-4:
            raise Exception(f'Bus {results.bus_results[idx].bus.Bus} angle is off by {"{:.4f}".format(ang_diff)}')

def print_infeas_comparison(casename, results: PowerFlowResults):
    resultfile = f'result_comparison/{casename}.infeas.csv'

    df = pd.read_csv(resultfile)

    bus_lookup = {}

    for result in results.bus_results:
        bus_lookup[result.bus.Bus] = result.get_infeasible()

    l2_sum = 0
    l2_sum_comp = 0

    I_r_diff_sum = 0
    I_i_diff_sum = 0

    for _, row in df.iterrows():
        bus_num = row['Bus']
        I_r_comp = float(row['Infeasibility Current Real'].replace("[", "").replace("]", ""))
        I_i_comp = float(row['Infeasibility Current Imag'].replace("[", "").replace("]", ""))

        I_r, I_i = bus_lookup[bus_num]

        l2_sum += I_r ** 2
        l2_sum += I_i ** 2

        l2_sum_comp += I_r_comp ** 2
        l2_sum_comp += I_i_comp ** 2

        I_r_diff_sum += abs(I_r - I_r_comp) / I_r
        I_i_diff_sum += abs(I_i - I_i_comp) / I_i

    l2_sum_str = "{:.3f}".format(math.sqrt(l2_sum))

    print("L2 norm:")
    print(l2_sum_str)

    l2_sum_comp_str = "{:.3f}".format(math.sqrt(l2_sum_comp))

    print("Comparison solution L2 norm:")
    print(l2_sum_comp_str)

    I_r_diff_sum_str = "{:.1f}".format(I_r_diff_sum / len(df) * 100)
    I_r_diff_sum_str = "{:.1f}".format(I_i_diff_sum / len(df) * 100)

    print('Average percent difference with comparison solution:')
    print(f'I_r: {I_r_diff_sum_str}%, I_i: {I_r_diff_sum_str}%')
