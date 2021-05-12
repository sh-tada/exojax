# exojax

## Functions

<details open><summary>Voigt Profile :heavy_check_mark: </summary>

```python
 from exojax.spec import voigt
 nu=numpy.linspace(-10,10,100)
 voigt(nu,1.0,2.0) #sigma_D=1.0, gamma_L=2.0
```

</details>

<details><summary>Cross Section using HITRAN/HITEMP/ExoMol :heavy_check_mark: </summary>
 
```python
 from exojax.spec import AutoXS
 nus=numpy.linspace(1900.0,2300.0,40000,dtype=numpy.float64) #wavenumber (cm-1)
 autoxs=AutoXS(nus,"ExoMol","CO") #using ExoMol CO (12C-16O). HITRAN and HITEMP are also supported.  
 xsv=autoxs.xsection(1000.0,1.0) #cross section for 1000K, 1bar (cm2)
```

 <img src="https://user-images.githubusercontent.com/15956904/111430765-2eedf180-873e-11eb-9740-9e1a313d590c.png" Titie="exojax auto cross section" Width=850px> </details>


When you want to plot the line strength...

```python
 ls=autoxs.linest(1000.0,1.0) #line strength for 1000K, 1bar (cm)
 plt.plot(autoxs.mdb.nu_lines,ls,".")
```

<details><summary>Emission Spectrum :heavy_check_mark: </summary>

```python
 from exojax.rtransfer import nugrid
 from exojax.spec import AutoRT
 nus,wav,res=nugrid(1900.0,2300.0,40000,"cm-1")
 Parr=numpy.logspace(-8,2,100)
 Tarr = 500.*(Parr/Parr[-1])**0.02    
 autort=AutoRT(nus,1.e5,2.33,Tarr,Parr) #g=1.e5 cm/s2, mmw=2.33
 autort.addcia("H2-H2",0.74,0.74)       #CIA, mmr(H)=0.74
 autort.addcia("H2-He",0.74,0.25)       #CIA, mmr(He)=0.25
 autort.addmol("ExoMol","CO",0.01)      #CO line, mmr(CO)=0.01
 F=autort.rtrun()
```

 <img src="https://user-images.githubusercontent.com/15956904/116488770-286ea000-a8ce-11eb-982d-7884b423592c.png" Titie="exojax auto \emission spectrum" Width=850px> 

 <details><summary>:telescope: Are you an observer? </summary>
 
 ```python
  nusobs=numpy.linspace(1900.0,2300.0,10000,dtype=np.float64) #observation wavenumber bin (cm-1)
  F=autort.spectrum(nusobs,100000.0,20.0,0.0) #R=100000, vsini=10km/s, RV=0km/s
 ```
 
  <img src="https://user-images.githubusercontent.com/15956904/116488769-273d7300-a8ce-11eb-8da1-661b23215c26.png" Titie="exojax auto \emission spectrum for observers" Width=850px> 
 
 </details>


</details>

<details><summary>HMC-NUTS of Emission Spectra :heavy_check_mark: </summary>
<img src="https://user-images.githubusercontent.com/15956904/117563416-b02f8800-b0e0-11eb-8c0c-3a5087aa31c6.png" Titie="exojax" Width=850px>
</details>

<details><summary>HMC-NUTS of Transmission Spectra :x: </summary>Not supported yet. </details>

<details><summary>Cloud modeling :x: </summary> Not supported yet. </details>



## Installation

```
python setup.py install
```

<details><summary> Note on installation w/ GPU support</summary>

:books: You need to install CUDA, NumPyro, JAX w/ NVIDIA GPU support, and cuDNN. 

- NumPyro

exojax supports NumPyro >0.5.0, which enables [the forward differentiation of HMC-NUTS](http://num.pyro.ai/en/latest/mcmc.html#numpyro.infer.hmc.NUTS). Please check the required JAX version by NumPyro. In May 2021, it seems the recent version of [NumPyro](https://github.com/pyro-ppl/numpyro) requires jaxlib>=0.1.62 (see [setup.py](https://github.com/pyro-ppl/numpyro/blob/master/setup.py) of NumPyro for instance). 

- JAX

Check you cuda version:

```
nvcc -V
```

Install such as

```
pip install --upgrade jax jaxlib==0.1.62+cuda112  -f https://storage.googleapis.com/jax-releases/jax_releases.html
```

In this case, jaxlib version is 0.1.62 and cuda version is 11.2. You can check which cuda version is avaiable at [here](https://storage.googleapis.com/jax-releases/jax_releases.html)

Visit [here](https://github.com/google/jax) for the details.

- cuDNN

For instance, get .deb from NVIDIA and install such as

```
sudo dpkg -i libcudnn8_8.2.0.53-1+cuda11.3_amd64.deb
```

cuDNN is used for to compute the astronomical/instrumental response for the large number of wave number grid (exojax.spec.response). Otherwise, we do not use it. 

</details>

## License

Copyright 2020-2021 [Hajime Kawahara](http://secondearths.sakura.ne.jp/en/index.html). exojax is publicly available under the MIT license. Under development since Dec. 2020.
