import logging
import numpy as np
import re
import math

logger = logging.getLogger(__name__)

remove_nonnum = re.compile(r'[^\d.]+')

lookup = ["A", "B", "C", "N", "E"]
num_dists = len(lookup)

rev_lookup = {"A": 0, "B": 1, "C": 2, "N": 3, "E": 4}

#####################
#####################
# All terms, eqns and figures are from Kersting 3rd Edition unless noted otherwise.
# Chapter 4 - Series impednace
# Chapter 5 - Shunt admittance
#####################
#####################

def compute_overhead_spacing(spacing_config, conductors, default_height=30):
    max_dist = -100
    max_from = -1
    max_to = -1
    distances = [[-1 for i in range(num_dists)] for j in range(num_dists)]

    for i in range(num_dists):
        for j in range(i + 1, num_dists):
            name = "distance_%s%s" % (lookup[i], lookup[j])
            try:
                spacing_config[name] = remove_nonnum.sub('', spacing_config[name])
                dist = float(spacing_config[name])
                distances[i][j] = dist
                distances[j][i] = dist
                distances[i][i] = 0
                distances[j][j] = 0
                if dist > max_dist and i < (num_dists - 1) and j < (num_dists - 1):
                    max_dist = dist
                    max_from = i
                    max_to = j
            except AttributeError:
                pass
    
    n_entries = num_dists ** 2
    for i in range(num_dists):
        for j in range(num_dists):
            if distances[i][j] == -1:
                n_entries = n_entries - 1
    n_entries = int(math.sqrt(n_entries))
    has_earth = max(distances[:][-1]) > -1

    if has_earth:
        n_entries = n_entries - 1

    if n_entries <= 0:
        logger.debug("Warning: No elements included in spacing")

    if n_entries == 1:
        for w in conductors:
            w.X = 0
            if has_earth:
                index = rev_lookup[w.phase]
                w.Y = distances[index][-1] * 0.3048 # convert from feet to meters
            else:
                w.Y = default_height * 0.3048 # convert from feet to meters

    if n_entries == 2:  # If only two wires and no ground distances given assume they are vertically in line
        tmp_map = {}
        if max_dist == 0:
            cnt = 0
            logger.warning("Spacing distance is 0 - using default positions")
            for w in conductors:
                w.X = 0
                w.Y = default_height + 2 * cnt
                cnt += 1

        else:
            for w in conductors:
                index = rev_lookup[w.phase]
                if index == max_from:
                    tmp_map[w.phase] = (0, 0)
                if index == max_to:
                    tmp_map[w.phase] = (0, 0 - max_dist)

            for w in conductors:
                non_rotated = np.array(tmp_map[w.phase])
                if has_earth:
                    # Rotate then translate
                    h = distances[max_from][-1] - distances[max_to][-1]
                    theta = math.acos(h / float(max_dist))
                    rotation = np.array(
                        [
                            [math.cos(theta), -1 * math.sin(theta)],
                            [math.sin(theta), math.cos(theta)],
                        ]
                    )
                    final = rotation.dot(non_rotated)
                    final[1] = final[1] + distances[max_from][-1]
                else:
                    final = non_rotated
                    final[1] = final[1] + default_height
                w.X = float(final[0])
                w.Y = float(final[1])

    if n_entries == 3:  # If there are three wires and no ground distances assume the furthest appart are on a horizontal axis.
        tmp_map = {}
        try:
            for w in conductors:
                index = rev_lookup[w.phase]
                if index == max_from:
                    tmp_map[w.phase] = [(0, 0)]
                elif index == max_to:
                    tmp_map[w.phase] = [(0, 0 - max_dist)]

                else:
                    dist_a = distances[index][max_from]
                    dist_b = distances[index][max_to]
                    heron_p = (dist_a + dist_b + max_dist) / 2.0
                    try:
                        x = (
                            2
                            * math.sqrt(
                                heron_p
                                * (heron_p - dist_a)
                                * (heron_p - dist_b)
                                * (heron_p - max_dist)
                            )
                            / max_dist
                        )  # May be +-x as it could be on either side of the max_dist edge
                        y = -1 * math.sqrt(dist_a ** 2 - x ** 2)
                        tmp_map[w.phase] = [(x, y), (-1 * x, y)]
                    except:
                        raise ValueError(
                            "Line Geometry infeasible with distances %f %f %f"
                            % (dist_a, dist_b, max_dist)
                        )

            for w in conductors:
                final = []
                for non_rotated in tmp_map[w.phase]:
                    non_rotated = np.array(non_rotated)
                    if has_earth:
                        index = rev_lookup[w.phase]
                        # Rotate then translate
                        h = distances[max_from][-1] - distances[max_to][-1]
                        theta = math.acos(h / float(max_dist))
                        rotation = np.array(
                            [
                                [math.cos(theta), -1 * math.sin(theta)],
                                [math.sin(theta), math.cos(theta)],
                            ]
                        )
                        final = rotation.dot(non_rotated)
                        final[1] = final[1] + distances[max_from][-1]
                        if final[1] == distances[index][-1]:
                            break

                    else:
                        rotation = np.array(
                            [
                                [math.cos(math.pi / 2), -1 * math.sin(math.pi / 2)],
                                [math.sin(math.pi / 2), math.cos(math.pi / 2)],
                            ]
                        )
                        final = rotation.dot(non_rotated)
                        final[1] = final[1] + default_height
                        break
                w.X = final[0]
                w.Y = final[1]
        except:
            cnt = 0
            logger.warning("Failed to read spacing - using default positions")
            for w in conductors:
                if w.phase.lower() == "n":
                    w.X = 0
                    w.Y = default_height + 2
                else:
                    w.X = cnt * 2
                    w.Y = default_height
                    cnt += 1
    
    if n_entries == 4:  # If there are three wires and no ground distances assume the furthest appart are on a horizontal axis.
        tmp_map = {}
        seen_one = False
        first_x = -10
        first_y = -10
        first_index = -10
        try:
            for w in conductors:
                index = rev_lookup[w.phase]
                if index == max_from:
                    tmp_map[w.phase] = [(0, 0)]
                elif index == max_to:
                    tmp_map[w.phase] = [(0, 0 - max_dist)]

                else:
                    dist_a = distances[index][max_from]
                    dist_b = distances[index][max_to]
                    heron_p = (dist_a + dist_b + max_dist) / 2.0
                    x = (
                        2
                        * math.sqrt(
                            heron_p
                            * (heron_p - dist_a)
                            * (heron_p - dist_b)
                            * (heron_p - max_dist)
                        )
                        / max_dist
                    )  # May be +-x as it could be on either side of the max_dist edge
                    y = -1 * math.sqrt(dist_a ** 2 - x ** 2)
                    if seen_one:
                        # Warning : possible bug in here - needs more testing
                        if (x - first_x) ** 2 + (y - first_y) ** 2 != distances[
                            index
                        ][first_index] ** 2:
                            x = x * -1
                    else:
                        seen_one = True
                        first_x = x
                        first_y = y
                        first_index = index
                    tmp_map[w.phase] = [(x, y)]

            for w in conductors:
                final = []
                for non_rotated in tmp_map[w.phase]:
                    non_rotated = np.array(non_rotated)
                    if has_earth:
                        index = rev_lookup[w.phase]
                        # Rotate then translate
                        h = distances[max_from][-1] - distances[max_to][-1]
                        theta = math.acos(h / float(max_dist))
                        rotation = np.array(
                            [
                                [math.cos(theta), -1 * math.sin(theta)],
                                [math.sin(theta), math.cos(theta)],
                            ]
                        )
                        final = rotation.dot(non_rotated)
                        final[1] = final[1] + distances[max_from][-1]
                        if final[1] == distances[index][-1]:
                            break

                    else:
                        rotation = np.array(
                            [
                                [math.cos(math.pi / 2), -1 * math.sin(math.pi / 2)],
                                [math.sin(math.pi / 2), math.cos(math.pi / 2)],
                            ]
                        )
                        final = rotation.dot(non_rotated)
                        final[1] = final[1] + default_height
                        break
                w.X = final[0]
                w.Y = final[1]
        except:
            cnt = 0
            logger.warning("Failed to read spacing - using default positions")
            for w in conductors:
                if w.phase.lower() == "n":
                    w.X = 0
                    w.Y = default_height + 2
                else:
                    w.X = cnt * 2
                    w.Y = default_height
                    cnt += 1
    
    return np.array(distances)

