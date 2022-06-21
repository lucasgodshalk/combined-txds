from __future__ import division
from itertools import count
import numpy as np
from sympy import symbols
from sympy import cos
from sympy import sin
from logic.lagrangehandler import LagrangeHandler
from logic.lagrangestamper import LagrangeStamper
from logic.matrixbuilder import MatrixBuilder
from models.positiveseq.shared import TX_LARGE_G, TX_LARGE_B
from models.positiveseq.buses import _all_bus_key
import math
from models.positiveseq.shared import build_line_stamper, stamp_line

constants = tr, ang, tx_factor = symbols('tr ang tx_factor')
primals = [Vr_from, Vi_from, Ir_prim, Ii_prim, Vr_sec, Vi_sec] = symbols('V_r V_i I_pri\,r I_pri\,i V_sec\,r V_sec\,i')
duals = [Lr_from, Li_from, Lir_prim, Lii_prim, Lvr_sec, Lvi_sec] = symbols('lambda_r lambda_i lambda_pri\,Ir lambda_pri\,Ii lambda_sec\,Vr lambda_sec\,Vi')

scaled_tr = tr + (1 - tr) * tx_factor 
scaled_angle = ang - ang * tx_factor

scaled_trcos = scaled_tr * cos(scaled_angle)
scaled_trsin = scaled_tr * sin(scaled_angle)

eqns = [
    Ir_prim,
    Ii_prim,
    Vr_from - scaled_trcos * Vr_sec + scaled_trsin * Vi_sec,
    Vi_from - scaled_trcos * Vi_sec - scaled_trsin * Vr_sec,
    -scaled_trcos * Ir_prim - scaled_trsin * Ii_prim,
    -scaled_trcos * Ii_prim + scaled_trsin * Ir_prim
]

lagrange = np.dot(duals, eqns)

xfrmr_lh = LagrangeHandler(lagrange, constants, primals, duals)

class Transformers:
    _ids = count(0)

    def __init__(self,
                 from_bus,
                 to_bus,
                 r,
                 x,
                 status,
                 tr,
                 ang,
                 Gsh_raw,
                 Bsh_raw,
                 rating):
        """Initialize a transformer instance

        Args:
            from_bus (int): the primary or sending end bus of the transformer.
            to_bus (int): the secondary or receiving end bus of the transformer
            r (float): the line resitance of the transformer in
            x (float): the line reactance of the transformer
            status (int): indicates if the transformer is active or not
            tr (float): transformer turns ratio
            ang (float): the phase shift angle of the transformer
            Gsh_raw (float): the shunt conductance of the transformer
            Bsh_raw (float): the shunt admittance of the transformer
            rating (float): the rating in MVA of the transformer
        """
        self.id = self._ids.__next__()

        self.from_bus = _all_bus_key[from_bus]
        self.to_bus = _all_bus_key[to_bus]

        self.r = r
        self.x = x

        self.tr = tr
        self.ang_rad = ang * math.pi / 180.

        self.G_loss = r / (r ** 2 + x ** 2)
        self.B_loss = x / (r ** 2 + x ** 2) #source of error

        self.status = status

        self.xfrmr_stamper = None
        self.losses_stamper = None

    def try_build_stamper(self):
        if self.xfrmr_stamper != None:
            return
        
        index_map = {}
        index_map[Vr_from] = self.from_bus.node_Vr
        index_map[Vi_from] = self.from_bus.node_Vi
        index_map[Ir_prim] = self.node_primary_Ir
        index_map[Ii_prim] = self.node_primary_Ii
        index_map[Vr_sec] = self.node_secondary_Vr
        index_map[Vi_sec] = self.node_secondary_Vi

        index_map[Lr_from] = self.from_bus.node_lambda_Vr
        index_map[Li_from] = self.from_bus.node_lambda_Vi
        index_map[Lir_prim] = self.node_primary_Lambda_Ir
        index_map[Lii_prim] = self.node_primary_Lambda_Ii
        index_map[Lvr_sec] = self.node_secondary_Lambda_Vr
        index_map[Lvi_sec] = self.node_secondary_Lambda_Vi

        self.xfrmr_stamper = LagrangeStamper(xfrmr_lh, index_map)

        self.losses_stamper = build_line_stamper(
            self.node_secondary_Vr, 
            self.node_secondary_Vi, 
            self.to_bus.node_Vr, 
            self.to_bus.node_Vi,
            self.node_secondary_Lambda_Vr, 
            self.node_secondary_Lambda_Vi, 
            self.to_bus.node_lambda_Vr, 
            self.to_bus.node_lambda_Vi
            )

    def assign_nodes(self, node_index, optimization_enabled):
        self.node_primary_Ir = next(node_index)
        self.node_primary_Ii = next(node_index)
        self.node_secondary_Vr = next(node_index)
        self.node_secondary_Vi = next(node_index)

        if not optimization_enabled:
            return
        
        self.node_primary_Lambda_Ir = next(node_index)
        self.node_primary_Lambda_Ii = next(node_index)
        self.node_secondary_Lambda_Vr = next(node_index)
        self.node_secondary_Lambda_Vi = next(node_index)

    def stamp_primal(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.status:
            return

        self.try_build_stamper()
        self.xfrmr_stamper.stamp_primal(Y, J, [self.tr, self.ang_rad, tx_factor], v_previous)
        self.losses_stamper.stamp_primal(Y, J, [self.G_loss, self.B_loss, tx_factor], v_previous)

    def stamp_dual(self, Y: MatrixBuilder, J, v_previous, tx_factor, network_model):
        if not self.status:
            return

        self.try_build_stamper()
        self.xfrmr_stamper.stamp_dual(Y, J, [self.tr, self.ang_rad, tx_factor], v_previous)
        self.losses_stamper.stamp_dual(Y, J, [self.G_loss, self.B_loss, tx_factor], v_previous)

    def calculate_residuals(self, network_model, v):
        return {}
