import logging
import numpy as np

logger = logging.getLogger(__name__)

def compute_overhead_impedance_matrix(wire_list, distances, freq=60, resistivity=100, kron_reduce=True):
    wire_map = {"A": 0, "B": 1, "C": 2, "N": 3}
    matrix = [[0 for i in range(4)] for j in range(4)]
    has_neutral = False
    for i in range(len(wire_list)):
        if wire_list[i].phase == "N":
            has_neutral = True
        for j in range(len(wire_list)):
            if i == j:
                z = 0  
                if (
                    wire_list[i].resistance is not None
                    and wire_list[i].gmr is not None
                ):
                    z = calc_Zii(wire_list[i].resistance, wire_list[i].gmr, False)
                    
                else:
                    logger.debug("Warning: resistance or GMR is missing from wire")

                if wire_list[i].phase is not None:
                    index1 = index2 = wire_map[wire_list[i].phase]
                    matrix[index1][index2] = z
                else:
                    logger.debug("Warning: phase missing from wire")

            else:
                z = 0
                if (
                    distances[i][j] is not None
                ):
                    distance = distances[i][j]
                    z = calc_Zij(distance, False)
                else:
                    logger.debug("Warning X or Y values missing from wire")
                    # import pdb; pdb.set_trace()
                if (
                    wire_list[i].phase is not None
                    and wire_list[j].phase is not None
                ):
                    index1 = wire_map[wire_list[i].phase]
                    index2 = wire_map[wire_list[j].phase]
                    matrix[index1][index2] = z  # ohms per meter
                else:
                    logger.debug("Warning: phase missing from wire")
        
    # Let me try doing the Kron reduction using actual matrix calculations, see if I get something different

    matrix = np.array(matrix)

    if set([wire.phase for wire in wire_list]) == set(["A", "B", "C"]):
        return matrix[:3, :3].tolist()

    z_ij = matrix[:3, :3]
    z_in = matrix[:3, 3:]
    z_nj = matrix[3:, :3]
    z_nn = matrix[3:, 3:]
    if hasattr(z_nn, "__len__"):
        z_nn_inv = np.linalg.inv(z_nn)
    else:
        z_nn_inv = z_nn**-1
    kron_matrix = z_ij - np.dot(np.dot(z_in, z_nn_inv), z_nj)
    wire_phases = [wire.phase for wire in wire_list]
    phase_list = [('C', 2), ('B', 1), ('A', 0)]
    for phase,ind in phase_list:
        if phase not in wire_phases:
            kron_matrix = np.delete(kron_matrix, ind, 0)
            kron_matrix = np.delete(kron_matrix, ind, 1)

            
    matrix = kron_matrix.tolist()

    return matrix

