"""Creates instances of two or three-winding transformers for use in the solver.

    Author(s): Victoria Ciplickas

    Date Created: 2019-06
    Date Modified: 2019-03-09

"""

import math
import copy

from models.Transformers import Transformers


class TwoWindingXfmrs:

    def __init__(self, xfmr_data, sbase, BusesData):
        self.mPrimaryBus = int(xfmr_data.i)
        self.mSecondaryBus = int(xfmr_data.j)
        self.mCkt = xfmr_data.ckt
        self.mCW = xfmr_data.cw
        self.mCZ = xfmr_data.cz
        self.mCM = xfmr_data.cm
        self.mMAG1 = xfmr_data.mag1
        self.mMAG2 = xfmr_data.mag2
        self.mR12 = xfmr_data.r1_2
        self.mX12 = xfmr_data.x1_2
        self.mSBASE12 = xfmr_data.sbase1_2
        self.mWINDV1 = xfmr_data.windv1
        self.mWINDV2 = xfmr_data.windv2
        self.mRatingA = xfmr_data.rata1 / sbase
        self.mRatingB = xfmr_data.ratb1 / sbase
        self.mRatingC = xfmr_data.ratc1 / sbase
        self.mMaxRating = max(self.mRatingA, self.mRatingB)
        self.mMaxRating = max(self.mMaxRating, self.mRatingC)
        self.mAng = xfmr_data.ang1
        self.mStatus = xfmr_data.stat

        # Calculations for transformer tap ratio
        mBasePrimary = BusesData[int(self.mPrimaryBus)].baskv
        mBaseSecondary = BusesData[int(self.mSecondaryBus)].baskv
        mWBasePrimary = xfmr_data.nomv1 if xfmr_data.nomv1 > 0 else mBasePrimary
        mWBaseSecondary = xfmr_data.nomv2 if xfmr_data.nomv2 > 0 else mBaseSecondary

        # This is the off-nominal turns ratio for primary and secondary winding in pu of the base
        # bus voltage
        # Set initial turns ratio based on units given in .raw file
        # Winding turns ratio into the solver should in per-unit per bus base voltage
        # for CW=1, off-nominal turns ratio in pu of winding bus base voltage
        if (self.mCW == 1):
            ti = self.mWINDV1
            tj = self.mWINDV2
        # for CW=2, for winding voltage in kV -> divide by bus base voltage to get pu
        elif (self.mCW == 2):
            ti = self.mWINDV1 / mBasePrimary
            tj = self.mWINDV2 / mBaseSecondary
        # for CW=3, for off-nominal turns ratio in pu of nominal winding voltage
        # To get to pu in bus base voltage -> multiply by nominal winding voltage,
        # divide by bus base voltage
        elif (self.mCW == 3):
            ti = (self.mWINDV1 * mWBasePrimary / mBasePrimary)
            tj = (self.mWINDV2 * mWBaseSecondary / mBaseSecondary)
        else:
            print("Invalid CW option for the transformer. Setting option CW to 1")
            ti = self.mWINDV1
            tj = self.mWINDV2
        # Calculate the turns ratio in pu of bus base voltage to be used in the solver
        self.mTR = ti / tj

        # This starts the control calculation of the transformer
        self.mControlCode = xfmr_data.cod1

        # Tap changing transformer - set min and max vals for tap
        if (self.mControlCode == 1 or self.mControlCode == 2):
            # Tap limits depend on units from .raw file (determined by CW param)
            # Follows the same calculation as that of TR
            if (self.mCW == 1):
                self.mTRUpper = xfmr_data.rma1 / self.mWINDV1
                self.mTRLower = xfmr_data.rmi1 / self.mWINDV1
            # for CW=2, for winding voltage in kV -> divide by bus base voltage to get pu
            elif (self.mCW == 2):
                self.mTRUpper = xfmr_data.rma1 / self.mWINDV1 / (self.mWINDV2 / mBaseSecondary)
                self.mTRLower = xfmr_data.rmi1 / self.mWINDV1 / (self.mWINDV2 / mBaseSecondary)
            # for CW=3, for off-nominal turns ratio in pu of nominal winding voltage
            # To get to pu in bus base voltage -> multiply by nominal winding voltage,
            # divide by bus base voltage
            elif (self.mCW == 3):
                self.mTRUpper = (xfmr_data.rma1 * mWBasePrimary / mBasePrimary) / (
                        self.mWINDV2 * mWBaseSecondary / mBaseSecondary)
                self.mTRLower = (xfmr_data.rmi1 * mWBasePrimary / mBasePrimary) / (
                        self.mWINDV2 * mWBaseSecondary / mBaseSecondary)
            else:
                print("Invalid CW option for the transformer. Setting option CW to 1")
                self.mTRUpper = xfmr_data.rma1 / self.mWINDV1
                self.mTRLower = xfmr_data.rmi1 / self.mWINDV1
            # Make sure initial value of turns ratio is within the bounds.
            # self.mTR = min(self.mTRUpper, self.mTR)
            # self.mTR = max(self.mTRLower, self.mTR)

            # Discrete tap step
            self.mTRStep = (self.mTRUpper - self.mTRLower) / (xfmr_data.ntp1 - 1)

            # Voltage control using transformer taps
            if (self.mControlCode == 1):
                self.mVoltUpper = xfmr_data.vma1
                self.mVoltLower = xfmr_data.vmi1
                self.mControlVolt = (self.mVoltUpper + self.mVoltLower) * 0.5
                # Controlled bus value and the direction of the control bus
                self.mControlledBus = abs(xfmr_data.cont1)
                # According to raw documentation if controlling bus number is 0,
                # # control is turned off
                if (self.mControlledBus == 0):
                    self.mControlCode = 0
                if (self.mControlledBus == self.mPrimaryBus):
                    self.mControlDirection = 1.0
                elif (self.mControlledBus == self.mSecondaryBus):
                    self.mControlDirection = -1.0
                else:
                    self.mControlDirection = 1.0 if xfmr_data.cont1 >= 0 else -1.0
            # Reactive Power Control - set min and max limits for Q
            elif (self.mControlCode == 2):
                self.mQFlowUpper = xfmr_data.vma1 / sbase
                self.mQFlowLower = xfmr_data.vmi1 / sbase
                self.mQFlowDesired = (self.mQFlowUpper + self.mQFlowLower) * 0.5
        # Phase shifting transformer - set min and max limits for phi
        if (self.mControlCode == 3):
            # Only one choice of units (degrees)
            self.mPhiUpper = xfmr_data.rma1
            self.mPhiLower = xfmr_data.rmi1
            self.mPowFlowUpper = xfmr_data.vma1 / sbase
            self.mPowFlowLower = xfmr_data.vmi1 / sbase
            self.mPowFlowDesired = (self.mPowFlowUpper + self.mPowFlowLower) * 0.5

        # Calculation of line loss parameters
        tj2 = tj * tj
        self.mImpedanceCode = xfmr_data.cz

        if (self.mImpedanceCode == 1):
            self.mRLossInit = self.mR12 * tj2
            self.mXLossInit = self.mX12 * tj2
        elif (self.mImpedanceCode == 2):
            self.mRLossInit = self.mR12 * tj2 * sbase / self.mSBASE12
            self.mXLossInit = self.mX12 * tj2 * sbase / self.mSBASE12
        elif (self.mImpedanceCode == 3):
            # R loss in watts
            # X in pu mva base and winding voltage base
            Rpu = self.mR12 / (1e6 * self.mSBASE12)
            Zpu = self.mX12
            baseImpedance = sbase / self.mSBASE12 * tj2
            self.mXLossInit = math.sqrt(Zpu * Zpu - Rpu * Rpu) * baseImpedance
            self.mRLossInit = Rpu * baseImpedance
        self.mRLoss = self.mRLossInit
        self.mXLoss = self.mXLossInit

        # Magnitizing impedance calculation
        if (xfmr_data.cm == 1):
            self.mGmag = self.mMAG1
            self.mBmag = self.mMAG2
            if (self.mBmag) > 0:
                print("Positive magnetizing impedance")

        # CM == 2: no load loss in watts and exciting current in pu on winding 1->2
        # MVA base
        elif (xfmr_data.cm == 2):
            self.mGmag = self.mMAG1 / (1e6 * sbase)  # Convert to pu base
            Sloss = self.mMAG2 * self.mSBASE12 / sbase
            if ((self.mGmag - Sloss) < -1e-6):
                self.mBmag = -math.sqrt(Sloss * Sloss - self.mGmag * self.mGmag)
            else:
                self.mGmag = 0
                self.mBmag = 0
        else:
            self.mGmag = self.mMAG1
            self.mBmag = self.mMAG2

    def createXfmrObject(self):
        if self.mStatus:
            new_xfmr = Transformers(int(self.mPrimaryBus), int(self.mSecondaryBus), self.mRLoss,
                                    self.mXLoss, self.mStatus, self.mTR,
                                    self.mAng, self.mGmag, self.mBmag, self.mMaxRating)

            return new_xfmr


