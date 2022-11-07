from __future__ import division
from itertools import count
import numpy as np
from sympy import symbols
from sympy import cos
from sympy import sin
from logic.stamping.lagrangesegment import LagrangeSegment
from logic.stamping.lagrangestampdetails import SKIP, LagrangeStampDetails
import math
from models.singlephase.line import build_line_stamper
from models.singlephase.bus import GROUND, Bus
from models.wellknownvariables import tx_factor
from logic.stamping.matrixstamper import build_stamps_from_stampers

tr, ang = symbols('tr ang')
constants = tr, ang, tx_factor
primals = Vr_pri_pos, Vi_pri_pos, Vr_pri_neg, Vi_pri_neg, Ir_prim, Ii_prim, Vr_sec_pos, Vi_sec_pos, Vr_sec_neg, Vi_sec_neg = symbols('Vr_pri_pos Vi_pri_pos Vr_pri_neg Vi_pri_neg Ir_prim Ii_prim Vr_sec_pos Vi_sec_pos Vr_sec_neg Vi_sec_neg')
duals = Lr_pri_pos, Li_pri_pos, Lr_pri_neg, Li_pri_neg, Lir_prim, Lii_prim, Lr_sec_pos, Li_sec_pos, Lr_sec_neg, Li_sec_neg = symbols('Lr_pri_pos Li_pri_pos Lr_pri_neg Li_pri_neg Lir_prim Lii_prim Lr_sec_pos Li_sec_pos Lr_sec_neg Li_sec_neg')

scaled_tr = tr + (1 - tr) * tx_factor 
scaled_angle = ang - ang * tx_factor

scaled_trcos = scaled_tr * cos(scaled_angle)
scaled_trsin = scaled_tr * sin(scaled_angle)

secondary_current_r = -scaled_trcos * Ir_prim - scaled_trsin * Ii_prim
secondary_current_i = -scaled_trcos * Ii_prim + scaled_trsin * Ir_prim

Vr_pri = Vr_pri_pos - Vr_pri_neg
Vi_pri = Vi_pri_pos - Vi_pri_neg

Vr_sec = Vr_sec_pos - Vr_sec_neg
Vi_sec = Vi_sec_pos - Vi_sec_neg

eqns = [
    Ir_prim,
    Ii_prim,
    -Ir_prim,
    -Ii_prim,
    Vr_pri - scaled_trcos * Vr_sec + scaled_trsin * Vi_sec,
    Vi_pri - scaled_trcos * Vi_sec - scaled_trsin * Vr_sec,
    secondary_current_r,
    secondary_current_i,
    -secondary_current_r,
    -secondary_current_i
]

lagrange = np.dot(duals, eqns)

xfrmr_lh = LagrangeSegment(lagrange, constants, primals, duals)

class Transformer:
    _ids = count(0)

    def __init__(self,
                 from_bus_pos: Bus,
                 from_bus_neg: Bus,
                 to_bus_pos: Bus,
                 to_bus_neg: Bus,
                 r,
                 x,
                 status,
                 tr,
                 ang,
                 G_shunt,
                 B_shunt,
                 rating):

        self.id = self._ids.__next__()

        self.from_bus_pos = from_bus_pos
        self.from_bus_neg = from_bus_neg
        self.to_bus_pos = to_bus_pos
        self.to_bus_neg = to_bus_neg
        self.r = r
        self.x = x

        self.tr = tr
        self.ang_rad = ang * math.pi / 180.

        self.G_loss = r / (r ** 2 + x ** 2)
        self.B_loss = -x / (r ** 2 + x ** 2)

        self.G_shunt = G_shunt
        self.B_shunt = B_shunt

        self.status = status

    def assign_nodes(self, node_index, optimization_enabled):
        self.node_primary_Ir = next(node_index)
        self.node_primary_Ii = next(node_index)
        self.node_secondary_Vr = next(node_index)
        self.node_secondary_Vi = next(node_index)

        if optimization_enabled:
            self.node_primary_Lambda_Ir = next(node_index)
            self.node_primary_Lambda_Ii = next(node_index)
            self.node_secondary_Lambda_Vr = next(node_index)
            self.node_secondary_Lambda_Vi = next(node_index)
        else:
            self.node_primary_Lambda_Ir = SKIP
            self.node_primary_Lambda_Ii = SKIP
            self.node_secondary_Lambda_Vr = SKIP
            self.node_secondary_Lambda_Vi = SKIP

        index_map = {}
        index_map[Vr_pri_pos] = self.from_bus_pos.node_Vr
        index_map[Vi_pri_pos] = self.from_bus_pos.node_Vi
        index_map[Vr_pri_neg] = self.from_bus_neg.node_Vr
        index_map[Vi_pri_neg] = self.from_bus_neg.node_Vi
        index_map[Ir_prim] = self.node_primary_Ir
        index_map[Ii_prim] = self.node_primary_Ii
        index_map[Vr_sec_pos] = self.node_secondary_Vr
        index_map[Vi_sec_pos] = self.node_secondary_Vi
        index_map[Vr_sec_neg] = self.to_bus_neg.node_Vr
        index_map[Vi_sec_neg] = self.to_bus_neg.node_Vi

        index_map[Lr_pri_pos] = self.from_bus_pos.node_lambda_Vr
        index_map[Li_pri_pos] = self.from_bus_pos.node_lambda_Vi
        index_map[Lr_pri_neg] = self.from_bus_neg.node_lambda_Vr
        index_map[Li_pri_neg] = self.from_bus_neg.node_lambda_Vi
        index_map[Lir_prim] = self.node_primary_Lambda_Ir
        index_map[Lii_prim] = self.node_primary_Lambda_Ii
        index_map[Lr_sec_pos] = self.node_secondary_Lambda_Vr
        index_map[Li_sec_pos] = self.node_secondary_Lambda_Vi
        index_map[Lr_sec_neg] = self.to_bus_neg.node_lambda_Vr
        index_map[Li_sec_neg] = self.to_bus_neg.node_lambda_Vi

        self.xfrmr_stamper = LagrangeStampDetails(xfrmr_lh, index_map, optimization_enabled)

        self.losses_stamper = build_line_stamper(
            self.node_secondary_Vr, 
            self.node_secondary_Vi, 
            self.to_bus_pos.node_Vr, 
            self.to_bus_pos.node_Vi,
            self.node_secondary_Lambda_Vr, 
            self.node_secondary_Lambda_Vi, 
            self.to_bus_pos.node_lambda_Vr, 
            self.to_bus_pos.node_lambda_Vi,
            optimization_enabled
            )
        
        self.shunt_stamper = build_line_stamper(
            self.to_bus_pos.node_Vr, 
            self.to_bus_pos.node_Vi,
            GROUND, 
            GROUND,
            self.to_bus_pos.node_lambda_Vr, 
            self.to_bus_pos.node_lambda_Vi,
            GROUND, 
            GROUND,
            optimization_enabled,
            no_tx_factor=True
            )

    def get_stamps(self):
        return build_stamps_from_stampers(self, 
            (self.xfrmr_stamper, [self.tr, self.ang_rad, 0]), 
            (self.losses_stamper, [self.G_loss, self.B_loss, 0])
            )

    def get_connections(self):
        return [(self.from_bus_pos, self.to_bus_pos), (self.from_bus_pos, self.from_bus_neg), (self.to_bus_pos, self.to_bus_neg)]
