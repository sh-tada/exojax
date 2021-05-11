from exojax.spec import rtransfer as rt
from exojax.spec import planck, moldb, contdb, response, molinfo
from exojax.spec import make_numatrix0,xsvector
from exojax.spec.lpf import xsmatrix
from exojax.spec.exomol import gamma_exomol
from exojax.spec.hitran import SijT, doppler_sigma, gamma_natural, gamma_hitran
from exojax.spec.hitrancia import read_cia, logacia 
from exojax.spec.rtransfer import rtrun, dtauM, dtauCIA
from exojax.plot.atmplot import plottau, plotcf, plot_maxpoint
import numpy as np
import tqdm
import seaborn as sns
import matplotlib.pyplot as plt
import jax.numpy as jnp
from jax import random
from jax import vmap, jit
import pandas as pd
from exojax.utils.constants import RJ, pc, Rs
import sys
from exojax.spec.evalline import mask_weakline


#FLUX reference
Fabs_REF2=2.7e-12 #absolute flux (i.e. flux@10pc) erg/s/cm2/um Burgasser+ 1303.7283 @2.3um
Rp=RJ #BD radius
fac0=Rp**2/((10.0*pc)**2) 
Ftoa=Fabs_REF2/fac0/1.e4 #erg/cm2/s/cm @ 2.3um

#loading spectrum
dat=pd.read_csv("data/luhman16a_spectra.csv",delimiter=",")
wavd=(dat["wavelength_micron"].values)*1.e4 #AA
nusd=1.e8/wavd[::-1]
fobs=(dat["normalized_flux"].values)[::-1]
err=(dat["err_normalized_flux"].values)[::-1]
plt.plot(wavd[::-1],fobs)

#masking
mask=(22930.0<wavd[::-1])*(wavd[::-1]<23010.0)
fobs=fobs[mask]
nusd=nusd[mask]
err=err[mask]
wavd=1.e8/nusd[::-1]
M=len(nusd)
plt.plot(wavd[::-1],fobs)
plt.savefig("fig/spec0.png")

#######################################################
#GENERATING A MOCK SPECTRUM PART
#######################################################

#grid for F0
N=1000
wav=np.linspace(22900,23000,N,dtype=np.float64)#AA
nus=1.e8/wav[::-1]

#ATMOSPHERE
NP=100
Parr, dParr, k=rt.pressure_layer(NP=NP)
mmw=2.33 #mean molecular weight
g=1.e5 # gravity cm/s2
beta=3.0 #IP sigma need check

ONEARR=np.ones_like(Parr) #ones_array for MMR

#LOADING CO
mdbCO=moldb.MdbExomol('.database/CO/12C-16O/Li2015',nus) #loading molecular database 
molmassCO=molinfo.molmass("CO") #molecular mass (CO)

#LOADING H2O
mdbH2O=moldb.MdbExomol('.database/H2O/1H2-16O/POKAZATEL',nus) #loading molecular dat
print(len(mdbH2O.logsij0))

molmassH2O=molinfo.molmass("H2O") #molecular mass (H2O)

#LOADING CIA
mmrH2=0.74
mmrHe=0.25
molmassH2=molinfo.molmass("H2")
molmassHe=molinfo.molmass("He")
vmrH2=(mmrH2*mmw/molmassH2)
vmrHe=(mmrHe*mmw/molmassHe)
cdbH2H2=contdb.CdbCIA('.database/H2-H2_2011.cia',nus)
cdbH2He=contdb.CdbCIA('.database/H2-He_2011.cia',nus)

### REDUCING UNNECESSARY LINES
#######################################################

#1. CO
MMR=0.1
maxMMR_CO=MMR
T0c=1700.0
Tarr = T0c*np.ones_like(Parr)    
qt=vmap(mdbCO.qr_interp)(Tarr)
gammaLMP = jit(vmap(gamma_exomol,(0,0,None,None)))\
    (Parr,Tarr,mdbCO.n_Texp,mdbCO.alpha_ref)
gammaLMN=gamma_natural(mdbCO.A)
gammaLM=gammaLMP[:,None]+gammaLMN[None,:]
SijM=jit(vmap(SijT,(0,None,None,None,0)))\
    (Tarr,mdbCO.logsij0,mdbCO.nu_lines,mdbCO.elower,qt)