class ThreeWindingXfmrs(object):

    def __init__(self, xfmr3_data, sbase, starNode, BusesData):
        self.mBusI = xfmr3_data.i
        self.mBusJ = xfmr3_data.j
        self.mBusK = xfmr3_data.k
        self.mStarNode = starNode
        # Check for the number of two-winding transformers
        # Create 2-winding xfmrs
        '''busIStatus = BusesData.busNum2BusStatus[self.mBusI]
        busJStatus = BusesData.busNum2BusStatus[self.mBusJ]
        busKStatus = BusesData.busNum2BusStatus[self.mBusK]'''
        busIStatus = BusesData[int(self.mBusI)].ide
        busJStatus = BusesData[int(self.mBusJ)].ide
        busKStatus = BusesData[int(self.mBusK)].ide
        # IDE is from the bus_data class - its either 1, 2, 3, 4 ?

        self.mStatus = xfmr3_data.stat
        self.mWindingStatus = [0, 0, 0]
        # Three winding statuses
        # option 4 - bus I is off : I-J and I-K are off
        # option 2 - bus J is off : I-J and J-K are off
        # option 3 - bus K is off : J-K and I-K are off
        if (self.mStatus != 4 and busIStatus != 4 and (busJStatus != 4 or busKStatus != 4)):
            # 2-winding xfmr between _I and starBus is in service
            self.mWindingStatus[0] = 1
        # Create 2-winding transformer from three-winding transformer
        if (self.mStatus != 2 and busJStatus != 4 and (busIStatus != 4 or busKStatus != 4)):
            # 2-winding xfmr between _J and starBus is in service
            self.mWindingStatus[1] = 1
        # Call two winding constructor
        if (self.mStatus != 3 and busKStatus != 4 and (busIStatus != 4 or busJStatus != 4)):
            # 2-winding xfmr between _K and starBus is in service
            self.mWindingStatus[2] = 1

        self.mPrimaryBus = [self.mBusI, self.mBusJ, self.mBusK]
        self.mSecondaryBus = [self.mStarNode, self.mStarNode, self.mStarNode]
        self.mCkt = xfmr3_data.ckt
        self.mCW = xfmr3_data.cw
        self.mCZ = xfmr3_data.cz
        self.mCM = xfmr3_data.cm
        self.mMAG1 = xfmr3_data.mag1
        self.mMAG2 = xfmr3_data.mag2
        self.mR = [xfmr3_data.r1_2, xfmr3_data.r2_3, xfmr3_data.r3_1]
        self.mX = [xfmr3_data.x1_2, xfmr3_data.x2_3, xfmr3_data.x3_1]
        self.mSBASE = [xfmr3_data.sbase1_2, xfmr3_data.sbase2_3, xfmr3_data.sbase3_1]
        self.mWINDVPri = [xfmr3_data.windv1, xfmr3_data.windv2, xfmr3_data.windv3]
        self.mWINDVSec = [1., 1., 1.]
        self.mRatingA = [xfmr3_data.rata1 / sbase, xfmr3_data.rata2 / sbase, xfmr3_data.rata3 / sbase]
        self.mRatingB = [xfmr3_data.ratb1 / sbase, xfmr3_data.ratb2 / sbase, xfmr3_data.ratb3 / sbase]
        self.mRatingC = [xfmr3_data.ratc1 / sbase, xfmr3_data.ratc2 / sbase, xfmr3_data.ratc3 / sbase]
        self.mAng = [xfmr3_data.ang1, xfmr3_data.ang2, xfmr3_data.ang3]
        # This starts the control calculation of the transformer
        self.mControlCode = [xfmr3_data.cod1, xfmr3_data.cod2, xfmr3_data.cod3]
        self.mControlledBus = [xfmr3_data.cont1, xfmr3_data.cont2, xfmr3_data.cont3]
        self.mRMA = [xfmr3_data.rma1, xfmr3_data.rma2, xfmr3_data.rma3]
        self.mRMI = [xfmr3_data.rmi1, xfmr3_data.rmi2, xfmr3_data.rmi3]
        self.mNTP = [xfmr3_data.ntp1, xfmr3_data.ntp2, xfmr3_data.ntp3]
        self.mVoltUpper = [xfmr3_data.vma1, xfmr3_data.vma2, xfmr3_data.vma3]
        self.mVoltLower = [xfmr3_data.vmi1, xfmr3_data.vmi2, xfmr3_data.vmi3]
        # self.mImpedanceCode = [xfmr3_data.cz1, xfmr3_data.cz2, xfmr3_data.cz3]
        self.mImpedanceCode = [xfmr3_data.cz, xfmr3_data.cz, xfmr3_data.cz]
        # Calculations for transformer tap ratio
        mBasePrimary = [BusesData[int(self.mBusI)].baskv, BusesData[int(self.mBusJ)].baskv,
                        BusesData[int(self.mBusK)].baskv]
        mBaseSecondary = [1., 1., 1.]
        mWBasePrimary = [xfmr3_data.nomv1, xfmr3_data.nomv2, xfmr3_data.nomv3]
        for i in range(len(mWBasePrimary)):
            if mWBasePrimary[i] == 0.:
                mWBasePrimary[i] = mBasePrimary[i]
        # mWBasePrimary = [mBasePrimary[idx] for (idx, val) in enumerate(mWBasePrimary) if val == 0.]
        mWBaseSecondary = copy.deepcopy(mBaseSecondary)

        # Initialize the following lists
        self.mTR = [1, 1, 1]
        self.mAng = [xfmr3_data.ang1, xfmr3_data.ang2, xfmr3_data.ang3]
        self.mTRUpper = [1.1, 1.1, 1.1]
        self.mTRLower = [0.9, 0.9, 0.9]
        self.mTRStep = [0., 0., 0.]
        self.mControlVolt = [1., 1., 1.]
        self.mControlDirection = [0, 0, 0]
        self.mRLossDelta = [0., 0., 0.]
        self.mXLossDelta = [0., 0., 0.]
        self.mGmag = [0., 0., 0.]
        self.mBmag = [0., 0., 0.]

        for idx in range(3):
            # if (self.mWindingStatus[idx]):
            # This is the off-nominal turns ratio for primary and secondary winding in pu of the base
            # bus voltage
            # Set initial turns ratio based on units given in .raw file
            # Winding turns ratio into the solver should in per-unit per bus base voltage
            # for CW=1, off-nominal turns ratio in pu of winding bus base voltage
            if (self.mCW == 1):
                ti = self.mWINDVPri[idx]
                tj = self.mWINDVSec[idx]
            # for CW=2, for winding voltage in kV -> divide by bus base voltage to get pu
            elif (self.mCW == 2):
                ti = self.mWINDVPri[idx] / mBasePrimary[idx]
                tj = self.mWINDVSec[idx] / mBaseSecondary[idx]
            # for CW=3, for off-nominal turns ratio in pu of nominal winding voltage
            # To get to pu in bus base voltage -> multiply by nominal winding voltage,
            # divide by bus base voltage
            elif (self.mCW == 3):
                ti = (self.mWINDVPri[idx] * mWBasePrimary[idx] / mBasePrimary[idx])
                tj = (self.mWINDVSec[idx] * mWBaseSecondary[idx] / mBaseSecondary[idx])
            else:
                print("Invalid CW option for the transformer. Setting option CW to 1")
                ti = self.mWINDVPri[idx]
                tj = self.mWINDVSec[idx]
            # Calculate the turns ratio in pu of bus base voltage to be used in the solver
            self.mTR[idx] = ti / tj

            # Tap changing transformer - set min and max vals for tap
            if (self.mControlCode[idx] == 1 or self.mControlCode[idx] == 2):
                # Tap limits depend on units from .raw file (determined by CW param)
                # Follows the same calculation as that of TR
                self.mTRUpper[idx] = self.mRMA[idx] * ti / self.mWINDVPri[idx]
                self.mTRLower[idx] = self.mRMI[idx] * ti / self.mWINDVPri[idx]

                # Make sure initial value of turns ratio is within the bounds.
                self.mTR[idx] = min(self.mTRUpper[idx], self.mTR[idx])
                self.mTR[idx] = max(self.mTRLower[idx], self.mTR[idx])

                # Discrete tap step
                self.mTRStep[idx] = (self.mTRUpper[idx] - self.mTRLower[idx]) / (self.mNTP[idx] - 1)

                # Voltage control using transformer taps
                if (self.mControlCode[idx] == 1):
                    self.mControlVolt[idx] = (self.mVoltUpper[idx] + self.mVoltLower[idx]) * 0.5
                    # According to raw documentation if controlling bus number is 0,
                    # control is turned off
                    if (self.mControlledBus[idx] == 0):
                        self.mControlCode[idx] = 0
                    if (self.mControlledBus[idx] == self.mPrimaryBus[idx]):
                        self.mControlDirection[idx] = 1
                    else:
                        if (self.mControlledBus[idx] > 0):
                            self.mControlDirection[idx] = 1
                        else:
                            self.mControlDirection[idx] = -1

            # Calculation of line loss parameters
            tj2 = tj * tj

            if (self.mImpedanceCode[idx] == 1):
                self.mRLossInit = self.mR[idx] * tj2
                self.mXLossInit = self.mX[idx] * tj2
            elif (self.mImpedanceCode[idx] == 2):
                self.mRLossInit = self.mR[idx] * tj2 * sbase / self.mSBASE[idx]
                self.mXLossInit = self.mX[idx] * tj2 * sbase / self.mSBASE[idx]
            elif (self.mImpedanceCode[idx] == 3):
                # R loss in watts
                # X in pu mva base and winding voltage base
                Rpu = self.mR[idx] / (1e6 * self.mSBASE[idx])
                Zpu = self.mX[idx]
                baseImpedance = sbase / self.mSBASE[idx] * tj2
                self.mXLossInit = math.sqrt(Zpu * Zpu - Rpu * Rpu) * baseImpedance
                self.mRLossInit = Rpu * baseImpedance
            self.mRLossDelta[idx] = self.mRLossInit
            self.mXLossDelta[idx] = self.mXLossInit
        # Star formation impedance are calculated as follows:
        self.mR1 = 0.5 * (self.mRLossDelta[0] + self.mRLossDelta[2] - self.mRLossDelta[1])
        self.mX1 = 0.5 * (self.mXLossDelta[0] + self.mXLossDelta[2] - self.mXLossDelta[1])
        self.mR2 = 0.5 * (self.mRLossDelta[1] + self.mRLossDelta[0] - self.mRLossDelta[2])
        self.mX2 = 0.5 * (self.mXLossDelta[1] + self.mXLossDelta[0] - self.mXLossDelta[2])
        self.mR3 = 0.5 * (self.mRLossDelta[1] + self.mRLossDelta[2] - self.mRLossDelta[0])
        self.mX3 = 0.5 * (self.mXLossDelta[1] + self.mXLossDelta[2] - self.mXLossDelta[0])
        # Magnetizing impedance is only on the primary side of the transformer
        if self.mWindingStatus[0]:
            # Magnitizing impedance calculation
            if (xfmr3_data.cm == 1):
                self.mGmag[0] = self.mMAG1
                self.mBmag[0] = self.mMAG2
                if self.mBmag[0] > 0:
                    print("Positive transformer magnetizing susceptance")
            # CM == 2: no load loss in watts and exciting current in pu on winding 1->2
            # MVA base
            elif (xfmr3_data.cm == 2):
                self.mGmag[0] = self.mMAG1 / (1e6 * sbase)
                Sloss = self.mMAG2 * self.mSBASE[0] / sbase
                if ((self.mGmag[0] - Sloss) < -1e-6):
                    self.mBmag[0] = -math.sqrt(Sloss * Sloss - self.mGmag[0] * self.mGmag[0])
                else:
                    self.mGmag[0] = 0.
                    self.mBmag[0] = 0.
            else:
                self.mGmag[0] = self.mMAG1
                self.mBmag[0] = self.mMAG2

    def createXfmrObject(self):
        xfmrs = []
        if self.mWindingStatus[0]:
            self.mMaxRatingA = max(self.mRatingA[0], self.mRatingA[1], self.mRatingA[2])
            new_3xfmr1 = Transformers(int(self.mPrimaryBus[0]), int(self.mSecondaryBus[0]), self.mR1,
                                      self.mX1, self.mWindingStatus[0], self.mTR[0], self.mAng[0],
                                      self.mGmag[0], self.mBmag[0], self.mMaxRatingA)
            xfmrs.append(new_3xfmr1)
        # Here create transformer object
        # In the constructor you will have to pass
        # self.mPrimaryBus[0], self.mSecondaryBus[0], self.mR1, self.mX1,
        # b=0, self.mWindingStatus[0], self.mTR[0], self.mAng[0], self.mGmag, self.mBmag,
        # self.mRating[0]
        if self.mWindingStatus[1]:
            self.mMaxRatingB = max(self.mRatingB[0], self.mRatingB[1], self.mRatingB[2])
            new_3xfmr2 = Transformers(int(self.mPrimaryBus[1]), int(self.mSecondaryBus[1]), self.mR2,
                                      self.mX2, self.mWindingStatus[1], self.mTR[1], self.mAng[1],
                                      0, 0, self.mMaxRatingB)
            xfmrs.append(new_3xfmr2)
        # Here create transformer object
        # In the constructor you will have to pass
        # self.mPrimaryBus[1], self.mSecondaryBus[1], self.mR2, self.mX2,
        # b=0, self.mWindingStatus[1], self.mTR[1], self.mAng[1], self.mGmag=0, self.mBmag=0,
        # self.mRating[1]
        if self.mWindingStatus[2]:
            self.mMaxRatingC = max(self.mRatingC[0], self.mRatingC[1], self.mRatingC[2])
            new_3xfmr3 = Transformers(int(self.mPrimaryBus[2]), int(self.mSecondaryBus[2]), self.mR3,
                                      self.mX3, self.mWindingStatus[2], self.mTR[2], self.mAng[2],
                                      0, 0, self.mMaxRatingC)
            xfmrs.append(new_3xfmr3)
        # Here create transformer object
        # In the constructor you will have to pass
        # self.mPrimaryBus[2], self.mSecondaryBus[2], self.mR3, self.mX3,
        # b=0, self.mWindingStatus[2], self.mTR[2], self.mAng[2], self.mGmag=0, self.mBmag=0,
        # self.mRating[2]
        return xfmrs
