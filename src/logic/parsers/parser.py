"""Parses all the power grid elements from a RAW file to use in the power flow solver.

    Author(s): Victoria Ciplickas

    Date Created: 2019-06
    Date Modified: 2019-03-09

    Description: Takes in a .raw file and returns two dictionaries: the information in lists of objects keyed to the
    data name in a dictionary and a nested dictionary allowing for searching for a specific object.

"""

import time

from models.Buses import Bus

import parsers.data_classes as data_classes

import parsers.Data as Data  # pared down/modified version of data.py from
# https://github.com/GOCompetition/Evaluation/blob/master/data.py
from lib.global_vars import global_vars


# also see this document for provided values for each type of entity:
# https://gocompetition.energy.gov/sites/default/files/SCOPF_Problem_Formulation__Challenge_1_20190402.pdf

def almostEqual(d1, d2, epsilon=10 ** -6):
    return (abs(d2 - d1) < epsilon)


def compute_bmin_bmax(n1, n2, n3, n4, n5, n6, n7, n8,
                      b1, b2, b3, b4, b5, b6, b7, b8):
    b_min = 0.0
    b_max = 0.0
    b1 = float(n1) * b1
    b2 = float(n2) * b2
    b3 = float(n3) * b3
    b4 = float(n4) * b4
    b5 = float(n5) * b5
    b6 = float(n6) * b6
    b7 = float(n7) * b7
    b8 = float(n8) * b8
    for b in [b1, b2, b3, b4, b5, b6, b7, b8]:
        if b > 0.0:
            b_max += b
        elif b < 0.0:
            b_min += b
        else:
            break
    return (b_min, b_max)


from enum import Enum


class GenType(Enum):
    Generation = 1
    Continuous_SS = 2
    Discrete_SS = 3
    FACTs = 4
    VSCHVDC = 5


