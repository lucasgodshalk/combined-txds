class PhaseCapacitor():

    def __init__(self, Vr_init, Vi_init, nominal_reactive_power, low_voltage, high_voltage, phase, bus_id):
        self.bus_id = bus_id
        self.Vr_init = Vr_init
        self.Vi_init = Vi_init
        self.phase = phase
        self.nominal_reactive_power = nominal_reactive_power
        self.low_voltage = low_voltage
        self.high_voltage = high_voltage
        self.on = True
        
    def stamp_primal(self, Y, J, v_estimate, tx_factor, state):
        f_r, f_i = state.bus_map[self.bus_id]
        v_r = v_estimate[f_r]
        v_i = v_estimate[f_i]

        v_magnitude = abs(complex(v_r,v_i))
        if v_magnitude > self.high_voltage:
            self.on = False
            return
        if v_magnitude < self.low_voltage:
            self.on = True
        if not self.on:
            return

        # A capacitor goes from the line to ground, so that voltage along the line remains constant
        # There is a current going across the capacitor into the ground, which depends on the voltage
        # So this is a nonlinear value, changing over the course of NR?
        # In steady state, a capacitor is essentially an open circuit, but it magically sets the voltage? That is definitely false.
        # 
        # i = C * dV / dT

        #(V_r + jV_i)*j*omega*C = jV_r*omega*C - V_i*omega*C = the impact of the capacitor on the current at that node?
        # V_r = -V_i*omega*C
        # V_i = V_r * omega * C


        # g = 0 # A capacitor has 0 conductance
        # b = state.OMEGA * self.capacitance # A capacitor has a susceptance only

        # We know there is only a real value of this
        z = (complex(v_r,v_i)*complex(v_r,-v_i)/self.nominal_reactive_power).real
        # Stamp as if the impedance is connected to neutral/ground
        Y.stamp(f_r, f_r, 1/z)
        Y.stamp(f_i, f_i, 1/z)
        # r,x = z.real, z.imag
        # g,b = r/(r**2+x**2), x/(r**2+x**2)

        # TODO figure out the stamp for these
        # Capacitors have an imaginary impedance (reactance) and an imaginary admittance (susceptance)
        # Y.stamp(f_r, f_i, -b)
        # Y.stamp(f_i, f_r, b)

        # Y.stamp(self.real_current_idx, f_r, 1)
        # Y.stamp(self.imag_current_idx, f_i, 1)

    def calculate_residuals(self, state, v, residual_contributions):
        f_r, f_i = state.bus_map[self.bus_id]
        v_r = v[f_r]
        v_i = v[f_i]
        
        z = (complex(v_r,v_i)*complex(v_r,-v_i)/self.nominal_reactive_power).real
        
        # This currently doesn't line up with what i expect it to do, so I'm going to try just ignoring it for now
        # Stamp as if the impedance is connected to neutral/ground
        # residual_contributions[f_r] += v_r / z
        # residual_contributions[f_i] += v_i / z

        return residual_contributions
        
    def set_initial_voltages(self, state, v):
        # Indices in J of the real and imaginary voltage variables for this bus
        f_r, f_i = state.bus_map[self.bus_id]

        v[f_r] = self.Vr_init
        v[f_i] = self.Vi_init