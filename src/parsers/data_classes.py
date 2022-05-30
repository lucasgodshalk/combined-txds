"""Creates instances of power grid elements for use in the solver.

    All variable names are consistent with the PSS/E 32.0 /33 handbook. Made for PSS/E  33/34.

    Author(s): Victoria Ciplickas

    Date Created: 2019-06
    Date Modified: 2019-03-09

"""
from enum import Enum

import numpy as np
import math

from models.Branches import Branches
from models.Buses import Bus
from models.Generators import Generators
from models.Loads import Loads
from models.Slack import Slack
from models.Shunts import Shunts

from lib.global_vars import global_vars

from parsers.parse_transformers import TwoWindingXfmrs, ThreeWindingXfmrs


class GenType(Enum):
    Generation = 1
    Continuous_SS = 2
    Discrete_SS = 3
    FACTs = 4
    VSCHVDC = 5


class Case_id_data:
    def __init__(self, ic, sbase, rev, xfrrat, nxfrat, basfrq, record_2, record_3):
        self.ic = ic
        self.sbase = sbase
        self.rev = rev
        self.xfrrat = xfrrat  # Units of transformer ratings
        self.nxfrat = nxfrat  # Units of ratings of non-transformer branches
        self.basfrq = basfrq  # System base frequency in Hertz
        self.record_2 = record_2
        self.record_3 = record_3


class Bus_data:

    def __init__(self, i, name, baskv, ide, area, zone, owner, vm, va,
                 nvhi=None, nvlo=None, evhi=None, evlo=None):
        self.i = int(i)  # bus number
        self.name = name
        self.baskv = baskv  # Bus base voltage; entered in kV
        self.ide = int(ide)  # Bus type code
        self.area = area
        self.zone = zone
        self.owner = owner
        self.vm = float(vm)  # Bus voltage magnitude; entered in pu
        self.va = va  # Bus voltage phase angle; degrees
        if nvhi != None:
            self.nvlo = nvlo
            self.nvhi = nvhi
            self.evhi = evhi
            self.evlo = evlo

    def __repr__(self):
        return (str(self.i) + ' ' + str(self.name))

    def integrate(self):
        new_bus = Bus(self.i, self.ide, self.vm, self.va, self.area)

        return new_bus


class Load_data:

    def __init__(self, i, id, status,
                 area, zone, pl, ql, ip, iq, yp,
                 yq, owner, scale, intrpt=None, version=32):
        self.i = int(i)  # bus number
        self.id = id
        self.status = status
        self.area = area
        self.zone = zone
        self.pl = pl  # Active power comp of const MVA load;in MW
        self.ql = ql  # Reactive power comp of const MVA load; Mvar.
        self.ip = ip  # Active power comp of const curr load; MW @ 1/unit voltage
        self.iq = iq  # reactive power of const. curr load; Mvar @ 1/unit voltage
        self.yp = yp  # Active power comp of const. admittance load;MW @ 1/unit voltage
        self.yq = yq  # Reactive power component of constant admittance load; Mvar @ 1/unit voltage
        self.owner = owner
        self.scale = scale

    def integrate(self):
        new_load = Loads(self.i, self.pl, self.ql, self.ip, self.iq,
                         self.yp, self.yq, self.area, self.status)
        return (new_load)


class Fixed_shunt_data:

    def __init__(self, i, id, status, gl, bl):
        self.i = int(i)
        self.id = id
        self.status = status
        self.gl = gl  # Active component of shunt admittance to ground (MW @ 1/unit voltage)
        self.bl = bl  # Reactive component of shunt admittance to ground(Mvar @ 1/unit voltage)

    def integrate(self):
        new_shunt = Shunts(self.i, self.gl, self.bl, 1, 0, 0, 0, 0, 0, 0, 0)
        return new_shunt


