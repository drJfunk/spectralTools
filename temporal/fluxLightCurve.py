# J. Michael Burgess ~April 2011


from spectralTools.models import modelLookup
from eFluxModels import modelLookup as eFluxLookup
from spectralTools.scatReader import scatReader
from scipy.integrate import quad, quadrature
from numpy import array, sqrt, zeros, vstack, asarray
import pickle



#experimental

#from numba import double, autojit, jit, void, int_, c_string_type, float_, float64
#from numba.decorators import jit, autojit





#numerical derivative 
#@autojit
def deriv(f):
#    @jit(double(double))
    def df(x):
        h=0.1e-7
        return ( f(x+h/2) - f(x-h/2) )/h

    return df



keV2erg =1.60217646e-9

#@autojit
class fluxLightCurve(object):
    '''
    The flux light curves are built from the scatReader. They can buikd both
    energy and photon flux light curves. The energy range is entered in keV.
    Light curves can be computed with or without errors but realize that the
    lightcurve object will without the errors.

    The lightcurve can be saved to a pickle file that is a dictionary.


    '''
    
    def __init__(self,scat,eMin,eMax,z=1.):

        
        self.eMin = eMin
        self.eMax = eMax

        self.z=z

        self.scat = scat


        self.tBins = scat.tBins
        self.modelNames = scat.modelNames

        self.modelDict = modelLookup
        self.eFluxModels = eFluxLookup



    def __add__(self,other):

        if other.eMin != self.eMin:
            print "eMins do not match"
            return


        if other.eMax != self.eMax:
            print "eMaxs do not match"
            return


        if other.modelNames != self.modelNames:
            print "modelNames do not match"
            return
          
        new = fluxLightCurve(self.scat,self.eMin,self.eMax)
        tBins = array(self.tBins.tolist().extend(other.tBins.tolist()) )
        new.tBins = tBins

        new.fluxes = dict(self.fluxes)
        new.fluxErrors = list(self.fluxErrors)
        new.fluxErrors.extend(other.fluxErrors)
        
        for x in self.modelNames:
            new.fluxes[x].extend(other.fluxes[x])
              

        return new 
          


 

 
    #@double(c_string_type,float64[:,:])
    def CalculateFlux(self,modelName,params):
        
        model = self.modelDict[modelName]
        if type(params[0].tolist()) == list:
                
                args = params[0].tolist()
        else:
            args = tuple(params)
        if (modelName == 'Band\'s GRB, Epeak') or (modelName =='Power Law w. 2 Breaks') or (modelName =='Broken Power Law'):
            


            val,_, = quadrature(model, self.eMin,self.eMax,args=params[0].tolist(),tol=1.49e-10, rtol=1.49e-10, maxiter=200)
            return val
            
        
        val,_, = quad(model, self.eMin,self.eMax,args=params[0].tolist(),epsabs=1.49e-08, epsrel= 1.e-5 )

        return val


    def CalculateFlux_vFvPeak(self,modelName,params):
        
        model = self.modelDict[modelName]
        if type(params[0].tolist()) == list:
                
                args = params[0].tolist()
        else:
            args = tuple(params)
        if (modelName == "Band\'s GRB, Epeak"):
            
            peak = params[0][1]

        elif (modelName == "Total Test Synchrotron"):

            peak = params[0][1]*params[0][2]**2


        else:
            return 0.
        
        val = (peak**2)*keV2erg*model(peak,*(params[0].tolist()))     

        return val


    
    def CalculateEnergyFlux(self,modelName,params):

        model = self.eFluxModels[modelName]
        #self.shit=params
        #print params
        try:
           args=params.tolist()
                
        except(AttributeError):
  
            args = tuple(params)
        #print args
        if (modelName == 'Band\'s GRB, Epeak') or (modelName =='Power Law w. 2 Breaks') or (modelName =='Broken Power Law'):

            
            
            
            val,_, = quadrature(model, self.eMin,self.eMax,args=args,tol=1.49e-10, rtol=1.49e-10, maxiter=200)
            val = val*keV2erg
            return val
            

        val,_, = quad(model, self.eMin,self.eMax,args=args[0], epsrel= 1.e-8 )

        
        val = val*keV2erg
        

        return val




    def CalculateEnergyFlux_kCor(self,modelName,params):

        model = self.eFluxModels[modelName]
        if type(params[0].tolist()) == list:
                
                args = params[0].tolist()
        else:
            args = tuple(params)
        if (modelName == 'Band\'s GRB, Epeak') or (modelName =='Power Law w. 2 Breaks') or (modelName =='Broken Power Law'):
            
            val,_, = quadrature(model, self.eMin,self.eMax,args=params[0].tolist(),tol=1.49e-10, rtol=1.49e-10, maxiter=200)
            val = val*keV2erg
            return val
            

        val,_, = quad(model, self.eMin/(1.+self.z),self.eMax/(1.+self.z),args=params[0].tolist(), epsabs=1.49e-08, epsrel= 1.e-5 )

        
        val = val*keV2erg
        

        return val



    def FluxError(self, params, covar, currentModel):
        '''
        Params is a list of the params from each models
        [mod1,mod2,...]

        '''


        

        firstDerivates = []
        
        for modName, par, z  in zip(self.scat.modelNames,params, self.scat.paramNames):

            
            #print modName
            for parName in z:

                #print parName
               

                def tmpFlux(currentPar):

                    tmpParams = par.copy()
                    tmpParams[parName]=currentPar


    #                print "\n New Tmp Params:"
     #               print tmpParams

                    return self.CalculateFlux(modName,tmpParams)




                if modName == currentModel:
                    #print "in currentModel"
                    firstDerivates.append( deriv(tmpFlux)(par[parName]))

                elif currentModel == "total":
                    #print "in total"
                    firstDerivates.append( deriv(tmpFlux)(par[parName]))
                else:
                    #print "not currentModel"
                    firstDerivates.append(0.0)

        #print firstDerivates
    
        firstDerivates = array(firstDerivates)
        tmp = firstDerivates.dot(covar)

        errors =  sqrt( tmp.dot(firstDerivates) )
        return errors


    def EnergyFluxError(self, params, covar, currentModel):
        '''
        Params is a list of the params from each models
        [mod1,mod2,...]

        '''
        firstDerivates = []
        
        for modName,par, z  in zip(self.scat.modelNames,params, self.scat.paramNames):
            
            for parName in z:

                def tmpFlux(currentPar):

                    tmpParams = asarray(par).copy()

                    tmpParams[parName]=currentPar

                    return self.CalculateEnergyFlux(modName,tmpParams)


                
                if modName == currentModel:
                    firstDerivates.append( deriv(tmpFlux)(par[parName]))

                elif currentModel == "total":
                    firstDerivates.append( deriv(tmpFlux)(par[parName]))
                else:
                    firstDerivates.append(0.0)

        firstDerivates = array(firstDerivates)
        tmp = firstDerivates.dot(covar)

        errors =  sqrt(tmp.dot(firstDerivates))
        return errors



    def EnergyFluxError_kCor(self, params, covar, currentModel):
        '''
        Params is a list of the params from each models
        [mod1,mod2,...]

        '''
        firstDerivates = []
        
        for modName,par, z  in zip(self.scat.modelNames,params, self.scat.paramNames):
            for parName in z:

                def tmpFlux(currentPar):

                    tmpParams = par.copy()

                    tmpParams[parName]=currentPar

                    return self.CalculateEnergyFlux_kCor(modName,tmpParams)


                
                if modName == currentModel:
                    firstDerivates.append( deriv(tmpFlux)(par[parName]))

                elif currentModel == "total":
                    firstDerivates.append( deriv(tmpFlux)(par[parName]))
                else:
                    firstDerivates.append(0.0)

        firstDerivates = array(firstDerivates)
        tmp = firstDerivates.dot(covar)

        errors =  sqrt(tmp.dot(firstDerivates))
        return errors


      
    def vFv_FluxError(self, params, covar, currentModel):
        '''
        Params is a list of the params from each models
        [mod1,mod2,...]

        '''


        

        firstDerivates = []
        
        for modName, par, z  in zip(self.scat.modelNames,params, self.scat.paramNames):

            
            #print modName
            for parName in z:

                #print parName
               

                def tmpFlux(currentPar):

                    tmpParams = par.copy()
                    tmpParams[parName]=currentPar


    #                print "\n New Tmp Params:"
     #               print tmpParams

                    return self.CalculateFlux_vFvPeak(modName,tmpParams)




                if modName == currentModel:
                    #print "in currentModel"
                    firstDerivates.append( deriv(tmpFlux)(par[parName]))

                elif currentModel == "total":
                    #print "in total"
                    firstDerivates.append( deriv(tmpFlux)(par[parName]))
                else:
                    #print "not currentModel"
                    firstDerivates.append(0.0)

        #print firstDerivates
    
        firstDerivates = array(firstDerivates)
        tmp = firstDerivates.dot(covar)

        errors =  sqrt( tmp.dot(firstDerivates) )
        return errors


    def FormatCovarMat(self):


        length = self.scat.numParams
        
        self.covars = []
      
        for x in self.scat.covars:
            
            covar = []
    

            for i in range(length):
                

                tmp = []

                for j in range(length):
                   

                    #tmp.append(x[i*length+j])
                    tmp.append(x[i][j])

                covar.append(tmp)
                    
            self.covars.append(array(covar))

    


    


    #@void()
    def CreateLightCurve(self):


        fluxes = []

        numSteps = len(self.scat.meanTbins)

        i=0

        for x in self.modelNames:

            tmp = []

            for pars in self.scat.models[x]['values']:

                flux = self.CalculateFlux(x,pars)
                tmp.append(flux)
                i=i+1
                print "Completed "+str(i)+" of "+str(numSteps)+" fluxes for "+x+"\n\n"

            fluxes.append(tmp)

       
        fluxes = map(array,fluxes)

        totFlux = zeros(len(fluxes[0]))

        for x in fluxes:
            totFlux+=x

        fluxes.append(totFlux)

        tmp = list(self.modelNames)
        tmp.append('total')

        self.fluxes = dict(zip(tmp,fluxes))



    def CreateEnergyLightCurve(self):
        

        fluxes = []
        numSteps = len(self.scat.meanTbins)

        i=0

        for x in self.modelNames:

            tmp = []

            for pars in self.scat.models[x]['values']:
                #print pars
                flux = self.CalculateEnergyFlux(x,pars)
                tmp.append(flux)
                i=i+1
                print "Completed "+str(i)+" of "+str(numSteps)+" fluxes\n\n"

            fluxes.append(tmp)

       
        fluxes = map(array,fluxes)

        totFlux = zeros(len(fluxes[0]))

        for x in fluxes:
            totFlux+=x

        fluxes.append(totFlux)

        tmp = list(self.modelNames)
        tmp.append('total')

        self.energyFluxes = dict(zip(tmp,fluxes))


    def CreateEnergyLightCurve_kCor(self,z=1.):
        

        fluxes = []
        numSteps = len(self.scat.meanTbins)

        i=0

        for x in self.modelNames:

            tmp = []

            for pars in self.scat.models[x]['values']:
                
                flux = self.CalculateEnergyFlux_kCor(x,pars)
                tmp.append(flux)
                i=i+1
                print "Completed "+str(i)+" of "+str(numSteps)+" fluxes\n\n"

            fluxes.append(tmp)

       
        fluxes = map(array,fluxes)

        totFlux = zeros(len(fluxes[0]))

        for x in fluxes:
            totFlux+=x

        fluxes.append(totFlux)

        tmp = list(self.modelNames)
        tmp.append('total')

        self.energyFluxes_kCor = dict(zip(tmp,fluxes))

        
    def CreatePeakCurve(self):


        fluxes = []

        numSteps = len(self.scat.meanTbins)

        i=0

        for x in self.modelNames:

            tmp = []

            for pars in self.scat.models[x]['values']:

                flux = self.CalculateFlux_vFvPeak(x,pars)
                tmp.append(flux)
                i=i+1
                print "Completed "+str(i)+" of "+str(numSteps)+" fluxes for "+x+"\n\n"

            fluxes.append(tmp)

       
        fluxes = map(array,fluxes)

        totFlux = zeros(len(fluxes[0]))

        for x in fluxes:
            totFlux+=x

        fluxes.append(totFlux)

        tmp = list(self.modelNames)
        tmp.append('total')

        self.vFv_fluxes = dict(zip(tmp,fluxes))






    def LightCurveErrors(self):

        self.FormatCovarMat()

        tmpParamArray = map(lambda x: [] ,self.tBins)
        

        individualFluxError=[]
        for mod in self.modelNames:
            
            
            for x,row in zip(self.scat.models[mod]['values'],tmpParamArray):
                row.append(x)

        for mod in self.modelNames:
            
            individualFluxError.append(map(lambda par,cov:self.FluxError(par,cov,mod), tmpParamArray,self.covars  ))
        
        
        individualFluxError.append ( map(lambda par,cov:self.FluxError(par,cov,"total"), tmpParamArray,self.covars  ))
        #self.fluxErrors= map(lambda par,cov:self.FluxError(par,cov,"total"), tmpParamArray,self.covars  )
        self.fluxErrors=dict(zip(self.modelNames+['total'],individualFluxError))


    def vFv_LightCurveErrors(self):

        self.FormatCovarMat()

        tmpParamArray = map(lambda x: [] ,self.tBins)
        

        individualFluxError=[]
        for mod in self.modelNames:
            
            
            for x,row in zip(self.scat.models[mod]['values'],tmpParamArray):
                row.append(x)

        for mod in self.modelNames:
            
            individualFluxError.append(map(lambda par,cov:self.vFv_FluxError(par,cov,mod), tmpParamArray,self.covars  ))
        
        
        individualFluxError.append ( map(lambda par,cov:self.vFv_FluxError(par,cov,"total"), tmpParamArray,self.covars  ))
        #self.fluxErrors= map(lambda par,cov:self.FluxError(par,cov,"total"), tmpParamArray,self.covars  )
        self.vFv_fluxErrors=dict(zip(self.modelNames+['total'],individualFluxError))



                    
    def EnergyLightCurveErrors(self):

        self.FormatCovarMat()

        tmpParamArray = map(lambda x: [] ,self.tBins)
        

        individualFluxError=[]
        for mod in self.modelNames:
            
            
            for x,row in zip(self.scat.models[mod]['values'],tmpParamArray):
                row.append(x)

        for mod in self.modelNames:
            
            individualFluxError.append(map(lambda par,cov:self.EnergyFluxError(par,cov,mod), tmpParamArray,self.covars  ))
        
        
        individualFluxError.append ( map(lambda par,cov:self.EnergyFluxError(par,cov,"total"), tmpParamArray,self.covars  ))
        #self.fluxErrors= map(lambda par,cov:self.FluxError(par,cov,"total"), tmpParamArray,self.covars  )
        self.energyFluxErrors=dict(zip(list(self.modelNames)+['total'],individualFluxError))        




    def EnergyLightCurveErrors_kCor(self):

        self.FormatCovarMat()

        tmpParamArray = map(lambda x: [] ,self.tBins)
        

        individualFluxError=[]
        for mod in self.modelNames:
            
            
            for x,row in zip(self.scat.models[mod]['values'],tmpParamArray):
                row.append(x)

        for mod in self.modelNames:
            
            individualFluxError.append(map(lambda par,cov:self.EnergyFluxError_kCor(par,cov,mod), tmpParamArray,self.covars  ))
        
        
        individualFluxError.append ( map(lambda par,cov:self.EnergyFluxError_kCor(par,cov,"total"), tmpParamArray,self.covars  ))
        #self.fluxErrors= map(lambda par,cov:self.FluxError(par,cov,"total"), tmpParamArray,self.covars  )
        self.energyFluxErrors_kCor=dict(zip(self.modelNames+['total'],individualFluxError))        



    def Save(self,fileName='fluxSave.p'):


        dicString=['fluxes','errors','tBins','energies']
        save = dict(zip(dicString,[self.fluxes,self.fluxErrors,self.tBins,[self.eMin,self.eMax]]))

        pickle.dump(save,open(fileName,'w'))


    def SaveVFV(self,fileName='vFv_fluxSave.p'):


        dicString=['fluxes','errors','tBins','energies']
        save = dict(zip(dicString,[self.vFv_fluxes,self.vFv_fluxErrors,self.tBins,[self.eMin,self.eMax]]))

        pickle.dump(save,open(fileName,'w'))


    def SaveEnergy(self,fileName='energyFluxSave.p'):


        dicString=['energy fluxes','errors','tBins','energies']
        save = dict(zip(dicString,[self.energyFluxes,self.energyFluxErrors,self.tBins,[self.eMin,self.eMax]]))

        pickle.dump(save,open(fileName,'w'))

    def SaveEnergy_kCor(self,fileName='kCor_energyFluxSave.p'):


        dicString=['energy fluxes','errors','tBins','energies']
        save = dict(zip(dicString,[self.energyFluxes_kCor,self.energyFluxErrors_kCor,self.tBins,[self.eMin,self.eMax]]))

        pickle.dump(save,open(fileName,'w'))
        