# Assume all wires are 6 feet under by default
default_ul_wire_depth = 6
default_ul_wire_spacing = 0.5

def compute_underground_spacing(outer_diameters, spacing_config, conductors):
    distances = [[-1 for i in range(num_dists)] for j in range(num_dists)]
    for i in range(num_dists):
        for j in range(i + 1, num_dists):
            name = "distance_%s%s" % (lookup[i], lookup[j])
            try:
                spacing_config[name] = remove_nonnum.sub('', spacing_config[name])
                dist = float(spacing_config[name])
                if dist == 0:
                    # A distance of zero was given, which is not accepted. Silently switching to default
                    # TODO proper error handling in this case
                    dist = (outer_diameters[i % len(outer_diameters)] + outer_diameters[j % len(outer_diameters)]) / 2
                distances[i][j] = dist
                distances[j][i] = dist
                distances[i][i] = 0
                distances[j][j] = 0
            except AttributeError:
                pass

    n_entries = num_dists ** 2
    i_index = 0
    j_index = 0
    for i in range(num_dists):
        for j in range(num_dists):
            if distances[i][j] == -1:
                n_entries = n_entries - 1
            elif distances[i][j] != 0:
                i_index = i
                j_index = j
    n_entries = int(math.sqrt(n_entries))

    if n_entries == 2:
        if distances[i_index][j_index] != 0:
            is_seen = False
            for w in conductors:
                if is_seen:
                    w.X = distances[i_index][j_index]
                    w.Y = -default_ul_wire_depth
                else:
                    w.X = 0
                    w.Y = -default_ul_wire_depth
                    is_seen = True
        else:
            logger.warning(
                "Spacing distance is 0 - using default positions"
            )
            cnt = 0
            for w in conductors:
                w.X = default_ul_wire_spacing * cnt
                w.Y = -default_ul_wire_depth
                cnt += 1

    if n_entries == 3:  # make longest side on bottom to form a triangle
        first = -1
        middle = -1
        last = -1
        max = -1
        total = 0
        try:
            for i in range(num_dists):
                for j in range(i + 1, num_dists):
                    if distances[i][j] != -1:
                        total = total + distances[i][j]
                        if distances[i][j] > max:
                            max = distances[i][j]
                            first = i
                            last = j

            for i in range(num_dists):
                if (
                    i != first
                    and i != last
                    and distances[i][first] != -1
                ):
                    middle = i
            heron_s = total / 2.0
            heron_area = heron_s
            for i in range(n_entries):
                for j in range(i + 1, n_entries):
                    if distances[i][j] != -1:
                        heron_area = heron_area * (
                            heron_s - distances[i][j]
                        )
            logger.debug(heron_area)
            heron_area = math.sqrt(heron_area)
            height = heron_area * 2 / (max * 1.0)
            for w in conductors:
                if w.phase == lookup[first]:
                    w.X = 0
                    w.Y = -default_ul_wire_depth
                elif w.phase == lookup[last]:
                    w.X = max
                    w.Y = -default_ul_wire_depth
                else:
                    w.Y = -default_ul_wire_depth + height
                    w.X = math.sqrt(
                        distances[middle][first] ** 2 - height ** 2
                    )

        except:
            logger.warning(
                "Failed to read spacing - using default positions"
            )
            cnt = 0
            for w in conductors:
                w.X = default_ul_wire_spacing * cnt
                w.Y = -default_ul_wire_depth
                cnt += 1

    # TODO: underground lines with 4 conductors ABCN. Use Heron's formula for there too in a similar way (works since we have pairwise distances)

    if n_entries == 4:  # make longest side on bottom to form a triangle
        max_dist = -100
        max_from = -1
        max_to = -1
        try:
            for i in range(n_entries):
                for j in range(n_entries):
                    if distances[i][j] > max_dist:
                        max_dist = distances[i][j]
                        max_from = i
                        max_to = j

            seen_one = False
            first_x = -10
            first_y = -10
            first_i = -1
            for w in conductors:
                i = rev_lookup[w.phase]
                if i != max_to and i != max_from:
                    heron_s = (
                        max_dist
                        + distances[i][max_to]
                        + distances[i][max_from]
                    ) / 2.0
                    heron_area = (
                        heron_s
                        * (heron_s - max_dist)
                        * (heron_s - distances[i][max_to])
                        * (heron_s - distances[i][max_from])
                    )
                    heron_area = math.sqrt(heron_area)
                    height = heron_area * 2 / (max_dist * 1.0)
                    if not seen_one:
                        w.Y = -default_ul_wire_depth + height
                        w.X = math.sqrt(
                            distances[i][max_from] ** 2
                            - height ** 2
                        )
                        seen_one = True
                        first_x = w.X
                        first_y = w.Y
                        first_i = i

                    else:
                        # Warning: possible bug here - needs extra testing.
                        w.Y = -default_ul_wire_depth + height
                        w.X = math.sqrt(
                            distances[i][max_from] ** 2
                            - height ** 2
                        )
                        if (w.X - first_x) ** 2 + (
                            w.Y - first_y
                        ) ** 2 != distances[i][first_i] ** 2:
                            w.Y = -default_ul_wire_depth - height
                elif i == max_from:
                    w.X = 0
                    w.Y = -default_ul_wire_depth
                elif i == max_to:
                    w.X = max_dist
                    w.Y = -default_ul_wire_depth

        except:
            logger.warning(
                "Failed to read spacing - using default positions"
            )
            cnt = 0
            for w in conductors:
                w.X = default_ul_wire_spacing * cnt
                w.Y = -default_ul_wire_depth
                cnt += 1
                                    

    return np.array(distances)

