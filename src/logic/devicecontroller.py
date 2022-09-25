from logic.powerflowsettings import PowerFlowSettings
from logic.homotopycontroller import HomotopyController
from models.singlephase.capacitor import CapSwitchState, Capacitor, CapacitorMode
from models.singlephase.fuse import Fuse, FuseStatus
from models.singlephase.regulator import RegControl, Regulator

MAX_DEVICE_ITERATIONS = 10

#This manages any device operations during the solve process (regulators, capacitors, etc).
#In order to avoid discontinuous Newton-Raphson steps, a complete solution is found before
#any device operational changes are made.
class DeviceController:
    def __init__(self, settings: PowerFlowSettings, solver: HomotopyController) -> None:
        self.settings = settings
        self.homotopy = solver

        self.optimization_enabled = self.settings.infeasibility_analysis
        self.network = self.homotopy.nrsolver.network

    def run_powerflow(self):
        #In the future, we may regenerate this based on device changes.
        self.network.assign_matrix(self.optimization_enabled)

        v_init = self.network.generate_v_init(self.settings)

        #Preliminary adjustments based on initial conditions
        if self.settings.device_control:
            self.try_adjust_devices(v_init)

        for _ in range(MAX_DEVICE_ITERATIONS):
            results = is_success, v_final, _, _ = self.homotopy.run_powerflow(v_init)
            if not is_success:
                return results
            if not self.settings.device_control or not self.try_adjust_devices(v_final):
                return results
        
        raise Exception("Could not find solution where no device adjustments were required.")

    def try_adjust_devices(self, v):
        adjustment_made = False
        if self.network.is_three_phase:
            for device in self.network.get_all_elements():
                if isinstance(device, (Fuse, Capacitor, Regulator)):
                    if device.try_adjust_device(v):
                        adjustment_made = True
        else:
            #No device control for transmission networks for now.
            pass

        return adjustment_made
