from logic.powerflowsettings import PowerFlowSettings
from logic.homotopycontroller import HomotopyController
from models.threephase.capacitor import CapSwitchState, Capacitor, CapacitorMode

MAX_DEVICE_ITERATIONS = 10

#This manages any device operations during the solve process (regulators, capacitors, etc).
#In order to avoid discontinuous Newton-Raphson steps, a complete solution is found before
#any device operational changes are made.
class DeviceController:
    def __init__(self, settings: PowerFlowSettings, solver: HomotopyController) -> None:
        self.settings = settings
        self.homotopy = solver

        self.network = self.homotopy.nrsolver.network_model

    def run_powerflow(self, v_init):
        #Preliminary adjustments based on initial conditions
        self.try_adjust_devices(v_init)

        for _ in range(MAX_DEVICE_ITERATIONS):
            is_success, v_final, iteration_num, tx_factor = self.homotopy.run_powerflow(v_init)
            if not self.try_adjust_devices(v_final):
                return (is_success, v_final, iteration_num, tx_factor)
        
        raise Exception("Could not find solution where no device adjustments were required.")

    #Returns True if a device adjustment is performed.
    def try_adjust_devices(self, v):
        adjustment_made = False
        if self.network.is_three_phase:
            if self.try_adjust_capacitors(v):
                adjustment_made = True

        return adjustment_made

    def try_adjust_capacitors(self, v):
        adjustment_made = False
        cap: Capacitor
        for cap in self.network.capacitors:
            if cap.mode == CapacitorMode.MANUAL:
                continue
            elif cap.mode == CapacitorMode.VOLT:
                f_r, f_i = (cap.from_bus.node_Vr, cap.from_bus.node_Vi)
                v_r = v[f_r]
                v_i = v[f_i]

                v_magnitude = abs(complex(v_r,v_i))
                if v_magnitude > cap.high_voltage:
                    if cap.switch == CapSwitchState.OPEN:
                        cap.switch = CapSwitchState.CLOSED
                        adjustment_made = True
                if v_magnitude < cap.low_voltage:
                    if cap.switch == CapSwitchState.CLOSED:
                        cap.switch = CapSwitchState.OPEN
                        adjustment_made = True
            else:
                raise Exception(f"{cap.mode} mode for capacitor not implemented")

        return adjustment_made