def compute_underground_capacitance(wire_list):
    capacitance_matrix =[[0+0j for i in range(3)] for j in range(3)]

    for index in range(len(wire_list)):
        wire = wire_list[index]
        if wire.phase == "N":
            #No need to calculate shunt values for independent neutral wire.
            continue

        # Radius of circle passing through neutral strands (see figure 4.11 or 5.4).
        R_b = (wire.outer_diameter - wire.concentric_neutral_diameter) / 2

        #phase conductor radius
        RD_c = wire.conductor_diameter / 2

        if hasattr(wire, "_shield_gmr") and wire.shield_gmr != 0:
            #Eqn 5.32
            V_p1 = np.log(R_b / RD_c)
        else:
            #neutral conductor radius
            RD_s = wire.concentric_neutral_diameter / 2

            #number of neutral strands
            k = wire.concentric_neutral_nstrand

            #Eqn 5.30
            V_p1 = np.log(R_b / RD_c) - (1 / k) * np.log(k * RD_s / R_b)

        #Eqn 5.31 & 5.32
        y_ag = 77.3619 * 1j * 1e-6 / V_p1

        #Shunt values go down the diagonal in wire order.
        capacitance_matrix[index][index] = y_ag
    
    #Shunt capacitance is applied on either side of the line.
    for i in range(len(capacitance_matrix)):
        for j in range(len(capacitance_matrix[0])):
            capacitance_matrix[i][j] = capacitance_matrix[i][j] / 2

    return capacitance_matrix

