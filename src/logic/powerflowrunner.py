from collections import defaultdict
from anoeds.anoeds_parser import Parser
from anoeds.models.bus import Bus
from anoeds.models.resistive_load import ResistiveLoad
from anoeds.models.pq_load import PQLoad
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
import os

class PowerFlowRunner:
    def __init__(self, input_file, settings):
        self.input_file = input_file
        self.settings = settings

    def run(self, return_state=False):
        parser = Parser(self.input_file)
        simulation_state = parser.parse()

        simulation_state.reset_linear_stamp_collection()
        self.collect_linear_stamps(simulation_state)
        self.stamp_linear(simulation_state)

        # Run Newton-Raphson
        NR_iteration = 0
        max_error = float('inf')
        self.reset_v_estimate(simulation_state)

        while (NR_iteration < self.settings['max_iterations']) and (self.settings['tolerance'] < max_error):
            simulation_state.reset_nonlinear_stamp_collection()
            self.collect_nonlinear_stamps(simulation_state, self.v_estimate)
            self.stamp_nonlinear(simulation_state)

            Y = simulation_state.lin_Y + simulation_state.nonlin_Y
            J = simulation_state.lin_J + simulation_state.nonlin_J

            # Check for all-zero rows and columns
            nonzero_rows = Y.getnnz(1)>0
            nonzero_columns = Y.getnnz(0)>0
            if not (np.all(nonzero_rows) and np.all(nonzero_columns)):
                raise Exception("should not have any zero rows or columns in Y matrix")

            previous_v_estimate = self.v_estimate

            self.v_estimate = spsolve(Y, J)
            
            max_error = np.max(np.abs(self.v_estimate - previous_v_estimate))
            if (np.isnan(max_error)):
                raise Exception("should not have NaN error values")
            
            # # Voltage limiting
            # if (self.settings['tolerance'] < max_error):
            #     voltage_change = self.v_estimate - previous_v_estimate
            #     signs = np.sign(voltage_change)
            #     voltage_limit = 1
            #     for key in simulation_state.bus_map.keys():
            #         real_node, imag_node = simulation_state.bus_map[key]
            #         voltage_change[real_node] = signs[real_node]*min(voltage_limit, np.abs(voltage_change[real_node]))
            #         voltage_change[imag_node] = signs[imag_node]*min(voltage_limit, np.abs(voltage_change[imag_node]))
            #     self.v_estimate = previous_v_estimate + voltage_change
            
            NR_iteration += 1
        residuals = self.calculate_residuals(simulation_state)
        # for k,v in residuals.items():
        #     assert(v==0 or np.isclose(v,0, rtol=1e-10, atol=1e-10)), f"Bus {k} has a residual of {v} instead of 0, indicating that KCL did not zero out"


        if return_state:
            return self.v_estimate, simulation_state
        else:
            return self.v_estimate

    def reset_v_estimate(self, simulation_state):
        self.v_estimate = np.zeros(simulation_state.J_length)

        # Set initial voltage values for infinite sources
        for infinite_source in simulation_state.infinite_sources:
            infinite_source.set_initial_voltages(simulation_state, self.v_estimate)

        # Set initial voltage values for loads
        for load in simulation_state.loads:
            load.set_initial_voltages(simulation_state, self.v_estimate)

        # Set initial voltage values for capacitors
        for cap in simulation_state.capacitors:
            cap.set_initial_voltages(simulation_state, self.v_estimate)

        # Set initial voltage values for all other buses (one object per phase)
        for bus in simulation_state.buses:
            bus.set_initial_voltages(simulation_state, self.v_estimate)
    
    def calculate_residuals(self, simulation_state):
        residuals = defaultdict(lambda: 0)
        # Calculate residuals for transmission lines
        for transmission_line in simulation_state.transmission_lines:
            line_residual_contributions = transmission_line.calculate_residuals(simulation_state, self.v_estimate)
            for k,v in line_residual_contributions.items():
                residuals[k] += v
        # Calculate residuals for slack buses
        for infinite_source in simulation_state.infinite_sources:
            source_residual_contributions = infinite_source.calculate_residuals(simulation_state, self.v_estimate)
            for k,v in source_residual_contributions.items():
                residuals[k] += v

        for load in simulation_state.loads:
            if isinstance(load, PQLoad):
                load_residual_contributions = load.calculate_residuals(simulation_state, self.v_estimate)
                for k,v in load_residual_contributions.items():
                    residuals[k] += v

        for transformer in simulation_state.transformers:
            transformer_residual_contributions = transformer.calculate_residuals(simulation_state, self.v_estimate)
            for k,v in transformer_residual_contributions.items():
                residuals[k] += v

        for fuse in simulation_state.fuses:
            fuse_residual_contributions = fuse.calculate_residuals(simulation_state, self.v_estimate)
            for k,v in fuse_residual_contributions.items():
                residuals[k] += v

        for switch in simulation_state.switches:
            switch_residual_contributions = switch.calculate_residuals(simulation_state, self.v_estimate)
            for k,v in switch_residual_contributions.items():
                residuals[k] += v

        for capacitor in simulation_state.capacitors:
            capacitor_residual_contributions = capacitor.calculate_residuals(simulation_state, self.v_estimate)
            for k,v in capacitor_residual_contributions.items():
                residuals[k] += v

        for regulator in simulation_state.regulators:
            regulator_residual_contributions = regulator.calculate_residuals(simulation_state, self.v_estimate)
            for k,v in regulator_residual_contributions.items():
                residuals[k] += v

        return residuals

    @staticmethod
    def collect_linear_stamps(simulation_state):
        # Collect stamps for transmission lines
        for transmission_line in simulation_state.transmission_lines:
            transmission_line.collect_Y_stamps(simulation_state)

        # Collect stamps for slack buses
        for infinite_source in simulation_state.infinite_sources:
            infinite_source.collect_Y_stamps(simulation_state)
            infinite_source.collect_J_stamps(simulation_state)

        for load in simulation_state.loads:
            if isinstance(load, ResistiveLoad):
                load.collect_Y_stamps(simulation_state)

        # Collect stamps for fixed shunts

        # Collect stamps for transformers
        for transformer in simulation_state.transformers:
            transformer.collect_Y_stamps(simulation_state)

        # Collect stamps for regulators
        for regulator in simulation_state.regulators:
            regulator.collect_Y_stamps(simulation_state)

        # Collect stamps for switches
        for switch in simulation_state.switches:
            switch.collect_Y_stamps(simulation_state)

    @staticmethod
    def stamp_linear(simulation_state):
        simulation_state.lin_Y = csr_matrix((simulation_state.lin_Y_stamp_val,(simulation_state.lin_Y_stamp_coord1,simulation_state.lin_Y_stamp_coord2)), shape=(simulation_state.J_length, simulation_state.J_length), dtype=np.float64)
        simulation_state.lin_J = csr_matrix((simulation_state.lin_J_stamp_val,(simulation_state.lin_J_stamp_coord,np.zeros(len(simulation_state.lin_J_stamp_coord)))), shape=(simulation_state.J_length, 1), dtype = np.float64)

    @staticmethod
    def collect_nonlinear_stamps(simulation_state, v_estimate):
        # Collect stamps for generators

        # Collect stamps for loads
        for load in simulation_state.loads:
            if isinstance(load, PQLoad):
                load.collect_Y_stamps(simulation_state, v_estimate)
                load.collect_J_stamps(simulation_state, v_estimate)

        # Collect stamps for capacitors
        for capacitor in simulation_state.capacitors:
            capacitor.collect_Y_stamps(simulation_state, v_estimate)

        # Collect stamps for fuses
        for fuse in simulation_state.fuses:
            fuse.collect_Y_stamps(simulation_state, v_estimate)

    @staticmethod
    def stamp_nonlinear(simulation_state):
        simulation_state.nonlin_Y = csr_matrix((simulation_state.nonlin_Y_stamp_val,(simulation_state.nonlin_Y_stamp_coord1,simulation_state.nonlin_Y_stamp_coord2)), shape=(simulation_state.J_length, simulation_state.J_length), dtype=np.float64)
        simulation_state.nonlin_J = csr_matrix((simulation_state.nonlin_J_stamp_val,(simulation_state.nonlin_J_stamp_coord,np.zeros(len(simulation_state.nonlin_J_stamp_coord)))), shape=(simulation_state.J_length, 1), dtype = np.float64)


if __name__ == "__main__":
    print("starting script")
    CURR_DIR = os.path.realpath(os.path.dirname(__file__))
    glm_file_path = os.path.join("test", "data", "ieee_4_node", "node.glm")
    glm_full_file_path = os.path.join(CURR_DIR, glm_file_path)
    test_powerflowrunner = PowerFlowRunner(glm_full_file_path, {'max_iterations':100, 'tolerance': 1e-10})
    v_estimate = test_powerflowrunner.run()
    print(v_estimate)
