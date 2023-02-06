""" short integration tests for PreMODIT spectrum"""
import pkg_resources
from jax import vmap
import jax.numpy as jnp
import pandas as pd
import numpy as np
#from exojax.spec.initspec import init_premodit
from exojax.utils.grids import wavenumber_grid
from exojax.test.emulate_mdb import mock_mdbExomol
from exojax.test.emulate_mdb import mock_mdbHitemp
from exojax.spec import rtransfer as rt
from exojax.spec import molinfo

from exojax.spec.rtransfer import dtauM
from exojax.spec.rtransfer import rtrun
from exojax.spec.planck import piBarr
from exojax.test.data import TESTDATA_CO_EXOMOL_MODIT_EMISSION_REF
from exojax.test.data import TESTDATA_CO_HITEMP_MODIT_EMISSION_REF
from exojax.spec.opacalc import OpaPremodit
import pytest
from jax.config import config

config.update("jax_enable_x64", True)

def select_xsmatrix(diffmode):
    from exojax.spec.premodit import xsmatrix_zeroth
    from exojax.spec.premodit import xsmatrix_first
    from exojax.spec.premodit import xsmatrix_second

    if diffmode == 0:
        return xsmatrix_zeroth
    elif diffmode == 1:
        return xsmatrix_first
    elif diffmode == 2:
        return xsmatrix_second
    else:
        raise ValueError("diffmode should be 0, 1, 2.")

@pytest.mark.parametrize("diffmode", [0, 1, 2])
def test_rt_exomol(diffmode, fig=False):
    dE = 400.0 * (diffmode + 1)
    xsmatrix = select_xsmatrix(diffmode)
    mdb = mock_mdbExomol()
    Parr, dParr, k = rt.pressure_layer(NP=100, numpy=True)
    T0_in = 1300.0
    alpha_in = 0.1
    Tarr = T0_in * (Parr)**alpha_in
    Tarr[Tarr<400.0] = 400.0 #lower limit
    Tarr[Tarr>1500.0] = 1500.0 #upper limit
    
    
    MMR = 0.1
    nu_grid, wav, res = wavenumber_grid(22900.0,
                                        23100.0,
                                        15000,
                                        unit='AA',
                                        xsmode="premodit")

    g = 2478.57
    opa = OpaPremodit(mdb=mdb,
                      nu_grid=nu_grid,
                      diffmode=diffmode,
                      auto_trange=[400, 1500.0],
                      dit_grid_resolution=0.1)
    lbd_coeff, multi_index_uniqgrid, elower_grid, \
    ngamma_ref_grid, n_Texp_grid, R, pmarray = opa.opainfo
    print("dE=", opa.dE, "cm-1")
    Mmol = mdb.molmass
    qtarr = vmap(mdb.qr_interp)(Tarr)

    xsm = xsmatrix(Tarr, Parr, opa.Tref, opa.Twt, R, pmarray, lbd_coeff, nu_grid,
                   ngamma_ref_grid, n_Texp_grid, multi_index_uniqgrid,
                   elower_grid, Mmol, qtarr)
    dtau = dtauM(dParr, jnp.abs(xsm), MMR * np.ones_like(Parr), Mmol, g)
    sourcef = piBarr(Tarr, nu_grid)
    F0 = rtrun(dtau, sourcef)
    filename = pkg_resources.resource_filename(
        'exojax', 'data/testdata/' + TESTDATA_CO_EXOMOL_MODIT_EMISSION_REF)
    dat = pd.read_csv(filename, delimiter=",", names=("nus", "flux"))
    residual = np.abs(F0 / dat["flux"].values - 1.0)
    print(np.max(residual))
    assert np.all(residual < 0.01)
    return nu_grid, F0, dat["flux"].values


def test_rt_hitemp(diffmode, fig=False):
    xsmatrix = select_xsmatrix(diffmode)
    mdb = mock_mdbHitemp(multi_isotope=False)
    isotope = 1

    Parr, dParr, k = rt.pressure_layer(NP=100, numpy=True)
    T0_in = 1300.0
    alpha_in = 0.1
    Tarr = T0_in * (Parr)**alpha_in
    Tarr[Tarr<400.0] = 400.0 #lower limit
    Tarr[Tarr>1500.0] = 1500.0 #upper limit
    
    MMR = 0.1
    nu_grid, wav, res = wavenumber_grid(22900.0,
                                        23100.0,
                                        15000,
                                        unit='AA',
                                        xsmode="premodit")
    dit_grid_resolution = 0.2
    opa = OpaPremodit(mdb=mdb,
                      nu_grid=nu_grid,
                      diffmode=diffmode,
                      auto_trange=[400.0, 1500.0],
                      dit_grid_resolution=dit_grid_resolution)
    lbd_coeff, multi_index_uniqgrid, elower_grid, \
        ngamma_ref_grid, n_Texp_grid, R, pmarray = opa.opainfo
    Mmol = mdb.molmass
    g = 2478.57

    Mmol = molinfo.molmass_isotope("CO")
    qtarr = vmap(mdb.qr_interp, (None, 0), 0)(isotope, Tarr)
    xsm = xsmatrix(Tarr, Parr, opa.Tref, opa.Twt, R, pmarray, lbd_coeff, nu_grid,
                   ngamma_ref_grid, n_Texp_grid, multi_index_uniqgrid,
                   elower_grid, Mmol, qtarr)
    dtau = dtauM(dParr, jnp.abs(xsm), MMR * np.ones_like(Parr), Mmol, g)
    sourcef = piBarr(Tarr, nu_grid)
    F0 = rtrun(dtau, sourcef)


    filename = pkg_resources.resource_filename(
        'exojax', 'data/testdata/' + TESTDATA_CO_HITEMP_MODIT_EMISSION_REF)
    dat = pd.read_csv(filename, delimiter=",", names=("nus", "flux"))
    residual = np.abs(F0/ dat["flux"].values - 1.0)
    print(np.max(residual))
    assert np.all(residual < 0.01)
    return nu_grid, F0, dat["flux"].values


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    diffmode = 2
    nus, F0, Fref = test_rt_exomol(diffmode)
    nus_hitemp, F0_hitemp, Fref_hitemp = test_rt_hitemp(diffmode)

    fig = plt.figure()
    ax = fig.add_subplot(311)
    ax.plot(nus, Fref, label="MODIT (ExoMol)")
    ax.plot(nus, F0, label="PreMODIT (ExoMol)", ls="dashed")
    plt.legend()
    #plt.yscale("log")
    ax = fig.add_subplot(312)
    ax.plot(nus_hitemp, Fref_hitemp, label="MODIT (HITEMP)")
    ax.plot(nus_hitemp, F0_hitemp, label="PreMODIT (HITEMP)", ls="dashed")
    plt.legend()
    plt.ylabel("cross section (cm2)")
    
    ax = fig.add_subplot(313)
    ax.plot(nus, 1.0 - F0 / Fref, alpha=0.7, label="dif = (MO - PreMO)/MO Exomol")
    ax.plot(nus_hitemp, 1.0 - F0_hitemp / Fref_hitemp, alpha=0.7,label="dif = (MO - PreMO)/MO HITEMP")
    
    #plt.ylabel("dif")
    plt.xlabel("wavenumber cm-1")
    plt.axhline(0.05, color="gray", lw=0.5)
    plt.axhline(-0.05, color="gray", lw=0.5)
    plt.axhline(0.01, color="gray", lw=0.5)
    plt.axhline(-0.01, color="gray", lw=0.5)
    plt.ylim(-0.07, 0.07)
    plt.legend()
    plt.show()