def compute_overhead_capacitance(wire_list, distances, freq = 60):
    neutral_index = rev_lookup["N"]
    earth_index = rev_lookup["E"]

    #See definitions below eqn 5.5
    S = np.zeros((4, 4), dtype=complex)
    RD = np.zeros(4)

    has_neutral = False
    indexes = []
    for i_wire in wire_list:
        if i_wire.diameter == None:
            return None

        if i_wire.phase == "N":
            has_neutral = True

        i = rev_lookup[i_wire.phase]
        indexes.append(i)
        S[i, i] = 2 * distances[i][i]
        RD[i] = i_wire.diameter / 2

        for j_wire in wire_list:
            j = rev_lookup[j_wire.phase]

            phase_phase_dist = distances[i][j]
            phase_neutral_dist = distances[i][neutral_index]
            phase_earth_dist = distances[i][earth_index]
            neutral_earth_dist = distances[neutral_index][earth_index]

            phasepair = i_wire.phase + j_wire.phase 

            if i == j:
                _horizDist = 0
                _vertDist = 2 * phase_earth_dist
            if phasepair in ["AB", "BA", "AC", "CA", "BC", "CB"]:
                _horizDist = phase_phase_dist
                _vertDist = 2 * phase_earth_dist
            elif phasepair in ["AN", "NA", "BN", "NB", "CN", "NC"]:
                _horizDist = (phase_neutral_dist ** 2 - (phase_earth_dist - neutral_earth_dist) ** 2) ** 0.5
                _vertDist = phase_earth_dist + neutral_earth_dist

            S[i, j] = (_horizDist ** 2 + _vertDist ** 2) ** 0.5

    #See eqn's 5.9 and 5.10.
    reduced_distances = distances[:, indexes][indexes, :]
    reduced_RD = RD[indexes]
    reduced_S = S[:, indexes][indexes, :]

    #Assumes distances matrix is zero along diag so we don't overwrite RD
    S_divisor = np.diag(reduced_RD) + reduced_distances
    P_primitive = 11.17689 * np.log(np.divide(reduced_S, S_divisor))

    if has_neutral:
        #Eqn 5.12 and 5.13
        phs_cnt = len(wire_list) - 1

        Pij = P_primitive[:phs_cnt, :phs_cnt]
        Pin = P_primitive[:phs_cnt, phs_cnt, np.newaxis]
        Pnj = P_primitive[phs_cnt, :phs_cnt, np.newaxis].T
        Pnn = P_primitive[phs_cnt, phs_cnt]

        P_abc = kron_reduction(Pij, Pin, Pnj, Pnn)
    else:
        P_abc = P_primitive[0:len(wire_list), 0:len(wire_list)]

    C = np.linalg.inv(P_abc)
    
    #Eqn 5.15
    Y = 2 * math.pi * freq * 1e-6 * 1j * C

    #Shunt capacitance is applied on either side of the line.
    Y = Y / 2

    return [[Y[i, j] for i in range(Y.shape[1])] for j in range(Y.shape[0])]