class Switched_shunt_data:

    def __init__(self, i, modsw, adjm, stat, vswhi, vswlo,
                 swrem, rmpct, rmidnt, binit, n1=0,
                 n2=0, n3=0, n4=0, n5=0, n6=0, n7=0,
                 n8=0, b1=0.0, b2=0.0, b3=0.0,
                 b4=0.0, b5=0.0, b6=0.0, b7=0.0,
                 b8=0.0):
        self.i = int(i)
        self.modsw = modsw
        self.adjm = adjm
        self.stat = stat
        self.vswhi = vswhi
        self.vswlo = vswlo
        self.swrem = swrem
        self.rmpct = rmpct
        self.rmidnt = rmidnt
        self.binit = binit

        # each switched shunt can have 0-9 steps (ni) and has
        # the corresponding number of increments (bi)
        self.n1, self.n2 = n1, n2
        self.n3, self.n4, self.n5 = n3, n4, n5
        self.n6, self.n7 = n6, n7
        self.n8 = n8

        self.b1, self.b2 = b1, b2
        self.b3, self.b4, self.b5 = b3, b4, b5
        self.b6, self.b7 = b6, b7
        self.b8 = b8

    def integrate(self):
        G_MW = 0
        B_MVAR = self.binit
        Nstep = [self.n1, self.n2, self.n3, self.n4, self.n5,
                 self.n6, self.n7, self.n8]
        Bstep = [self.b1, self.b2, self.b3, self.b4, self.b5, self.b6,
                 self.b7, self.b8]
        npBstep = np.asarray(Bstep)
        npNstep = np.asarray(Nstep)
        pos_Bstep = np.where(npBstep >= 0)
        neg_Bstep = np.where(npBstep <= 0)

        bmax = sum(np.multiply(npBstep[pos_Bstep], npNstep[pos_Bstep]))
        bmin = sum(np.multiply(npBstep[neg_Bstep], npNstep[neg_Bstep]))

        new_shunt = Shunts(self.i, G_MW, B_MVAR, 3, self.vswhi,
                           self.vswlo, bmax, bmin, self.binit, self.swrem,
                           Nstep, Bstep)

        return new_shunt


class Generator_data:

    def __init__(self, i, id, pg, qg, qt,
                 qb, vs, ireg, mbase, zr, zx, rt, xt,
                 gtap, stat, rmpct, pt, pb, wmod,
                 wpf, o1=0, o2=0, o3=0, o4=0, f1=1.0,
                 f2=1.0, f3=1.0, f4=1.0):
        self.i = int(i)  # bus number
        self.id = id
        self.pg = pg  # Gen active power output (MW)
        self.qg = qg  # Gen reactive power output (Mvar)
        self.qt = qt  # Max generator reactive power output (Mvar)
        self.qb = qb  # min gen reactive power output (Mvar)
        self.vs = vs  # Regulated voltage setpoint (pu)
        self.ireg = ireg  # bus num of remote bus which is to be reg
        self.mbase = mbase  # Total MVA base of the units represented by this machine(MVA)
        self.zr, self.zx = zr, zx  # Complex machine impedance, ZSORCE
        self.rt, self.xt = rt, xt  # Step-up transformer impedance, XTRAN(pu)
        self.gtap = gtap  # Step-up transformer off-nominal turns ratio (pu)
        self.stat = stat
        self.rmpct = rmpct
        self.pt = pt  # max gen active power output (MW)
        self.pb = pb  # min gen active power output

        # each generator can have 1-4 owners (oi)
        # and the corresponding num of fraction of total ownership (fi)
        self.o1 = o1
        self.o2 = o2
        self.o3 = o3
        self.o4 = o4
        self.f1 = f1
        self.f2 = f2
        self.f3 = f3
        self.f4 = f4
        self.wmod = wmod  # Wind machine control mode
        self.wpf = wpf  # Power factor

        # Wind machine with Q limits determined from P and WPF
        if (self.wmod == 2):
            qlim = math.sqrt(math.pow(pg / wpf, 2) - math.pow(pg, 2))
            self.qT = qlim
            self.qB = -qlim

        # Fixed reactive power setting determined from P and WPF
        elif (self.wmod == 3):
            qg = math.sqrt(math.pow(pg / wpf, 2) - math.pow(pg, 2))
            if (self.wpf > 0):
                self.qt = np.sign(self.pg) * qg
                self.qb = np.sign(self.pg) * qg
            elif (self.wpf <= 0):
                self.qt = -np.sign(self.pg) * qg
                self.qb = -np.sign(self.pg) * qg

        # Set q within qt and qb
        if (abs(self.qt - self.qb) < 1e-6):
            self.qg = self.qt

    def integrate(self, isGenerator=True):
        if isGenerator:
            self.rmpct = self.rmpct
            new_obj = Generators(self.i, self.pg, self.vs, self.qt, self.qb,
                                 self.pt, self.pb, self.qg, self.ireg, self.rmpct, GenType.Generation)

        else:
            area = -1
            status = 1
            new_obj = Loads(self.i, -self.pg, -self.qg, 0.0, 0.0, 0.0, 0.0, area, status)

        return new_obj

    def __repr__(self):
        return str(self.i)


