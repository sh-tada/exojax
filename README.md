# exojax

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

<details><summary>Auto-differentiable Radiative Transfer :heavy_check_mark: </summary> <img src="https://github.com/HajimeKawahara/exojax/blob/develop/documents/exojax.png" Titie="exojax" Width=850px> </details>

<details><summary>HMC-NUTS of Emission Spectra :heavy_check_mark: </summary></details>

<details><summary>HMC-NUTS of Transmission Spectra :x: </summary>Not supported yet. </details>

<details><summary>Cloud modeling :x: </summary> Not supported yet. </details>



## install

```
python setup.py install
```

under development since Dec. 2020.
