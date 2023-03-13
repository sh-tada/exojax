"""Atmospheric Radiative Transfer (art) class

    Notes:
        opacity is computed in art because it uses planet physical quantities 
        such as gravity, mmr.

"""
import numpy as np
import jax.numpy as jnp
from exojax.spec.planck import piBarr
from exojax.spec.rtransfer import rtrun_emis_pure_absorption
from exojax.spec.rtransfer import rtrun_trans_pure_absorption
from exojax.spec.layeropacity import layer_optical_depth
from exojax.atm.atmprof import atmprof_gray, atmprof_Guillot, atmprof_powerlow
from exojax.atm.idealgas import number_density
from exojax.atm.atmprof import normalized_layer_height
from exojax.spec.opachord import chord_geometric_matrix
from exojax.spec.opachord import chord_optical_depth
from exojax.spec.rtransfer import rtrun_trans_pure_absorption
from exojax.utils.constants import logkB, logm_ucgs


class ArtCommon():
    """Common Atmospheric Radiative Transfer
    """
    def __init__(self, nu_grid, pressure_top, pressure_btm, nlayer):
        """initialization of art

        Args:
            nu_grid (nd.array): wavenumber grid in cm-1
            pressure_top (float):top pressure in bar
            pressure_bottom (float): bottom pressure in bar
            nlayer (int): # of atmospheric layers
        """
        self.artinfo = None
        self.method = None  # which art is used
        self.ready = False  # ready for art computation
        self.Tlow = 0.0
        self.Thigh = jnp.inf

        self.nu_grid = nu_grid
        self.pressure_top = pressure_top
        self.pressure_btm = pressure_btm
        self.nlayer = nlayer
        self.check_pressure()
        self.log_pressure_btm = np.log10(self.pressure_btm)
        self.log_pressure_top = np.log10(self.pressure_top)
        self.init_pressure_profile()

        self.fguillot = 0.25

    def atmosphere_height(self, temperature, mean_molecular_weight, radius_btm,
                          gravity_btm):
        """atmosphere height and radius

        Args:
            temperature (1D array): temparature profile (Nlayer)
            mean_molecular_weight (float/1D array): mean molecular weight profile (float/Nlayer)
            radius_btm (float): the bottom radius of the atmospheric layer
            gravity_btm (float): the bottom gravity cm2/s at radius_btm, i.e. G M_p/radius_btm

        Returns:
            1D array: height normalized by radius_btm (Nlayer)
            1D array: radius normalized by radius_btm (Nlayer)
        """
        normalized_height, normalized_radius = normalized_layer_height(
            temperature, self.pressure, self.dParr, mean_molecular_weight,
            radius_btm, gravity_btm)
        return normalized_height, normalized_radius

    def constant_gravity_profile(self, value):
        return value * np.array([np.ones_like(self.pressure)]).T

    def gravity_profile(self, temperature, mean_molecular_weight, radius_btm,
                      gravity_btm):
        """gravity layer profile assuming hydrostatic equilibrium

        Args:
            temperature (1D array): temparature profile (Nlayer)
            mean_molecular_weight (float/1D array): mean molecular weight profile (float/Nlayer)
            radius_btm (float): the bottom radius of the atmospheric layer
            gravity_btm (float): the bottom gravity cm2/s at radius_btm, i.e. G M_p/radius_btm

        Returns:
            2D array: gravity in cm2/s (Nlayer, 1), suitable for the input of opacity_profile_lines
        """
        _, normalized_radius = self.atmosphere_height(temperature,
                                                      mean_molecular_weight,
                                                      radius_btm, gravity_btm)
        return jnp.array([gravity_btm / normalized_radius]).T

    def constant_mmr_profile(self, value):
        return value * np.ones_like(self.pressure)

    def opacity_profile_lines(self, xsmatrix, mixing_ratio, molmass, gravity):
        """opacity profile (delta tau) for lines

        Args:
            xsmatrix (2D array): cross section matrix (Nlayer, N_wavenumber)
            mixing_ratio (1D array): mass mixing ratio, Nlayer, (or volume mixing ratio profile)
            molmass (float): molecular mass (or mean molecular weight)
            gravity (float/1D profile): constant or 1d profile of gravity in cgs

        Returns:
            dtau: opacity profile, whose element is optical depth in each layer. 
        """
        return layer_optical_depth(self.dParr, jnp.abs(xsmatrix), mixing_ratio,
                                   molmass, gravity)

    def opacity_profile_cia(self, logacia_matrix, temperature, vmr1, vmr2, mmw,
                            gravity):
        narr = number_density(self.pressure, temperature)
        lognarr1 = jnp.log10(vmr1 * narr)  # log number density
        lognarr2 = jnp.log10(vmr2 * narr)  # log number density
        logg = jnp.log10(gravity)
        ddParr = self.dParr / self.pressure
        return 10**(logacia_matrix + lognarr1[:, None] + lognarr2[:, None] +
                    logkB - logg -
                    logm_ucgs) * temperature[:, None] / mmw * ddParr[:, None]

    def check_pressure(self):
        if self.pressure_btm < self.pressure_top:
            raise ValueError(
                "Pressure at bottom should be higher than that at top atmosphere."
            )
        if type(self.nlayer) is not int:
            raise ValueError("Number of the layer should be integer")

    def init_pressure_profile(self):
        from exojax.spec.rtransfer import pressure_layer
        self.pressure, self.dParr, self.k = pressure_layer(
            log_pressure_top=self.log_pressure_top,
            log_pressure_btm=self.log_pressure_btm,
            NP=self.nlayer,
            mode='ascending',
            numpy=True)

    
    
    def change_temperature_range(self, Tlow, Thigh):
        """temperature range to be assumed.

        Note:
            The default temperature range is self.Tlow = 0 K, self.Thigh = jnp.inf.

        Args:
            Tlow (float): lower temperature
            Thigh (float): higher temperature
        """
        self.Tlow = Tlow
        self.Thigh = Thigh

    def clip_temperature(self, temperature):
        """temperature clipping

        Args:
            temperature (array): temperature profile

        Returns:
            array: temperature profile clipped in the range of (self.Tlow-self.Thigh)
        """
        return jnp.clip(temperature, self.Tlow, self.Thigh)

    def powerlaw_temperature(self, T0, alpha):
        """powerlaw temperature profile

        Args:
            T0 (float): T at P=1 bar in K
            alpha (float): powerlaw index

        Returns:
            array: temperature profile
        """
        return self.clip_temperature(atmprof_powerlow(self.pressure, T0,
                                                      alpha))

    def gray_temperature(self, gravity, kappa, Tint):
        """ gray temperature profile

        Args:
            gravity: gravity (cm/s2)
            kappa: infrared opacity 
            Tint: temperature equivalence of the intrinsic energy flow in K

        Returns:
            array: temperature profile

        """
        return self.clip_temperature(
            atmprof_gray(self.pressure, gravity, kappa, Tint))

    def guillot_temeprature(self, gravity, kappa, gamma, Tint, Tirr):
        """ Guillot tempearture profile

        Notes:  
            Set self.fguillot (default 0.25) to change the assumption of irradiation.
            self.fguillot = 1. at the substellar point, self.fguillot = 0.5 for a day-side average 
            and self.fguillot = 0.25 for an averaging over the whole planetary surface
            See Guillot (2010) Equation (29) for details.

        Args:
            gravity: gravity (cm/s2)
            kappa: thermal/IR opacity (kappa_th in Guillot 2010)
            gamma: ratio of optical and IR opacity (kappa_v/kappa_th), gamma > 1 means thermal inversion
            Tint: temperature equivalence of the intrinsic energy flow in K
            Tirr: temperature equivalence of the irradiation in K
            
        Returns:
            array: temperature profile

        """
        return self.clip_temperature(
            atmprof_Guillot(self.pressure, gravity, kappa, gamma, Tint, Tirr,
                            self.fguillot))