sigmaDM=jit(vmap(doppler_sigma,(None,0,None)))\
    (mdbCO.nu_lines,Tarr,molmassCO)    

mask_CO,maxcf,maxcia=mask_weakline(mdbCO,Parr,dParr,Tarr,SijM,gammaLM,sigmaDM,MMR*ONEARR,molmassCO,mmw,g,vmrH2,cdbH2H2)
mdbCO.masking(mask_CO)

plot_maxpoint(mask_CO,Parr,maxcf,maxcia,mol="CO")
plt.savefig("maxpoint_CO.pdf", bbox_inches="tight", pad_inches=0.0)


#2. H2O
MMR=0.05
maxMMR_H2O=MMR
T0c=1700.0
Tarr = T0c*np.ones_like(Parr)    
qt=vmap(mdbH2O.qr_interp)(Tarr)
gammaLMP = jit(vmap(gamma_exomol,(0,0,None,None)))\
    (Parr,Tarr,mdbH2O.n_Texp,mdbH2O.alpha_ref)
gammaLMN=gamma_natural(mdbH2O.A)
gammaLM=gammaLMP[:,None]+gammaLMN[None,:]
SijM=jit(vmap(SijT,(0,None,None,None,0)))\
    (Tarr,mdbH2O.logsij0,mdbH2O.nu_lines,mdbH2O.elower,qt)
sigmaDM=jit(vmap(doppler_sigma,(None,0,None)))\
    (mdbH2O.nu_lines,Tarr,molmassH2O)    

mask_H2O,maxcf,maxcia=mask_weakline(mdbH2O,Parr,dParr,Tarr,SijM,gammaLM,sigmaDM,MMR*ONEARR,molmassH2O,mmw,g,vmrH2,cdbH2H2)

mdbH2O.masking(mask_H2O)

plot_maxpoint(mask_H2O,Parr,maxcf,maxcia,mol="H2O")
plt.savefig("maxpoint_H2O.pdf", bbox_inches="tight", pad_inches=0.0)



#nu matrix
nu0_CO=mdbCO.nu_lines
numatrix_CO=make_numatrix0(nus,nu0_CO)

nu0_H2O=mdbH2O.nu_lines
numatrix_H2O=make_numatrix0(nus,nu0_H2O)

#######################################################
#HMC-NUTS FITTING PART
#######################################################

import arviz
import numpyro.distributions as dist
import numpyro
from numpyro.infer import MCMC, NUTS
from numpyro.infer import Predictive
from numpyro.diagnostics import hpdi