class Slack_generator_data:

    def __init__(self, i, id, pg, qg, qt,
                 qb, vs, ireg, mbase, zr, zx, rt, xt,
                 gtap, stat, rmpct, pt, pb, wmod,
                 wpf, ang, o1, o2=0, o3=0, o4=0, f1=1.0, f2=1.0, f3=1.0, f4=1.0):
        self.i = int(i)  # bus number
        self.id = id
        self.pg = pg  # Gen active power output (MW)
        self.qg = qg  # Gen reactive power output (Mvar)
        self.qt = qt  # Max generator reactive power output (Mvar)
        self.qb = qb  # min gen reactive power output (Mvar)
        self.vs = vs  # Regulated voltage setpoint (pu)
        self.ireg = ireg  # bus num of remote bus which is to be reg
        self.mbase = mbase  # Total MVA base of the units represented by this machine(MVA)
        self.zr, self.zx = zr, zx  # Complex machine impedance, ZSORCE
        self.rt, self.xt = rt, xt  # Step-up transformer impedance, XTRAN(pu)
        self.gtap = gtap  # Step-up transformer off-nominal turns ratio (pu)
        self.stat = stat
        self.rmpct = rmpct
        self.pt = pt  # max gen active power output (MW)
        self.pb = pb  # min gen active power output
        self.ang = ang

        # each generator can have 1-4 owners (oi)
        # and the corresponding num of fraction of total ownership (fi)
        self.o1 = o1
        self.o2 = o2
        self.o3 = o3
        self.o4 = o4
        self.f1 = f1
        self.f2 = f2
        self.f3 = f3
        self.f4 = f4
        self.wmod = wmod  # Wind machine control mode
        self.wpf = wpf  # Power factor

    def integrate(self):
        new_slack = Slack(self.i, self.vs, self.ang, self.pg, self.qg)
        return (new_slack)

    def __repr__(self):
        return str(self.i)


# Non-Transformer Branch Data
class Branch_data:

    def __init__(self, i, j, ckt, r, x, b, rateA, rateB,
                 rateC, gi, bi, gj, bj, st, met, len,
                 o1, o2=0, o3=0, o4=0, f1=1.0, f2=1.0,
                 f3=1.0, f4=1.0):
        self.i = int(i)
        self.j = int(j)
        self.ckt = ckt
        self.r = r
        self.x = x
        self.b = b
        self.rateA = rateA
        self.rateB = rateB
        self.rateC = rateC
        self.gi, self.bi = gi, bi
        self.gj, self.bj = gj, bj
        self.st = st
        self.met = met
        self.len = len

        # each branch can have 1-4 owners (oi)
        # and the corresponding num of fraction of total ownership (fi)
        self.o1 = o1
        self.o2 = o2
        self.o3 = o3
        self.o4 = o4
        self.f1 = f1
        self.f2 = f2
        self.f3 = f3
        self.f4 = f4

    def integrate(self):
        new_branch = Branches(self.i, self.j, self.r, self.x, self.b, self.st,
                              self.rateA, self.rateB, self.rateC)
        shunt_i = None
        shunt_j = None
        if self.gi != 0 or self.bi != 0:
            shunt_i = Shunts(self.i, self.gi * global_vars.MVAbase, self.bi * global_vars.MVAbase, 1, 0, 0, 0, 0, 0, 0,
                             0)
        if self.gj != 0 or self.bj != 0:
            shunt_j = Shunts(self.j, self.gj * global_vars.MVAbase, self.bj * global_vars.MVAbase, 1, 0, 0, 0, 0, 0, 0,
                             0)

        return new_branch, shunt_i, shunt_j


class Xfrmr_ic_data:

    def __init__(self, i, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11,
                 f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11):
        self.i = i

        self.t1, self.t2, self.t3 = t1, t2, t3
        self.t4, self.t5, self.t6 = t4, t5, t6
        self.t7, self.t8, self.t9 = t7, t8, t9
        self.t10, self.t11 = t10, t11

        self.f1, self.f2, self.f3 = f1, f2, f3
        self.f4, self.f5, self.f6 = f4, f5, f6
        self.f7, self.f8, self.f9 = f7, f8, f9
        self.f10, self.f11 = f10, f11


# two winding transformers
class Two_xfmr_data:
    def __init__(self, i, j, k, ckt, cw, cz, cm, mag1, mag2, nmetr, name, stat,
                 o1, o2, o3, o4, f1, f2, f3, f4, r1_2, x1_2, sbase1_2,
                 windv1, nomv1, ang1, rata1, ratb1, ratc1, cod1, cont1, rma1, rmi1, vma1,
                 vmi1, ntp1, tab1, cr1, cx1, windv2, nomv2, vecgrp=None, cnxa1=None):
        self.i = int(i)
        self.j = int(j)
        self.k = int(k)
        self.ckt = ckt
        self.cw = cw
        self.cz = cz
        self.cm = cm
        self.mag1 = mag1
        self.mag2 = mag2
        self.nmetr = nmetr
        self.name = name
        self.stat = stat
        self.o1, self.o2, self.o3, self.o4 = o1, o2, o3, o4
        self.f1, self.f2, self.f3, self.f4 = f1, f2, f3, f4
        self.r1_2 = r1_2
        self.x1_2 = x1_2
        self.sbase1_2 = sbase1_2
        self.windv1 = windv1
        self.nomv1 = nomv1
        self.ang1 = ang1
        self.rata1, self.ratb1, self.ratc1 = rata1, ratb1, ratc1
        self.cod1 = cod1
        self.cont1 = cont1
        self.rma1 = rma1
        self.rmi1 = rmi1
        self.vma1 = vma1
        self.vmi1 = vmi1
        self.ntp1 = ntp1
        self.tab1 = tab1
        self.cri1 = cr1
        self.cx1 = cx1
        self.cr1 = cr1
        self.windv2 = windv2
        self.nomv2 = nomv2
        if vecgrp != None:
            self.vecgrp = vecgrp
            self.cnxa1 = cnxa1