def compute_overhead_impedance(wire_list, distances, freq=60, resistivity=100, kron_reduce=True):
    matrix = [[0 for i in range(4)] for j in range(4)]
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
                    index1 = index2 = rev_lookup[wire_list[i].phase]
                    matrix[index1][index2] = z
                else:
                    logger.debug("Warning: phase missing from wire")

            else:
                z = 0
                if distances[i][j] is not None:
                    distance = distances[i][j]
                    z = calc_Zij(distance, False)
                else:
                    logger.debug("Warning X or Y values missing from wire")
                    
                if (
                    wire_list[i].phase is not None
                    and wire_list[j].phase is not None
                ):
                    index1 = rev_lookup[wire_list[i].phase]
                    index2 = rev_lookup[wire_list[j].phase]
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
def compute_underground_impedance(wire_list, distances, freq=60, resistivity=100):
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
                neutral_gmrs.append(wire.shield_gmr if wire.shield_gmr != 0 else ((wire.shield_diameter - (wire.shield_thickness / 1000)) / (12 * 2)))
                conductor_own_neutral_distances.append((wire.shield_diameter - wire.shield_thickness) / (12 * 2))
            else:
                conductor_own_neutral_distance = (wire.outer_diameter - wire.concentric_neutral_diameter) / (12 * 2)
                conductor_own_neutral_distances.append(conductor_own_neutral_distance)
                k = wire.concentric_neutral_nstrand
                neutral_resistances.append(wire.concentric_neutral_resistance / k)
                neutral_gmrs.append((wire.concentric_neutral_gmr * k * (conductor_own_neutral_distance ** (k - 1))) ** (1 / k))

    conductor_neutral_distances = []
    for i in range(len(wire_list)):
        temp = []
        for j in range(len(wire_list)):
            if i == j:
                temp.append(conductor_own_neutral_distances[i])
            else:
                temp.append((distances[i][j]**k - conductor_own_neutral_distances[j]**k)**(1/k))
        conductor_neutral_distances.append(temp)

    _R = np.concatenate((conductor_resistances, neutral_resistances))
    _Z = np.zeros((len(_R), len(_R)), dtype=complex)

    _GMR = np.concatenate((conductor_gmrs, neutral_gmrs))

    all_distances = np.zeros((len(_R), len(_R)))
    for i, wire1 in enumerate(wire_list):
        for j, wire2 in enumerate(wire_list):
            if wire1.phase != "N" and wire2.phase != "N":
                all_distances[i][j] = distances[i][j]
            if wire1.phase != "N":
                all_distances[i][num_non_neutral+j] = conductor_neutral_distances[i][j]
            if wire2.phase != "N":
                all_distances[num_non_neutral+i][j] = conductor_neutral_distances[j][i]
            all_distances[num_non_neutral+i][num_non_neutral+j] = distances[i][j]

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