def parse_raw(rawfile):
    start = time.time()
    data = Data.Data()
    data.read(rawfile)

    non_empty_bus_set = set()
    all_case_data = {}
    integrated_data = {}
    search_case_data = {}
    gen_bus_keys = {}

    # toggle this to store unused data types or not
    integrate = True

    # ---------- case identification ----------
    all_case_data['all_case_id'] = []

    case_id = data_classes.Case_id_data(data.raw.case_identification.ic,
                                        data.raw.case_identification.sbase,
                                        data.raw.case_identification.rev,
                                        data.raw.case_identification.xfrrat,
                                        data.raw.case_identification.nxfrat,
                                        data.raw.case_identification.basfrq,
                                        data.raw.case_identification.record_2,
                                        data.raw.case_identification.record_3)

    all_case_data['all_case_id'].append(case_id)
    search_case_data['case_id'] = case_id

    version = case_id.rev
    sbase = case_id.sbase

    #  ----------buses ----------
    PV_list = []
    all_case_data['all_buses'] = []
    search_case_data['buses'] = {}
    integrated_data['buses'] = []
    offline_bus = set()
    for bus in data.raw.get_buses():
        # adding all the info to a generic data class
        if version in (32, 30):
            b = data_classes.Bus_data(bus.i, bus.name, bus.baskv, bus.ide, bus.area, bus.zone,
                                      bus.owner, bus.vm, bus.va)
        elif version in (33, 34):
            b = data_classes.Bus_data(bus.i, bus.name, bus.baskv, bus.ide, bus.area, bus.zone,
                                      bus.owner, bus.vm, bus.va, bus.nvhi, bus.nvlo, bus.evhi, bus.evlo)

        all_case_data['all_buses'].append(b)
        search_case_data['buses'][bus.i] = b

        # adding to pwer flow/lab specific data classes
        if bus.ide == 2:
            PV_list.append(bus.i)
        if bus.ide == 4:
            offline_bus.add(bus.i)
        else:
            integrated_data['buses'].append(b.integrate())

    # ---------- generators ----------
    all_case_data['all_ns_generators'] = []
    all_case_data['all_slack_generators'] = []

    search_case_data['ns_generators'] = {}
    search_case_data['slack_generators'] = {}

    integrated_data['slack'] = []
    integrated_data['generators'] = []

    # loads list
    all_case_data['all_loads'] = []
    search_case_data['loads'] = {}

    integrated_data['loads'] = []

    # for finding and modifying later
    slack_idx = 0
    slack_dic = {}

    gen_dic = {}

    # set of voltge control buses
    voltage_controlling_bus = set()
    voltage_controlled_bus = set()

    non_added_gens = []

    for gen in data.raw.get_generators():

        if gen.i in data.raw.slack_buses:  # --- slack generators ---
            # adding to generic data class
            ang = search_case_data['buses'][gen.i].va
            g = data_classes.Slack_generator_data(gen.i, gen.id, gen.pg, gen.qg, gen.qt, gen.qb, gen.vs,
                                                  gen.ireg, gen.mbase, gen.zr, gen.zx, gen.rt,
                                                  gen.xt, gen.gtap, gen.stat, gen.rmpct, gen.pt,
                                                  gen.pb, gen.wmod, gen.wpf, ang, gen.o1, gen.o2, gen.o3,
                                                  gen.o4, gen.f1, gen.f2, gen.f3, gen.f4)

            if gen.i not in offline_bus and gen.stat == True:
                # adding to power flow specific data class
                if gen.i not in search_case_data['slack_generators'].keys():
                    integrated_data['slack'].append(g.integrate())
                    slack_dic[g.i] = slack_idx
                    slack_idx += 1
                else:
                    integrated_data['slack'][slack_dic[gen.i]].Pinit += gen.pg / sbase
                non_empty_bus_set.add(int(gen.i))

                all_case_data['all_slack_generators'].append(g)
                search_case_data['slack_generators'][g.i] = g

        else:  # --- conventional generators ---

            g = data_classes.Generator_data(gen.i, gen.id, gen.pg, gen.qg, gen.qt, gen.qb, gen.vs,
                                            gen.ireg, gen.mbase, gen.zr, gen.zx, gen.rt,
                                            gen.xt, gen.gtap, gen.stat, gen.rmpct, gen.pt,
                                            gen.pb, gen.wmod, gen.wpf, gen.o1, gen.o2, gen.o3,
                                            gen.o4, gen.f1, gen.f2, gen.f3, gen.f4)

            if gen.i not in search_case_data['ns_generators'].keys():
                search_case_data['ns_generators'][gen.i] = [g]
            else:
                search_case_data['ns_generators'][gen.i] += [g]
            # If the generator is in bus list or if the generator is a SVC or FACTS device
            if (g.i in PV_list) and (g.stat == True):
                non_empty_bus_set.add(g.i)
                # Deal with generators with qb equal qt
                if almostEqual(g.qt, g.qb) and (gen.wmod != 2):
                    l = g.integrate(False)
                    g.qg = gen.qt
                    integrated_data['loads'].append(l)
                elif (g.pg == 0 and g.qt == 0 and g.qb == 0):
                    g.qg = gen.qt
                    continue
                else:
                    if g.i in voltage_controlling_bus:
                        # print('Due to another generator on %i generator location, parameters are appended' % g.i)
                        idx = gen_dic[g.i]
                        integrated_data['generators'][idx].P += gen.pg / global_vars.MVAbase
                        integrated_data['generators'][idx].Pmax += gen.pt / global_vars.MVAbase
                        integrated_data['generators'][idx].Pmin += gen.pb / global_vars.MVAbase
                        integrated_data['generators'][idx].Qmax += gen.qt / global_vars.MVAbase
                        integrated_data['generators'][idx].Qmin += gen.qb / global_vars.MVAbase
                        integrated_data['generators'][idx].Qinit += gen.qg / global_vars.MVAbase
                        integrated_data['generators'][idx].RMPCT += gen.rmpct
                        # check for discrepencies
                        if integrated_data['generators'][idx].RemoteBus != gen.ireg:
                            print("Discrepancy found in remote bus (%d, %d) for generators on the same bus: %i" % (
                                integrated_data['generators'][idx].RemoteBus, gen.ireg, gen.i))
                            # If the new generator is controlling self. Make everyone control that
                            # if gen.ireg == 0 or gen.ireg == gen.i:
                            #    integrated_data['generators'][idx].RemoteBus = gen.ireg
                            #    # TODO Remove voltage controlled node and add new
                        if integrated_data['generators'][idx].Vset != gen.vs:
                            print("Discrepancy found in Vset (%f, %f) for generators on the same bus: %i" % (
                                integrated_data['generators'][idx].Vset, gen.vs, gen.i))
                    else:
                        gen_dic[g.i] = len(integrated_data['generators'])
                        integrated_data['generators'].append(g.integrate())
                        voltage_controlling_bus.add(g.i)

                    if gen.ireg == 0:
                        voltage_controlled_bus.add(gen.i)
                    else:
                        voltage_controlled_bus.add(gen.ireg)
            else:
                non_added_gens += [g]

        all_gens = sorted(search_case_data['ns_generators'].keys())
        all_case_data['all_ns_generators'] = all_gens


    # ---------- switched shunts ----------
    all_case_data['all_switched_shunts'] = []
    search_case_data['switched_shunts'] = {}
    integrated_data['shunts'] = []
    for sshunt in data.raw.get_switched_shunts():

        ss = data_classes.Switched_shunt_data(sshunt.i, sshunt.modsw, sshunt.adjm,
                                              sshunt.stat, sshunt.vswhi, sshunt.vswlo, sshunt.swrem,
                                              sshunt.rmpct, sshunt.rmidnt, sshunt.binit,
                                              sshunt.n1, sshunt.n2, sshunt.n3, sshunt.n4, sshunt.n5,
                                              sshunt.n6, sshunt.n7, sshunt.n8,
                                              sshunt.b1, sshunt.b2, sshunt.b3, sshunt.b4,
                                              sshunt.b5, sshunt.b6, sshunt.b7, sshunt.b8)
        if ss.i not in search_case_data['switched_shunts'].keys():
            search_case_data['switched_shunts'][ss.i] = [ss]
        else:
            search_case_data['switched_shunts'][ss.i] += [ss]
        if ss.i == ss.swrem:
            ss.swrem = 0

        if (sshunt.i not in offline_bus) and (sshunt.stat == 1):

            non_empty_bus_set.add(ss.i)
            # Shunt-type (modsw) LINE-SHUNT = 8 SS-LOCKED = 0 SS-DISCRETE-Volt = 3
            # SS-DISCRETE-Q = 4 SS-Continuous =2

            if sshunt.modsw == 2:  # treat like generator
                bmin, bmax = compute_bmin_bmax(sshunt.n1, sshunt.n2, sshunt.n3, sshunt.n4, sshunt.n5,
                                               sshunt.n6, sshunt.n7, sshunt.n8,
                                               sshunt.b1, sshunt.b2, sshunt.b3, sshunt.b4,
                                               sshunt.b5, sshunt.b6, sshunt.b7, sshunt.b8)
                Qmax = bmax * (sshunt.vswhi ** 2)
                Qmin = bmin * (sshunt.vswhi ** 2)
                Qinit = sshunt.binit * (sshunt.vswhi ** 2)
                rmpct = sshunt.rmpct
                if sshunt.i in voltage_controlling_bus:
                    # print(voltage_controlling_bus)
                    # print('Due to a generator on %i SVC location, parameters are appended' % sshunt.i)
                    gen_id = gen_dic[sshunt.i]
                    # print(gen_id)
                    integrated_data['generators'][gen_id].Qmax += Qmax / global_vars.MVAbase
                    integrated_data['generators'][gen_id].Qmin += Qmin / global_vars.MVAbase
                    integrated_data['generators'][gen_id].Qinit += Qinit / global_vars.MVAbase
                    integrated_data['generators'][gen_id].RMPCT += rmpct
                    if integrated_data['generators'][gen_id].RemoteBus != ss.swrem:
                        print("Discrepency between control buses in shunts for bus ", ss.i)
                        # if integrated_data['generators'][gen_id].RemoteBus ==0:
                        #    integrated_data['generators'][gen_id].RemoteBus = ss.swrem

                else:
                    Pmax = 0
                    Pmin = 0
                    P = 0
                    flag_Qinit = False
                    Vset = (sshunt.vswhi + sshunt.vswlo) / 2.0
                    Id = "ContinuousShunt"
                    remoteBus = sshunt.swrem
                    zr = 0.
                    zx = 0.
                    rt = 0.
                    rx = 0.
                    gtap = 1.
                    stat = sshunt.stat
                    wmod = 0
                    wpf = 1
                    ss = data_classes.Generator_data(sshunt.i, Id, P,
                                                     Qinit, Qmax, Qmin, Vset, remoteBus, global_vars.MVAbase,
                                                     zr, zx, rt, rx, gtap, stat, rmpct, Pmax, Pmin,
                                                     wmod, wpf)
                    gen_dic[sshunt.i] = len(integrated_data['generators'])
                    integrated_data['generators'].append(ss.integrate())

                    voltage_controlling_bus.add(sshunt.i)
                    if ss.ireg == 0:
                        voltage_controlled_bus.add(sshunt.i)
                    else:
                        voltage_controlled_bus.add(ss.ireg)

            else:  # treat it like a shunt

                integrated_data['shunts'].append(ss.integrate())

        # add both offline and online shunts in all_case_data
        all_case_data['all_switched_shunts'].append(ss)

    # ---------- fixed shunts  ----------
    all_case_data['all_fixed_shunts'] = []
    search_case_data['fixed_shunts'] = {}

    for fshunt in data.raw.get_fixed_shunts():

        fs = data_classes.Fixed_shunt_data(fshunt.i, fshunt.id, fshunt.status, fshunt.gl,
                                           fshunt.bl)
        all_case_data['all_fixed_shunts'].append(fs)
        search_case_data['fixed_shunts'][(fs.i, fs.id)] = fs

        if (fs.i not in offline_bus) and (fshunt.status == 1) and (fshunt.gl != 0 or fshunt.bl != 0):
            non_empty_bus_set.add(fs.i)
            integrated_data['shunts'].append(fs.integrate())

    # ---------- loads ----------
    for load in data.raw.get_loads():

        l = data_classes.Load_data(load.i, load.id, load.status, load.area, load.zone,
                                   load.pl, load.ql, load.ip, load.iq, load.yp, load.yq,
                                   load.owner, load.scale)
        all_case_data['all_loads'].append(l)
        search_case_data['loads'][(l.i, l.id)] = l
        if (load.i not in offline_bus) and (load.status == 1):
            integrated_data['loads'].append(l.integrate())
            non_empty_bus_set.add(load.i)

    # copied from parser_three, not sure what it does

    # Create the struncture for two Y matrices linear and non-linear

    # Find number of remote share generators

    # ---------- non transformer branches ----------
    all_case_data['all_non_xfmr_branches'] = []
    search_case_data['branches'] = {}

    integrated_data['branches'] = []
    for branch in data.raw.get_nontransformer_branches():
        br = data_classes.Branch_data(branch.i, branch.j, branch.ckt, branch.r, branch.x,
                                      branch.b, branch.ratea, branch.rateb, branch.ratec,
                                      branch.gi, branch.bi, branch.gj, branch.bj, branch.st,
                                      branch.met, branch.len, branch.o1, branch.o2, branch.o3,
                                      branch.o4, branch.f1, branch.f2, branch.f3, branch.f4)
        all_case_data['all_non_xfmr_branches'].append(br)
        search_case_data['branches'][(br.i, br.j, br.ckt)] = br
        if (branch.i not in offline_bus) and (branch.j not in offline_bus) and (branch.st == 1):
            (new_branch, shunt_i, shunt_j) = br.integrate()
            integrated_data['branches'].append(new_branch)
            if shunt_i != None:
                non_empty_bus_set.add(shunt_i.Bus)
                integrated_data['shunts'].append(shunt_i)
            if shunt_j != None:
                non_empty_bus_set.add(shunt_j.Bus)
                integrated_data['shunts'].append(shunt_j)

    # ---------- transformer data ----------

    # --- two-winding tranformers ---
    all_case_data['all_two_xfmrs'] = []
    search_case_data['two_xfmrs'] = {}

    integrated_data['three_xfmrs'] = []
    integrated_data['xfmrs'] = []

    for two_x in data.raw.get_two_xfmrs():
        if version in (33, 34):
            x2 = data_classes.Two_xfmr_data(two_x.i, two_x.j, two_x.k, two_x.ckt, two_x.cw,
                                            two_x.cz, two_x.cm, two_x.mag1, two_x.mag2, two_x.nmetr,
                                            two_x.name, two_x.stat, two_x.o1, two_x.o2, two_x.o3,
                                            two_x.o4, two_x.f1, two_x.f2, two_x.f3, two_x.f4,
                                            two_x.r1_2, two_x.x1_2, two_x.sbase1_2,
                                            two_x.windv1, two_x.nomv1, two_x.ang1, two_x.rata1,
                                            two_x.ratb1, two_x.ratc1, two_x.cod1, two_x.cont1, two_x.rma1, two_x.rmi1,
                                            two_x.vma1, two_x.vmi1, two_x.ntp1, two_x.tab1,
                                            two_x.cr1, two_x.cx1, two_x.windv2, two_x.nomv2,
                                            vecgrp=two_x.vecgrp, cnxa1=two_x.cnxa1)
        else:
            x2 = data_classes.Two_xfmr_data(two_x.i, two_x.j, two_x.k, two_x.ckt, two_x.cw,
                                            two_x.cz, two_x.cm, two_x.mag1, two_x.mag2, two_x.nmetr,
                                            two_x.name, two_x.stat, two_x.o1, two_x.o2, two_x.o3,
                                            two_x.o4, two_x.f1, two_x.f2, two_x.f3, two_x.f4,
                                            two_x.r1_2, two_x.x1_2, two_x.sbase1_2,
                                            two_x.windv1, two_x.nomv1, two_x.ang1, two_x.rata1,
                                            two_x.ratb1, two_x.ratc1, two_x.cod1, two_x.cont1, two_x.rma1, two_x.rmi1,
                                            two_x.vma1, two_x.vmi1, two_x.ntp1, two_x.tab1,
                                            two_x.cr1, two_x.cx1, two_x.windv2, two_x.nomv2)
        all_case_data['all_two_xfmrs'].append(x2)
        search_case_data['two_xfmrs'][(x2.i, x2.j, x2.ckt)] = x2

        if (x2.i not in offline_bus) and (x2.j not in offline_bus):
            new_xfmr2 = data_classes.integrate_2xfmrs(x2, sbase, search_case_data['buses'])
            if new_xfmr2 != None:
                integrated_data['xfmrs'].append(new_xfmr2)

    # --- three winding transformers ---
    all_case_data['all_three_xfmrs'] = []
    search_case_data['three_xfmrs'] = {}
    tempBus = integrated_data['buses']
    largestBusNum = max([ele.Bus for ele in tempBus])
    startNodeThreeWinding = 1000000 + largestBusNum
    for x in data.raw.get_three_xfmrs():

        if version in (33, 34):
            x3 = data_classes.Three_xfmr_data(x.i, x.j, x.k, x.ckt, x.cw, x.cz, x.cm,
                                              x.mag1, x.mag2, x.nmetr, x.name, x.stat, x.o1, x.o2, x.o3,
                                              x.o4, x.f1, x.f2, x.f3, x.f4,
                                              x.r1_2, x.x1_2, x.sbase1_2, x.r2_3, x.x2_3, x.sbase2_3,
                                              x.r3_1, x.x3_1, x.sbase3_1, x.vmstar, x.anstar,
                                              x.windv1, x.nomv1, x.ang1, x.rata1, x.ratb1, x.ratc1, x.cod1,
                                              x.cont1, x.rma1, x.rmi1, x.vma1, x.vmi1, x.ntp1, x.tab1, x.cr1, x.cx1,
                                              x.windv2, x.nomv2, x.ang2, x.rata2, x.ratb2, x.ratc2, x.cod2,
                                              x.cont2, x.rma2, x.rmi2, x.vma2, x.vmi2, x.ntp2, x.tab2, x.cr2, x.cx2,
                                              x.windv3, x.nomv3, x.ang3, x.rata3, x.ratb3, x.ratc3, x.cod3,
                                              x.cont3, x.rma3, x.rmi3, x.vma3, x.vmi3, x.ntp3, x.tab3, x.cr3, x.cx3,
                                              x.vecgrp, x.cnxa1, x.cnxa2, x.cnxa3)
        else:
            x3 = data_classes.Three_xfmr_data(x.i, x.j, x.k, x.ckt, x.cw, x.cz, x.cm,
                                              x.mag1, x.mag2, x.nmetr, x.name, x.stat, x.o1, x.o2, x.o3,
                                              x.o4, x.f1, x.f2, x.f3, x.f4,
                                              x.r1_2, x.x1_2, x.sbase1_2, x.r2_3, x.x2_3, x.sbase2_3,
                                              x.r3_1, x.x3_1, x.sbase3_1, x.vmstar, x.anstar,
                                              x.windv1, x.nomv1, x.ang1, x.rata1, x.ratb1, x.ratc1, x.cod1,
                                              x.cont1, x.rma1, x.rmi1, x.vma1, x.vmi1, x.ntp1, x.tab1, x.cr1, x.cx1,
                                              x.windv2, x.nomv2, x.ang2, x.rata2, x.ratb2, x.ratc2, x.cod2,
                                              x.cont2, x.rma2, x.rmi2, x.vma2, x.vmi2, x.ntp2, x.tab2, x.cr2, x.cx2,
                                              x.windv3, x.nomv3, x.ang3, x.rata3, x.ratb3, x.ratc3, x.cod3,
                                              x.cont3, x.rma3, x.rmi3, x.vma3, x.vmi3, x.ntp3, x.tab3, x.cr3, x.cx3)
        all_case_data['all_three_xfmrs'].append(x3)
        search_case_data['three_xfmrs'][(x3.i, x3.j, x3.k, x3.ckt)] = x3
        if x3.stat != 0:
            new_xfmr3 = data_classes.integrate_3xfmrs(x3, sbase, search_case_data['buses'], -1)
            if new_xfmr3 != []:
                busType = 1
                vmInit = x.vmstar
                vaInit = x.anstar
                'Stat 2-Winding 2 out of service 3 - Winding 3 out of service 4 - winding 1 out of service'
                area = search_case_data['buses'][x3.i].area
                if int(x.stat) == 4:
                    area = search_case_data['buses'][x3.j].area

                integrated_data['buses'].append(Bus(startNodeThreeWinding, busType,
                                                      vmInit, vaInit, area))
                for ele in new_xfmr3:
                    ele.to_bus = startNodeThreeWinding
                startNodeThreeWinding += 1
                integrated_data['xfmrs'] += new_xfmr3

    end = time.time()
    print("Time to parse the file is: %0.5f" % (end - start))

    return integrated_data