def integrate_2xfmrs(xfmr_data, sbase, busData):
    # send in system sbase
    new_2xfmr = TwoWindingXfmrs(xfmr_data, sbase, busData)
    return (new_2xfmr.createXfmrObject())


# three winding transformers
class Three_xfmr_data:
    def __init__(self, i, j, k, ckt, cw, cz, cm, mag1, mag2, nmetr, name, stat, o1, o2, o3, o4, f1, f2, f3, f4,
                 r1_2, x1_2, sbase1_2, r2_3, x2_3, sbase2_3, r3_1, x3_1, sbase3_1, vmstar, anstar,
                 windv1, nomv1, ang1, rata1, ratb1, ratc1, cod1, cont1, rma1, rmi1, vma1, vmi1, ntp1, tab1, cr1, cx1,
                 windv2, nomv2, ang2, rata2, ratb2, ratc2, cod2, cont2, rma2, rmi2, vma2, vmi2, ntp2, tab2, cr2, cx2,
                 windv3, nomv3, ang3, rata3, ratb3, ratc3, cod3, cont3, rma3, rmi3, vma3, vmi3, ntp3, tab3, cr3, cx3,
                 vecgrp=None, cnxa1=None, cnxa2=None, cnxa3=None):
        self.i = int(i)
        self.j = int(j)
        self.k = int(k)
        self.ckt = ckt
        self.cw = cw
        self.cz = cz
        self.cm = cm
        self.mag1 = mag1
        self.mag2 = mag2
        self.nmetr = nmetr
        self.name = name
        self.stat = stat
        self.o1, self.o2, self.o3, self.o4 = o1, o2, o3, o4
        self.f1, self.f2, self.f3, self.f4 = f1, f2, f3, f4
        self.r1_2 = r1_2
        self.x1_2 = x1_2
        self.sbase1_2 = sbase1_2
        self.r2_3 = r2_3
        self.x2_3 = x2_3
        self.sbase2_3 = sbase2_3
        self.r3_1 = r3_1
        self.x3_1 = x3_1
        self.sbase3_1 = sbase3_1
        self.vmstar = vmstar
        self.anstar = anstar

        self.windv1 = windv1
        self.nomv1 = nomv1
        self.ang1 = ang1
        self.rata1, self.ratb1, self.ratc1 = rata1, ratb1, ratc1
        self.cod1 = cod1
        self.cont1 = cont1
        self.rma1 = rma1
        self.rmi1 = rmi1
        self.vma1 = vma1
        self.vmi1 = vmi1
        self.ntp1 = ntp1
        self.tab1 = tab1
        self.cr1 = cr1
        self.cx1 = cx1

        self.windv2 = windv2
        self.nomv2 = nomv2
        self.ang2 = ang2
        self.rata2, self.ratb2, self.ratc2 = rata2, ratb2, ratc2
        self.cod2 = cod2
        self.cont2 = cont2
        self.rma2 = rma2
        self.rmi2 = rmi2
        self.vma2 = vma2
        self.vmi2 = vmi2
        self.ntp2 = ntp2
        self.tab2 = tab2
        self.cr2 = cr2
        self.cx2 = cx2

        self.windv3 = windv3
        self.nomv3 = nomv3
        self.ang3 = ang3
        self.rata3, self.ratb3, self.ratc3 = rata3, ratb3, ratc3
        self.cod3 = cod3
        self.cont3 = cont3
        self.rma3 = rma3
        self.rmi3 = rmi3
        self.vma3 = vma3
        self.vmi3 = vmi3
        self.ntp3 = ntp3
        self.tab3 = tab3
        self.cr3 = cr3
        self.cx3 = cx3

        self.vecgrp = vecgrp
        self.cnxa1 = cnxa1
        self.cnxa2 = cnxa2
        self.cnxa3 = cnxa3


def integrate_3xfmrs(xfmr_data, sbase, busData, starNode):
    # send in system sbase
    new_3xfmr = ThreeWindingXfmrs(xfmr_data, sbase, -1, busData)
    return (new_3xfmr.createXfmrObject())