def compute_triplex_impedance(
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
    if hasattr(Znn, "__len__"):
        Znn_inv = np.linalg.inv(Znn)
    else:
        Znn_inv = Znn ** -1
    _tempZ = np.dot(np.dot(Zin, Znn_inv), Znj)
    Zabc = Zij - _tempZ
    matrix = Zabc.tolist()
    return matrix

line_direct_lookup = {
    "11": (0, 0),
    "12": (0, 1), 
    "13": (0, 2), 
    "21": (1, 0), 
    "22": (1, 1), 
    "23": (1, 2), 
    "31": (2, 0), 
    "32": (2, 1), 
    "33": (2, 2)
}

def try_load_direct_line_impedance(line_config):
    #It is possible to specify the line impedance directly in Z matrix form:
    #http://gridlab-d.shoutwiki.com/wiki/Power_Flow_User_Guide#Line_configuration_properties

    impedance_matrix = None
    for property_number in line_direct_lookup.keys():
        prop_name = f"z{property_number}"
        if not hasattr(line_config, prop_name):
            continue

        if impedance_matrix == None:
            impedance_matrix = [[0 for i in range(3)] for j in range(3)]
        
        i, j = line_direct_lookup[property_number]

        impedance_matrix[i][j] = complex(line_config[prop_name])
    
    return impedance_matrix

def try_load_direct_line_capacitance(line_config):
    #It is possible to specify the line capacitance directly in Z matrix form:
    #http://gridlab-d.shoutwiki.com/wiki/Power_Flow_User_Guide#Line_configuration_properties

    capacitance_matrix = None
    for property_number in line_direct_lookup.keys():
        prop_name = f"c{property_number}"
        if not hasattr(line_config, prop_name):
            continue

        if capacitance_matrix == None:
            capacitance_matrix = [[0 for i in range(3)] for j in range(3)]
        
        i, j = line_direct_lookup[property_number]

        capacitance_matrix[i][j] = complex(line_config[prop_name])
    
    return capacitance_matrix