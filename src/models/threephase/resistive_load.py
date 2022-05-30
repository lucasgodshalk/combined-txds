class ResistiveLoad():

    def __init__(self):
        # The phase loads associated with this Resistive load
        self.phase_loads = []
        
    def stamp_primal(self, Y, J, v_previous, tx_factor, state):
        for phase_load in self.phase_loads:
            phase_load.collect_Y_stamps(state)

    def set_initial_voltages(self, state, v):
        for phase_load in self.phase_loads:
            phase_load.set_initial_voltages(state, v)
        