# Calculating the impedance matrix for underground lines, assuming the presence of concentric neutrals
def compute_underground_impedance_matrix(wire_list, conductor_distances, freq=60, resistivity=100):
    conductor_own_neutral_distances = []
    conductor_resistances = []
    neutral_resistances = []
    conductor_gmrs = []
    neutral_gmrs = []
    num_non_neutral = 0
    for wire in wire_list:
        if wire.phase == "N":
            conductor_own_neutral_distances.append(0)
            neutral_resistances.append(wire.resistance)
            neutral_gmrs.append(wire.gmr)
        else:
            num_non_neutral += 1
            conductor_resistances.append(wire.resistance)
            conductor_gmrs.append(wire.gmr)
            if hasattr(wire, "_shield_gmr") and wire.shield_gmr != 0:
                # Neutrals are ignored for tape-shielded wires, but shield may have resistance
                MAGIC_NUMBER = 7.9385 * 2.3715
                neutral_resistances.append(wire.shield_resistance if wire.shield_resistance != 0 else (MAGIC_NUMBER / (wire.shield_diameter * wire.shield_thickness)))
                neutral_gmrs.append(wire.shield_gmr if wire.shield_gmr != 0 else ((wire.shield_diameter - (wire.shield_thickness /1000)) / 24))
                conductor_own_neutral_distances.append((wire.shield_diameter - wire.shield_thickness) / 24)
            else:
                conductor_own_neutral_distance = (wire.outer_diameter - wire.concentric_neutral_diameter) / 24
                conductor_own_neutral_distances.append(conductor_own_neutral_distance)
                k = wire.concentric_neutral_nstrand
                # # Try truncating concentric neutral resistance, to match Kersting example 4.2 output
                # factor = 10.0 ** 2
                # truncated_cn_res = math.trunc(wire.concentric_neutral_resistance * factor) / factor
                # # 
                neutral_resistances.append(wire.concentric_neutral_resistance / k)
                neutral_gmrs.append((wire.concentric_neutral_gmr * k * (conductor_own_neutral_distance ** (k - 1))) ** (1 / k))
    conductor_neutral_distances = []
    for i in range(len(wire_list)):
        temp = []
        for j in range(len(wire_list)):
            if i == j:
                temp.append(conductor_own_neutral_distances[i])
            else:
                temp.append((conductor_distances[i][j]**k - conductor_own_neutral_distances[j]**k)**(1/k))
        conductor_neutral_distances.append(temp)


    _R = np.concatenate((conductor_resistances, neutral_resistances))
    _Z = np.zeros((len(_R), len(_R)), dtype=complex)

    _GMR = np.concatenate((conductor_gmrs, neutral_gmrs))

    all_distances = np.zeros((len(_R), len(_R)))
    for i, wire1 in enumerate(wire_list):
        for j, wire2 in enumerate(wire_list):
            if wire1.phase != "N" and wire2.phase != "N":
                all_distances[i][j] = conductor_distances[i][j]
            if wire1.phase != "N":
                all_distances[i][num_non_neutral+j] = conductor_neutral_distances[i][j]
            if wire2.phase != "N":
                all_distances[num_non_neutral+i][j] = conductor_neutral_distances[j][i]
            all_distances[num_non_neutral+i][num_non_neutral+j] = conductor_distances[i][j]

    for i in range(len(_R)):
        for j in range(len(_R)):
            if i == j:
                _Z[i, j] = calc_Zii(_R[i], _GMR[i], True)
            else:
                _D_ij = all_distances[i][j]
                _Z[i, j] = calc_Zij(_D_ij, True)
                
    # Evaluate Zij, Zin, Znj, Znn
    _Zij = _Z[:len(_R)//2, :len(_R)//2]
    _Zin = _Z[:len(_R)//2, len(_R)//2:]
    _Znj = _Z[len(_R)//2:, :len(_R)//2]
    _Znn = _Z[len(_R)//2:, len(_R)//2:]
    return kron_reduction(_Zij, _Zin, _Znj, _Znn)

def compute_triplex_impedance_matrix(
    wire_list, freq=60, resistivity=100, kron_reduce=True
):
    wire_map = {'1':0,'2':1,'N':2}
    matrix = [[0 for i in range(3)] for j in range(3)]
    d12 = 0
    d1n = 0
    distances_mapped = False
    for w in wire_list:
        if w.diameter is not None and w.insulation_thickness is not None:
            d12 = (w.diameter + 2 * w.insulation_thickness) / 12.0 #Convert from inches to feet
            d1n = (w.diameter + w.insulation_thickness) / 12.0 #Convert from inches to feet
            distances_mapped = True
            break

    for i in range(len(wire_list)):
        for j in range(len(wire_list)):
            if i == j:
                z = 0
                if (
                    wire_list[i].resistance is not None
                    and wire_list[i].gmr is not None
                ):
                    z = calc_Zii(wire_list[i].resistance, wire_list[i].gmr, False)
                else:
                    logger.debug("Warning: resistance or GMR is missing from wire")

                if wire_list[i].phase is not None:
                    index = wire_map[wire_list[i].phase]
                    matrix[index][index] = z
                else:
                    logger.debug("Warning: phase missing from wire")

            else:
                z = 0
                if (
                    wire_list[i].phase is not None
                    and wire_list[j].phase is not None
                    and distances_mapped
                ):
                    if wire_list[i].phase == "N" or wire_list[j].phase == "N":
                        z = calc_Zij(d1n, False)
                    else:
                        z = calc_Zij(d12, False)
                    index1 = wire_map[wire_list[i].phase]
                    index2 = wire_map[wire_list[j].phase]
                    matrix[index1][index2] = z# / 1609.344  # ohms per meter

                else:
                    # import pdb; pdb.set_trace()
                    logger.debug(
                        "Warning phase missing from wire, or Insulation_thickness/diameter not set"
                    )
    
    if kron_reduce:
        # Evaluate Zij, Zin, Znj, Znn
        matrix = np.array(matrix)
        matrix_ij = matrix[:2, :2]
        matrix_in = matrix[:2, 2:]
        matrix_nj = matrix[2:, :2]
        matrix_nn = matrix[2:, 2:]
        matrix = kron_reduction(matrix_ij, matrix_in, matrix_nj, matrix_nn)

    return matrix

resistance_of_dirt_overhead = 0.09530 #ohms/mile
resistance_of_dirt_underground = 0.09327 #ohms/mile

resistivity_thing_overhead = 7.93402#ohms/mile
resistivity_thing_underground = 7.95153#ohms/mile

def calc_Zii(r_i, GMRi, is_underground, resistivity = 100, freq = 60):
    #Kersting 4.4.1 pg82-83
    # returns Zii in ohms/mile

    if is_underground:
        resistance_of_dirt = resistance_of_dirt_underground
        resistivity_thing = resistivity_thing_underground
    else:
        resistance_of_dirt = resistance_of_dirt_overhead
        resistivity_thing = resistivity_thing_overhead
    
    Zii = r_i + resistance_of_dirt + 1j * 0.12134 * (np.log(1 / GMRi) + resistivity_thing)
    return Zii

def calc_Zij(Dij, is_underground, resistivity = 100, freq = 60):
    #Kersting 4.4.2 pg82-83
    # returns Zij in ohms/mile

    if is_underground:
        resistance_of_dirt = resistance_of_dirt_underground
        resistivity_thing = resistivity_thing_underground
    else:
        resistance_of_dirt = resistance_of_dirt_overhead
        resistivity_thing = resistivity_thing_overhead

    Zij = resistance_of_dirt + 1j * 0.12134 * (np.log(1 / Dij) + resistivity_thing)
    return Zij

def kron_reduction(Zij, Zin, Znj, Znn):
    #  _r = Zij.shape[0]
    #  _c = Zij.shape[1]
    if hasattr(Znn, "__len__"):
        Znn_inv = np.linalg.inv(Znn)
    else:
        Znn_inv = Znn ** -1
    _tempZ = np.dot(np.dot(Zin, Znn_inv), Znj)
    Zabc = Zij - _tempZ
    matrix = Zabc.tolist()
    return matrix
