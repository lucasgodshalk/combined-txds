class global_vars:
    base_MVA = 1#2400
    base_kV = 1#2000000

    WYE_WYE = 1

    @staticmethod
    def add_nonlinear_Y_stamp(state, i, j, val):
        state.nonlin_Y_stamp_coord1.append(i)
        state.nonlin_Y_stamp_coord2.append(j)
        state.nonlin_Y_stamp_val.append(val)

    @staticmethod
    def add_linear_Y_stamp(state, i, j, val):
        state.lin_Y_stamp_coord1.append(i)
        state.lin_Y_stamp_coord2.append(j)
        state.lin_Y_stamp_val.append(val)

    @staticmethod
    def add_nonlinear_J_stamp(state, i,val):
        state.nonlin_J_stamp_coord.append(i)
        state.nonlin_J_stamp_val.append(val)

    @staticmethod
    def add_linear_J_stamp(state, i,val):
        state.lin_J_stamp_coord.append(i)
        state.lin_J_stamp_val.append(val)