class ArtEmisPure(ArtCommon):
    """Atmospheric RT for emission w/ pure absorption

    Attributes:
        pressure_layer: pressure profile in bar
        
    """
    def __init__(self,
                 nu_grid,
                 pressure_top=1.e-8,
                 pressure_btm=1.e2,
                 nlayer=100):
        """initialization of ArtEmisPure

        
        """
        super().__init__(nu_grid, pressure_top, pressure_btm, nlayer)
        self.method = "emission_with_pure_absorption"

    def run(self, dtau, temperature):
        """run radiative transfer

        Args:
            dtau (2D array): optical depth matrix, dtau  (N_layer, N_nus)
            temperature (1D array): temperature profile (Nlayer)

        Returns:
            _type_: _description_
        """
        sourcef = piBarr(temperature, self.nu_grid)
        return rtrun_emis_pure_absorption(dtau, sourcef)


class ArtTransPure(ArtCommon):
    def __init__(self,
                 nu_grid,
                 pressure_top=1.e-8,
                 pressure_btm=1.e2,
                 nlayer=100):
        """initialization of ArtTransPure

        
        """
        super().__init__(nu_grid, pressure_top, pressure_btm, nlayer)
        self.method = "transmission_with_pure_absorption"

    def run(self, dtau, temperature, mean_molecular_weight, radius_btm,
            gravity_btm):
        """run radiative transfer

        Args:
            dtau (2D array): optical depth matrix, dtau  (N_layer, N_nus)
            temperature (1D array): temperature profile (Nlayer)
            mean_molecular_weight (1D array): mean molecular weight profile, (Nlayer, from atmospheric top to bottom) 
            radius_btm (float): radius (cm) at the lower boundary of the bottom layer, R0 or r_N
            gravity_btm (float): gravity (cm/s2) at the lower boundary of the bottom layer, g_N

        Returns:
            1D array: transit squared radius in the same unit as sqaure of the radius/radius_btm

        Notes:
            This function gives the sqaure of the transit radius.
            If you would like to obtain the transit radius, take sqaure root of the output.
            If you would like to compute the transit depth, devide the output by the square of stellar radius

        """

        normalized_height, normalized_radius = self.atmosphere_height(
            temperature, mean_molecular_weight, radius_btm, gravity_btm)
        cgm = chord_geometric_matrix(normalized_height, normalized_radius)
        tauchord = chord_optical_depth(cgm, dtau)
        return rtrun_trans_pure_absorption(tauchord, normalized_radius)
