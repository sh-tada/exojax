""" short integration tests for PreMODIT spectrum"""
import pkg_resources
from jax import vmap
import jax.numpy as jnp
import pandas as pd
import numpy as np
from exojax.spec.initspec import init_premodit
from exojax.utils.grids import wavenumber_grid
from exojax.test.emulate_mdb import mock_mdbExomol
from exojax.test.emulate_mdb import mock_mdbHitemp
from exojax.spec import rtransfer as rt
from exojax.spec import molinfo
from exojax.spec.premodit import xsmatrix
from exojax.spec.rtransfer import dtauM
from exojax.spec.rtransfer import rtrun
from exojax.spec.planck import piBarr
from exojax.test.data import TESTDATA_CO_EXOMOL_MODIT_EMISSION_REF
#from exojax.test.data import TESTDATA_CO_HITEMP_MODIT_EMISSION_REF
from exojax.spec.opacalc import OpaPremodit
import pytest
from jax.config import config
config.update("jax_enable_x64", True)


@pytest.mark.parametrize("diffmode", [0, 1, 2])
def test_rt_exomol(diffmode, fig=False):
    dE = 400.0 * (diffmode + 1)

    mdb = mock_mdbExomol()
    Parr, dParr, k = rt.pressure_layer(NP=100)
    T0_in = 1300.0
    alpha_in = 0.1
    Tarr = T0_in * (Parr)**alpha_in

    MMR = 0.1
    nu_grid, wav, res = wavenumber_grid(22900.0,
                                        23100.0,
                                        15000,
                                        unit='AA',
                                        xsmode="premodit")
    Tref = 600.0
    Twt = 1200.0

    g = 2478.57
    opa = OpaPremodit(mdb=mdb, nu_grid=nu_grid, diffmode=diffmode, auto_trange=[700,1500.0])
    lbd_coeff, multi_index_uniqgrid, elower_grid, \
    ngamma_ref_grid, n_Texp_grid, R, pmarray = opa.opainfo

    Mmol = mdb.molmass
    qtarr = vmap(mdb.qr_interp)(Tarr)
    xsm = xsmatrix(Tarr, Parr, Tref, R, pmarray, lbd_coeff[0], nu_grid, ngamma_ref_grid,
                   n_Texp_grid, multi_index_uniqgrid, elower_grid, Mmol, qtarr)
    dtau = dtauM(dParr, jnp.abs(xsm), MMR * np.ones_like(Parr), Mmol, g)
    sourcef = piBarr(Tarr, nu_grid)
    F0 = rtrun(dtau, sourcef)
    filename = pkg_resources.resource_filename(
        'exojax', 'data/testdata/' + TESTDATA_CO_EXOMOL_MODIT_EMISSION_REF)
    dat = pd.read_csv(filename, delimiter=",", names=("nus", "flux"))

    # The reference data was generated by
    #
    # >>> np.savetxt("premodit_rt_test_ref.txt",np.array([nu_grid,F0]).T,delimiter=",")
    #
    # Because of errors from GPU, using pytest.approx does not pass the condition of the assertion error.
    # Instead, we use an absolute relative difference < 3 % as a condition.
    # We also note that we found the error at the edge of data exceed 2 %. Therefore, we removed the edge here.

    residual = np.abs(F0[10:12000] / dat["flux"].values[10:12000] - 1.0)
    print(np.max(residual))
    #assert np.all(residual < 0.035)
    return nu_grid, F0, dat["flux"].values


def test_rt_hitemp(fig=False):
    mdb = mock_mdbHitemp(multi_isotope=False)
    isotope = 1

    Parr, dParr, k = rt.pressure_layer(NP=100)
    T0_in = 1300.0
    alpha_in = 0.1
    Tarr = T0_in * (Parr)**alpha_in

    MMR = 0.1
    nu_grid, wav, res = wavenumber_grid(22900.0,
                                        23100.0,
                                        15000,
                                        unit='AA',
                                        xsmode="modit")
    interval_contrast = 0.1
    dit_grid_resolution = 0.1
    opa = OpaPremodit(mdb=mdb,
                      nu_grid=nu_grid,
                      diffmode=diffmode,
                      auto_trange=[500.0, 1500.0])
    lbd_coeff, multi_index_uniqgrid, elower_grid, \
        ngamma_ref_grid, n_Texp_grid, R, pmarray = opa.opainfo
    Mmol = mdb.molmass
     Ttyp = 2000.0
    g = 2478.57

    
    Mmol = molinfo.molmass_isotope("CO")
    qtarr = vmap(mdb.qr_interp, (None, 0), 0)(isotope, Tarr)
    xsm = xsmatrix(Tarr, Parr, R, pmarray, lbd, nu_grid, ngamma_ref_grid,
                   n_Texp_grid, multi_index_uniqgrid, elower_grid, Mmol, qtarr)
    dtau = dtauM(dParr, jnp.abs(xsm), MMR * np.ones_like(Parr), Mmol, g)
    sourcef = piBarr(Tarr, nu_grid)
    F0 = rtrun(dtau, sourcef)
    filename = pkg_resources.resource_filename(
        'exojax', 'data/testdata/' + TESTDATA_CO_EXOMOL_MODIT_EMISSION_REF)
    dat = pd.read_csv(filename, delimiter=",", names=("nus", "flux"))

    # The reference data was generated by
    #
    # >>> np.savetxt(TESTDATA_CO_HITEMP_PREMODIT_EMISSION_REF,np.array([nu_grid,F0]).T,delimiter=",")
    #

    residual = np.abs(F0[:12000] / dat["flux"].values[:12000] - 1.0)
    print(np.max(residual))
    assert np.all(residual < 0.035)
    return F0


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    diffmode = 0
    nus, F0, Fref = test_rt_exomol(diffmode)
    #test_rt_hitemp()

    fig = plt.figure()
    ax = fig.add_subplot(211)
    ax.plot(nus, Fref, label="MODIT")
    ax.plot(nus, F0, label="PreMODIT", ls="dashed")
    plt.legend()
    plt.yscale("log")
    plt.ylabel("cross section (cm2)")
    ax = fig.add_subplot(212)
    ax.plot(nus, 1.0 - F0 / Fref, label="dif = (MODIT - PreMODIT)/MODIT")
    plt.ylabel("dif")
    plt.xlabel("wavenumber cm-1")
    plt.axhline(0.05, color="gray", lw=0.5)
    plt.axhline(-0.05, color="gray", lw=0.5)
    plt.ylim(-0.07, 0.07)
    plt.legend()
    plt.show()
 
