##############################################################################
##############################################################################
# Routines for
# Particle filtering based on approximate Bayesian computations
#
# Copyright (c) 2016 Johan Dahlin
# liu (at) johandahlin.com
#
##############################################################################
##############################################################################

import numpy as np
from smc_resampling import *
from smc_helpers import *

##########################################################################
# Particle filtering with ABC: main routine
##########################################################################


def proto_pf_abc(classSMC, sys):

    # Check algorithm settings and set to default if needed
    classSMC.T = sys.T
    classSMC.filterType = "abcPF"
    setSettings(classSMC, "abcfilter")

    # Initalise variables
    a = np.zeros((classSMC.nPart, sys.T))
    ar = np.zeros((classSMC.nPart, sys.T))
    p = np.zeros((classSMC.nPart, sys.T))
    v = np.zeros((classSMC.nPart, sys.T))
    v1 = np.zeros((classSMC.nPart, sys.T))
    v2 = np.zeros((classSMC.nPart, sys.T))
    w = np.zeros((classSMC.nPart, sys.T))
    xh = np.zeros((sys.T, 1))
    ess = np.zeros(sys.T)
    ll = np.zeros(sys.T)

    # Generate or set initial state
    if (classSMC.genInitialState):
        p[:, 0] = sys.generateInitialState(classSMC.nPart)
    else:
        p[:, 0] = classSMC.xo

    # Set tolerance parameter
    classSMC.epsilon = np.ones(sys.T) * classSMC.tolLevel

    #=====================================================================
    # Run main loop
    #=====================================================================

    for tt in range(0, sys.T):
        if tt != 0:

            #==================================================================
            # Resample particles
            #==================================================================

            # If resampling is enabled
            if (classSMC.resamplingInternal == 1):

                # Calculate ESS
                ess[tt] = (np.sum(w[:, tt - 1]**2))**(-1)

                # Check if ESS if below threshold, then resample
                if (ess[tt] < (classSMC.nPart * classSMC.resampFactor)):

                    if classSMC.resamplingType == "stratified":
                        nIdx = resampleStratified(w[:, tt - 1])
                        nIdx = np.transpose(nIdx.astype(int))
                        ar[:, 0:(tt - 1)] = ar[nIdx, 0:(tt - 1)]
                        ar[:, tt] = nIdx

                    elif classSMC.resamplingType == "systematic":
                        nIdx = resampleSystematic(w[:, tt - 1])
                        nIdx = np.transpose(nIdx.astype(int))
                        ar[:, 0:(tt - 1)] = ar[nIdx, 0:(tt - 1)]
                        ar[:, tt] = nIdx

                    elif classSMC.resamplingType == "multinomial":
                        nIdx = resampleMultinomial(w[:, tt - 1])
                        ar[:, 0:(tt - 1)] = ar[nIdx, 0:(tt - 1)]
                        ar[:, tt] = nIdx

                else:
                    # No resampling
                    nIdx = np.arange(0, classSMC.nPart)
                    ar[:, tt] = nIdx

            a[:, tt] = nIdx

            #==================================================================
            # Propagate particles
            #==================================================================
            p[:, tt] = sys.generateState(p[nIdx, tt - 1], tt - 1)

        #======================================================================
        # Weight particles
        #======================================================================
        (v[:, tt], v1[:, tt], v2[:, tt]) = sys.generateObservation(p[:, tt], tt)

        if (classSMC.weightdist == "boxcar"):

            # Standard ABC
            w[:, tt] = 1.0 * (np.abs(v[:, tt] - sys.y[tt]) < classSMC.tolLevel)

            # Calculate log-likelihood
            ll[tt] = np.log(np.sum(w[:, tt])) - \
                np.log(classSMC.nPart) - np.log(classSMC.tolLevel)

        elif (classSMC.weightdist == "gaussian"):

            # Smooth ABC
            w[:, tt] = loguninormpdf(sys.y[tt], v[:, tt], classSMC.tolLevel)

            # Rescale log-weights and recover weights
            wmax = np.max(w[:, tt])
            w[:, tt] = np.exp(w[:, tt] - wmax)

            # Calculate log-likelihood
            ll[tt] = wmax + np.log(np.sum(w[:, tt])) - np.log(classSMC.nPart)

        elif (classSMC.weightdist == "qcauchy"):

            # Estimate the bandwidth h of the kernel
            Sadaptive = np.var(v[:, tt])
            Padaptive = 3.0 / (8.0 * np.sqrt(np.pi)) * Sadaptive**(-5.0 / 2.0)
            hadaptive = ((5.0 * np.pi**4) /
                         (128 * classSMC.nPart * Padaptive))**(1.0 / 5.0)

            # Quasi-Cauchy ABC with adaptive epsilon
            w[:, tt] = loguniqcauchypdf(sys.y[tt], v[:, tt], hadaptive)

            # Rescale log-weights and recover weights
            wmax = np.max(w[:, tt])
            w[:, tt] = np.exp(w[:, tt] - wmax)

            # Calculate log-likelihood
            ll[tt] = wmax + np.log(np.sum(w[:, tt])) - np.log(classSMC.nPart)

        #======================================================================
        # Calculate state estimate
        #======================================================================
        w[:, tt] /= np.sum(w[:, tt])
        xh[tt] = np.sum(w[:, tt] * p[:, tt])
    
    # Sample a trajectory
    idx = np.random.choice(classSMC.nPart, 1, p=w[:, sys.T - 1])
    idx = ar[idx, sys.T - 1].astype(int)
    classSMC.xtraj = p[idx, :]

    #=====================================================================
    # Create output
    #=====================================================================
    classSMC.xhatf = xh
    classSMC.ll = np.sum(ll)
    classSMC.llt = ll
    classSMC.w = w
    classSMC.v = v
    classSMC.v1 = v1
    classSMC.v2 = v2
    classSMC.a = a
    classSMC.ar = ar
    classSMC.p = p

##############################################################################
##############################################################################
# End of file
##############################################################################
##############################################################################
