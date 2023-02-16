""" short integration tests for PreMODIT cross section

    Note:
        This tests compares the results by PreMODIT with thoses by MODIT.
        If you are interested more manual comparison, see integrations/premodit/line_strength_comparison_*****.py
        ***** = exomol or hitemp, which compares cross section and line strength, starting from molecular databases. 

"""
import pytest
import pkg_resources
import pandas as pd
import numpy as np
from exojax.spec.opacalc import OpaModit
from exojax.test.emulate_mdb import mock_mdbExomol
from exojax.test.emulate_mdb import mock_mdbHitemp
from exojax.test.emulate_mdb import mock_wavenumber_grid

#The following data can be regenerated by tests/generate_xs.py
from exojax.test.data import TESTDATA_CO_EXOMOL_MODIT_XS_REF
from exojax.test.data import TESTDATA_CO_HITEMP_MODIT_XS_REF_AIR


@pytest.mark.parametrize("diffmode", [0, 1, 2])
def test_xsection_modit_hitemp(diffmode):
    from jax.config import config
    config.update("jax_enable_x64", True)
    ### DO NOT CHANGE ###
    Ttest = 1200  #fix to compare w/ precomputed xs by MODIT.
    #####################
    Ptest = 1.0
    nu_grid, wav, res = mock_wavenumber_grid()
    #temporary
    mdb = mock_mdbHitemp(multi_isotope=False)

    opa = OpaModit(
        mdb=mdb,
        nu_grid=nu_grid,
    )
    xsv = opa.xsvector(Ttest, Ptest)

    filename = pkg_resources.resource_filename(
        'exojax', 'data/testdata/' + TESTDATA_CO_HITEMP_MODIT_XS_REF_AIR)
    dat = pd.read_csv(filename, delimiter=",", names=("nus", "xsv"))
    res = np.max(np.abs(1.0 - xsv / dat["xsv"].values))
    print(res)
    #assert res < 0.01
    return opa.nu_grid, xsv


@pytest.mark.parametrize("diffmode", [0, 1, 2])
def test_xsection_premodit_exomol(diffmode):
    from jax.config import config
    config.update("jax_enable_x64", True)

    ### DO NOT CHANGE ###
    Ttest = 1200  #fix to compare w/ precomputed xs by MODIT.
    #####################
    Ptest = 1.0
    mdb = mock_mdbExomol()
    nu_grid, wav, res = mock_wavenumber_grid()
    opa = OpaPremodit(mdb=mdb,
                      nu_grid=nu_grid,
                      diffmode=diffmode,
                      auto_trange=[500.0, 1500.0])
    xsv = opa.xsvector(Ttest, Ptest)
    filename = pkg_resources.resource_filename(
        'exojax', 'data/testdata/' + TESTDATA_CO_EXOMOL_MODIT_XS_REF)
    dat = pd.read_csv(filename, delimiter=",", names=("nus", "xsv"))
    res = np.max(np.abs(1.0 - xsv / dat["xsv"].values))
    print(res)
    assert res < 0.012
    return opa.nu_grid, xsv, opa.dE, opa.Twt, opa.Tref, Ttest


if __name__ == "__main__":
    #comparison with MODIT
    from exojax.test.data import TESTDATA_CO_EXOMOL_MODIT_XS_REF
    from exojax.test.data import TESTDATA_CO_HITEMP_MODIT_XS_REF_AIR
    import matplotlib.pyplot as plt

    db = "hitemp"
    #db = "exomol"

    diffmode = 0
    if db == "exomol":
        nus, xs, dE, Twt, Tref, Tin = test_xsection_premodit_exomol(diffmode)
        filename = pkg_resources.resource_filename(
            'exojax', 'data/testdata/' + TESTDATA_CO_EXOMOL_MODIT_XS_REF)
    elif db == "hitemp":
        nus, xs, dE, Twt, Tref, Tin = test_xsection_premodit_hitemp(diffmode)
        filename = pkg_resources.resource_filename(
            'exojax', 'data/testdata/' + TESTDATA_CO_HITEMP_MODIT_XS_REF_AIR)

    dat = pd.read_csv(filename, delimiter=",", names=("nus", "xsv"))
    fig = plt.figure()
    ax = fig.add_subplot(211)
    #plt.title("premodit_xsection_test.py diffmode=" + str(diffmode))
    plt.title("diffmode=" + str(diffmode) + " T=" + str(Tin) + " Tref=" +
              str(np.round(Tref, 1)) + " Twt=" + str(np.round(Twt, 1)) +
              " dE=" + str(np.round(dE, 1)))
    ax.plot(nus, xs, label="PreMODIT", ls="dashed")
    ax.plot(nus, dat["xsv"], label="MODIT")
    plt.legend()
    plt.yscale("log")
    plt.ylabel("cross section (cm2)")
    ax = fig.add_subplot(212)
    ax.plot(nus, 1.0 - xs / dat["xsv"], label="dif = (MODIT - PreMODIT)/MODIT")
    plt.ylabel("dif")
    plt.xlabel("wavenumber cm-1")
    plt.axhline(0.01, color="gray", lw=0.5)
    plt.axhline(-0.01, color="gray", lw=0.5)
    #plt.ylim(-0.05, 0.05)
    plt.legend()
    plt.savefig("premodit" + str(diffmode) + ".png")
    plt.show()
