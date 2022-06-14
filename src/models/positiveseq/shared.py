from logic.matrixbuilder import MatrixBuilder

def stamp_line(Y: MatrixBuilder, Vr_from, Vr_to, Vi_from, Vi_to, G, B):
    #From Bus - Real
    Y.stamp(Vr_from, Vr_from, G)
    Y.stamp(Vr_from, Vr_to, -G)
    Y.stamp(Vr_from, Vi_from, B)
    Y.stamp(Vr_from, Vi_to, -B)

    #From Bus - Imaginary
    Y.stamp(Vi_from, Vi_from, G)
    Y.stamp(Vi_from, Vi_to, -G)
    Y.stamp(Vi_from, Vr_from, -B)
    Y.stamp(Vi_from, Vr_to, B)

    #To Bus - Real
    Y.stamp(Vr_to, Vr_to, G)
    Y.stamp(Vr_to, Vr_from, -G)
    Y.stamp(Vr_to, Vi_to, B)
    Y.stamp(Vr_to, Vi_from, -B)

    #To Bus - Imaginary
    Y.stamp(Vi_to, Vi_to, G)
    Y.stamp(Vi_to, Vi_from, -G)
    Y.stamp(Vi_to, Vr_to, -B)
    Y.stamp(Vi_to, Vr_from, B)

def dump_index_map(buses, slacks):
    map = {}

    for bus in buses:
        map[f'bus-{bus.Bus}-Vr'] = bus.node_Vr
        map[f'bus-{bus.Bus}-Vi'] = bus.node_Vi
        if bus.node_Q != None:
            map[f'bus-{bus.Bus}-Q'] = bus.node_Q
    
    for slack in slacks:
        map[f'slack-{slack.bus.Bus}-Ir'] = slack.slack_Ir
        map[f'slack-{slack.bus.Bus}-Ii'] = slack.slack_Ii

    return map

def dump_Y(Y):
    for idx_row in range(len(Y)):
        for idx_col in range(len(Y)):
            if Y[idx_row, idx_col] > 0:
                print(f'row: {idx_row}, col: {idx_col}, val:{Y[idx_row, idx_col]}')