#Model
def model_c(nu,y):
    An = numpyro.sample('An', dist.Normal(1.0,0.1))
    sigma = numpyro.sample('sigma', dist.Exponential(0.5))
    RV = numpyro.sample('RV', dist.Uniform(25.0,35.0))
    MMR_CO = numpyro.sample('MMR_CO', dist.Uniform(0.01,maxMMR_CO))
    MMR_H2O = numpyro.sample('MMR_H2O', dist.Uniform(0.0001,maxMMR_H2O))

    #    nu0 = numpyro.sample('nu0', dist.Uniform(-0.3,0.3))
    T0 = numpyro.sample('T0', dist.Uniform(1200.0,T0c))
    alpha = numpyro.sample('alpha', dist.Uniform(0.01,0.07))
    vsini = numpyro.sample('vsini', dist.Uniform(1.0,30.0))

    #T-P model//
    Tarr = T0*(Parr/Parr[-1])**alpha 
    
    #line computation CO
    qt_CO=vmap(mdbCO.qr_interp)(Tarr)
    SijM_CO=jit(vmap(SijT,(0,None,None,None,0)))\
        (Tarr,mdbCO.logsij0,mdbCO.dev_nu_lines,mdbCO.elower,qt_CO)
    gammaLMP_CO = jit(vmap(gamma_exomol,(0,0,None,None)))\
        (Parr,Tarr,mdbCO.n_Texp,mdbCO.alpha_ref)
    gammaLMN_CO=gamma_natural(mdbCO.A)
    gammaLM_CO=gammaLMP_CO[:,None]+gammaLMN_CO[None,:]
    sigmaDM_CO=jit(vmap(doppler_sigma,(None,0,None)))\
        (mdbCO.dev_nu_lines,Tarr,molmassCO)    
    xsm_CO=xsmatrix(numatrix_CO,sigmaDM_CO,gammaLM_CO,SijM_CO) 
    dtaumCO=dtauM(dParr,xsm_CO,MMR_CO*ONEARR,molmassCO,g)

    #line computation H2O
    qt_H2O=vmap(mdbH2O.qr_interp)(Tarr)
    SijM_H2O=jit(vmap(SijT,(0,None,None,None,0)))\
        (Tarr,mdbH2O.logsij0,mdbH2O.dev_nu_lines,mdbH2O.elower,qt_H2O)
    gammaLMP_H2O = jit(vmap(gamma_exomol,(0,0,None,None)))\
        (Parr,Tarr,mdbH2O.n_Texp,mdbH2O.alpha_ref)
    gammaLMN_H2O=gamma_natural(mdbH2O.A)
    gammaLM_H2O=gammaLMP_H2O[:,None]+gammaLMN_H2O[None,:]
    sigmaDM_H2O=jit(vmap(doppler_sigma,(None,0,None)))\
        (mdbH2O.dev_nu_lines,Tarr,molmassH2O)
    xsm_H2O=xsmatrix(numatrix_H2O,sigmaDM_H2O,gammaLM_H2O,SijM_H2O) 
    dtaumH2O=dtauM(dParr,xsm_H2O,MMR_H2O*ONEARR,molmassH2O,g)

    #CIA
    dtaucH2H2=dtauCIA(nus,Tarr,Parr,dParr,vmrH2,vmrH2,\
              mmw,g,cdbH2H2.nucia,cdbH2H2.tcia,cdbH2H2.logac)
    dtaucH2He=dtauCIA(nus,Tarr,Parr,dParr,vmrH2,vmrHe,\
              mmw,g,cdbH2He.nucia,cdbH2He.tcia,cdbH2He.logac)
    
    dtau=dtaumCO+dtaumH2O+dtaucH2H2+dtaucH2He    
    sourcef = planck.piBarr(Tarr,nus)

    F0=rtrun(dtau,sourcef)/Ftoa
#    print("mean",jnp.mean(F0))
#    print("An,sigma,MMR,RV,alpha,T0,vsini")
#    print(An,sigma,MMR,RV,alpha,T0,vsini)
    Frot=response.rigidrot(nus,F0,vsini,0.0,0.0)
    mu=response.ipgauss(nus,nusd,Frot,beta,RV)

    mu=An*mu
    numpyro.sample('y', dist.Normal(mu, sigma), obs=y)


rng_key = random.PRNGKey(0)
rng_key, rng_key_ = random.split(rng_key)
num_warmup, num_samples = 100, 200

kernel = NUTS(model_c,forward_mode_differentiation=True)
mcmc = MCMC(kernel, num_warmup, num_samples)

#------------------
dat=np.load("save.npz",allow_pickle=True)
pred,posterior_sample,predictions=dat["arr_0"]
#------------------

median_mu = jnp.median(predictions["y"],axis=0)
hpdi_mu = hpdi(predictions["y"], 0.9)

fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(20,6.0))
#plt.plot(wav[::-1],Fx0,lw=1,color="C1",label="in")
ax.plot(wavd[::-1],median_mu,color="C0")
ax.plot(wavd[::-1],fobs,"+",color="C1",label="data")
ax.fill_between(wavd[::-1], hpdi_mu[0], hpdi_mu[1], alpha=0.3, interpolate=True,color="C0",
                label="90% area")
plt.xlabel("wavelength ($\AA$)",fontsize=16)
plt.legend()
plt.savefig("fig/results.png")
plt.show()

pararr=["An","sigma","MMR","RV","alpha","T0","vsini"]
arviz.plot_trace(mcmc, var_names=pararr)
plt.savefig("fig/trace.png")
arviz.plot_pair(arviz.from_numpyro(mcmc),kind='kde',divergences=False,marginals=True) 
plt.savefig("fig/corner.png")

