#!/usr/bin/python3
# -*- coding: utf-8 -*-
## @namespace Col_LP
# Created on Tue Oct 31 11:11:33 2017
# Author
# Alejandro Pena-Bello
# alejandro.penabello@unige.ch
# This script prepares the input for the LP algorithm and get the output in a dataframe, finally it saves the output.
# Description
# -----------
# INPUTS
# ------
# OUTPUTS
# -------
# TODO
# ----
# User Interface, including path to save the results and choose countries, load curves, etc.
# Simplify by merging select_data and load_data and probably load_param.
# Requirements
# ------------
# Pandas, numpy, pyomo, pickle, math, sys,glob, time

import pandas as pd
import paper_classes as pc
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
from pyomo.core import Var
import time
import numpy as np
import HP_pyomo_model as optim
import math
import pickle
import sys
import glob
from functools import wraps
import csv
import os
import tempfile
import matplotlib.pyplot as plt
import threading
import itertools
from pathlib import Path


def fn_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        #print ("Total time running %s: %s seconds" %
               #(function.__name__, str(t1-t0))
               #)
        return result
    return function_timer

def Get_output(instance):
    '''
    Gets the model output and transforms it into a pandas dataframe
	with the desired names.
    Parameters
    ----------
    instance : instance of pyomo
    Returns
    -------
    df : DataFrame
    P_max_ : vector of daily maximum power
    '''
    #to write in a csv goes faster than actualize a df
    global_lock = threading.Lock()
    while global_lock.locked():
        continue
    global_lock.acquire()
    np.random.seed()
    filename='out'+str(np.random.randint(1, 10, 10))[1:-1].replace(" ", "")+'.csv'
    with open(filename, 'a') as f:
        writer = csv.writer(f, delimiter=';')
        for v in instance.component_objects(Var, active=True):
            varobject = getattr(instance, str(v))
            for index in varobject:
                writer.writerow([index, varobject[index].value, v])
    df=pd.read_csv(filename,sep=';',names=['val','var'])
    os.remove(filename)
    global_lock.release()
    df=df.pivot_table(values='val', columns='var',index=df.index)
    df=df.drop(-1)
    ##print(filename)
    return df
@fn_timer
def Optimize(data_input,param):

    """
    This function calls the LP and controls the aging. The aging is then
    calculated in daily basis and the capacity updated. When the battery
    reaches the EoL the loop breaks. 'days' allows to optimize multiple days at once.

    Parameters
    ----------
    Capacity : float
    Tech : string
    App_comb : array
    Capacity_tariff : float
    data_input: DataFrame
    param: dict
    PV_nom: float

    Returns
    -------
    df : DataFrame
    aux_Cap_arr : array
    SOH_arr : array
    Cycle_aging_factor : array
    P_max_arr : array
    results_arr : array
    cycle_cal_arr : array
    DoD_arr : array
    """
    days=1
    dt=param['delta_t']
    end_d=int(param['ndays']*24/dt)
    window=int(24*days/dt)

    print('%%%%%%%%% Optimizing %%%%%%%%%%%%%%%')
    results_arr=[]
    Cooling=0
    width=200
    data_input.loc[:,'Temp_supply']=data_input['Temp_supply'].rolling(window=width).mean().bfill()
    data_input.loc[:,'Temp_supply_tank']=data_input['Temp_supply_tank'].copy().rolling(window=width).mean().bfill()
    data_input['T_aux_supply'] = data_input.apply(lambda row: row.Temp_supply+10,axis=1)
    for i in range(int(param['ndays']/days)):
        print(i, end='')
        toy=0
        data_input_=data_input[data_input.index.dayofyear==data_input.index.dayofyear[0]+i]
        if i==0:
            SOH=1
            T_init=data_input[data_input.index.dayofyear==data_input.index.dayofyear[0]+i].Temp_supply[0]
        else:
            T_init=T_init_
        if data_input.index.dayofyear[0]+i==120:
            toy=1
        elif data_input.index.dayofyear[0]+i==274:
            toy=3
        elif (data_input.index.dayofyear[0]+i<274)&(data_input.index.dayofyear[0]+i>120):
            toy=2
        if param['Cooling_ind']:
            if toy==2:
                Cooling=1
        retail_price_dict=dict(enumerate(data_input_.Price_DT))
        
        for col in data_input_.keys():
            param.update({col:dict(enumerate(data_input_[col]))})
        Set_declare=np.arange(-1,data_input_.shape[0])
        
        param.update({'dayofyear':data_input.index.dayofyear[0]+i,
                      'toy':toy,
                      'subset_tank_day':(np.arange(1,97/3)*3).astype(int),
                      'Set_declare':Set_declare,
                      'Cooling':Cooling,'T_init':T_init,'retail_price':retail_price_dict})
        print(param)
        
        instance = optim.Concrete_model(param)
        global_lock = threading.Lock()
        while global_lock.locked():
            continue
        global_lock.acquire()
        if sys.platform=='win32':
            opt = SolverFactory('cplex')
            opt.options["threads"]=1
            opt.options["mipgap"]=0.001
        else:
            opt = SolverFactory('cplex',executable='/opt/ibm/ILOG/'
                            'CPLEX_Studio1271/cplex/bin/x86-64_linux/cplex')
            opt.options["threads"]=1
            opt.options["mipgap"]=0.001
        results = opt.solve(instance,tee=True)
        results.write(num=1)
        global_lock.release()

        if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):
        # Do something when the solution is optimal and feasible
            df_1=Get_output(instance)
            #df_1.to_csv('out.csv')
            #print(df_1)
            T_init_=df_1.loc[df_1.index[-1],'T_ts']
            results_arr.append(instance.total_cost())
            if i==0:#initialize
                df=pd.DataFrame(df_1)
            elif i==param['ndays']-1:#if we go until the end of the days
                df=df.append(df_1,ignore_index=True)
            else:#if SOH or ndays are greater than the limit
                df=df.append(df_1,ignore_index=True)
        elif (results.solver.termination_condition == TerminationCondition.infeasible):
            results.write(num=1)
            # Do something when model is infeasible
            #print('Termination condition',results.solver.termination_condition)
            return (None,None,None,None,None,None,None,None,results)
        else:
            results.write(num=1)
            # Something else is wrong
            #print ('Solver Status: ',  results.solver.status)
            return (None,None,None,None,None,None,None,None,results)
    end_d=df.shape[0]
    df=pd.concat([df,data_input.loc[data_input.index[:end_d]].reset_index()],axis=1)

    df['Req_kWh']=data_input.Req_kWh.reset_index(drop=True)[:end_d].values
    df['Req_kWh_DHW']=data_input.Req_kWh_DHW.reset_index(drop=True)[:end_d].values
    df['Set_T']=data_input.Set_T.reset_index(drop=True)[:end_d].values
    df['Temp']=data_input.Temp.reset_index(drop=True)[:end_d].values
    df['Temp_supply']=data_input.Temp_supply.reset_index(drop=True)[:end_d].values
    df['Temp_supply_tank']=data_input.Temp_supply_tank.reset_index(drop=True)[:end_d].values
    df['T_aux_supply']=data_input.Temp_supply_tank.reset_index(drop=True)[:end_d].values
    df['COP_tank']=data_input.COP_tank.reset_index(drop=True)[:end_d].values
    df['COP_SH']=data_input.COP_SH.reset_index(drop=True)[:end_d].values
    df['COP_DHW']=data_input.COP_DHW.reset_index(drop=True)[:end_d].values
    df['Cooling']=data_input.Cooling.reset_index(drop=True)[:end_d].values
    df.set_index('index',inplace=True)
    return df


def load_obj(name ):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)
def load_param(combinations):
    '''
    Description
    -----------
    Load all parameters into a dictionary,  time
    resolution (0.25), number of years or days if only some days want to be
    optimized.


    Parameters
    ----------
    

    Returns
    ------
    param: dict
    Comments
    -----
    week 18 day 120 is transtion from cooling to heating
    week 40 day 274 is transtion from cooling to heating
    '''
    print('##############')
    print('load data')
    #################################################
    design_param=load_obj('../Input/dict_design_oct')
    dt=0.25
    nyears=1
    days=365
    testing=True
    cooling=False
    week=1
    conf=combinations['conf']
######################################################

    
    filename_heat=Path('../Input/preprocessed_heat_demand_2_new_Oct.csv')
    filename_prices=Path('../Input/Prices_2017.csv')

    if (combinations['house_type']=='SFH15')| (combinations['house_type']=='SFH45'):
        aux_name='SFH15_45'
    else:
        aux_name='SFH100'

    fields_heat=['index','Set_T','Temp', combinations['house_type']+'_kWh','DHW_kWh', 'Temp_supply_'+aux_name,'Temp_supply_'+aux_name+'_tank',
                'COP_'+combinations['house_type'],'hp_'+combinations['house_type']+'_el_cons','COP_'+combinations['house_type']+'_DHW',
                 'hp_'+combinations['house_type']+'_el_cons_DHW','COP_'+combinations['house_type']+'_tank',
                 'hp_'+combinations['house_type']+'_tank_el_cons']
    new_cols=['Set_T','Temp', 'Req_kWh','Req_kWh_DHW','Temp_supply','Temp_supply_tank','COP_SH','COP_tank','COP_DHW',
              'hp_sh_cons','hp_tank_cons','hp_dhw_cons']
    df_heat=pd.read_csv(filename_heat,engine='python',sep=';',index_col=[0],
                        parse_dates=[0],infer_datetime_format=True, usecols=fields_heat)
    df_heat.columns=new_cols


    if np.issubdtype(df_heat.index.dtype, np.datetime64):
        df_heat.index=df_heat.index.tz_localize('UTC').tz_convert('Europe/Brussels')
    else:
        df_heat.index=pd.to_datetime(df_heat.index,utc=True)
        df_heat.index=df_heat.index.tz_convert('Europe/Brussels')

    fields_prices=['index', 'Price_flat', 'Price_DT', 'Export_price', 'Price_flat_mod',
   'Price_DT_mod']
    df_prices=pd.read_csv(filename_prices,engine='python',sep=',|;',index_col=[0],
                        parse_dates=[0],infer_datetime_format=True ,usecols=fields_prices)

    if np.issubdtype(df_prices.index.dtype, np.datetime64):
        df_prices.index=df_prices.index.tz_localize('UTC').tz_convert('Europe/Brussels')
    else:
        df_prices.index=pd.to_datetime(df_prices.index,utc=True)
        df_prices.index=df_prices.index.tz_convert('Europe/Brussels')
    
    data_input=pd.concat([df_heat,df_prices],axis=1,copy=True,sort=False)
    #skip the first DHW data since cannot be produced simultaneously with SH
    data_input.loc[(data_input.index.hour<2),'Req_kWh_DHW']=0
    T_var=data_input.Temp.resample('1d').mean()
    data_input['T_var']=T_var
    data_input.T_var=data_input.T_var.fillna(method='ffill')
    data_input['Cooling']=0
    data_input.loc[((data_input.index.month<=4)|(data_input.index.month>=10))&(data_input.Req_kWh<0),'Req_kWh']=0
    if cooling:
        data_input.loc[(data_input.index.month>4)&(data_input.index.month<10)&(data_input.T_var>20),'Cooling']=1#is T_var>20 then we need to cool only
        data_input.loc[(data_input.Cooling==1)&(data_input.Req_kWh>0),'Req_kWh']=0#if we should cool then ignore the heating requirements
        data_input.loc[(data_input.Cooling==1),'Req_kWh']=abs(data_input.loc[(data_input.Cooling==1),'Req_kWh'])

    data_input.loc[(data_input.index.month>4)&(data_input.index.month<10)&(data_input.Cooling==0),'Req_kWh']=0#if we should heat then ignore the cooling requirements
    data_input['Temp']=data_input['Temp']+273.15
    data_input['Set_T']=data_input['Set_T']+273.15
    data_input['Temp_supply']=data_input['Temp_supply']+273.15
    data_input['Temp_supply_tank']=data_input['Temp_supply_tank']+273.15
    data_input.loc[data_input.index.dayofyear==120,'Req_kWh']=0
    data_input.loc[data_input.index.dayofyear==274,'Req_kWh']=0
    data_input.loc[(data_input.index.dayofyear<120)|(data_input.index.dayofyear>274),'season']=0#'heating'
    data_input.loc[data_input.index.dayofyear==120,'season']=1#'transition_heating_cooling'
    data_input.loc[(data_input.index.dayofyear>120)&(data_input.index.dayofyear<274),'season']=2#'cooling'
    data_input.loc[data_input.index.dayofyear==274,'season']=3#'transition_cooling_heating'
    if data_input[((data_input.index.dayofyear<120)|(data_input.index.dayofyear>274))&(data_input.Temp_supply==data_input.Temp_supply_tank)].empty==False:
        data_input.loc[((data_input.index.dayofyear<120)|(data_input.index.dayofyear>274))&(data_input.Temp_supply==data_input.Temp_supply_tank),'Temp_supply_tank']+=1.5

    if combinations['house_type']=='SFH45': 
        data_input.loc[data_input.index.dayofyear==23,'Req_kWh']=data_input.loc[data_input.index.dayofyear==23,'Req_kWh']*.7#'transition_cooling_heating'
    if testing:
        data_input=data_input[data_input.index.week==week]
        nyears=1
        days=1
        ndays=1
        

    #configuration=[Batt,HP,TS,DHW]
    #if all false, only PV
    conf_aux=[False,True,False,False]#[Batt,HP,TS,DHW]

    
    if (conf!=0)&(conf!=1)&(conf!=4)&(conf!=5):#TS present in 2,3 and 6,7
        #print('inside TS')
        conf_aux[2]=True
        if (combinations['house_type']=='SFH15')|(combinations['house_type']=='SFH45'):
            tank_sh=pc.heat_storage_tank(mass=8000,surface=11)# For a 8128 liter tank with 1.15 m height and 3 m diameter 
            #tank_sh=pc.heat_storage_tank(mass=1500*3,surface=6*2)# For a 9600 liter tank with 3 m height and 2 m diameter 
            T_min_cooling=285.15#12°C
        else:
            tank_sh=pc.heat_storage_tank(mass=8000,surface=11)# For a 8128 liter tank with 1.15 m height and 3 m diameter 
            T_min_cooling=285.15#12°C
    else:#No TS
        tank_sh=pc.heat_storage_tank(mass=0, surface=0.41)# For a 50 liter tank with .26 m height and .25 diameter
        T_min_cooling=0

    if (conf==1)|(conf==3)|(conf==5)|(conf==7):#DHW present
        #print('inside DHW')
        conf_aux[3]=True
        tank_dhw=pc.heat_storage_tank(mass=200, t_max=60+273.15, t_min=40+273.15,surface=1.6564) # For a 200 liter tank with 0.95 m height and .555 diameter
        if (conf==1)|(conf==5):
            if combinations['house_type']=='SFH15':
                tank_sh=pc.heat_storage_tank(mass=100, surface=1.209)# For a 100 liter tank with  .52m height and .25 diameter
            elif combinations['house_type']=='SFH45':
                tank_sh=pc.heat_storage_tank(mass=100, surface=1.209)# For a 200 liter tank with .52 m height and .35 diameter
            elif combinations['house_type']=='SFH100':
                tank_sh=pc.heat_storage_tank(mass=0, surface=3.2)# For a 50 liter tank with .52 m height and .5 diameter
    else:#No DHW
        tank_dhw=pc.heat_storage_tank(mass=1, t_max=0, t_min=0,specific_heat_dhw=0,U_value_dhw=0,surface_dhw=0)#null

    ndays=days*nyears
    print(data_input.head())
    if combinations['HP']=='AS':
        if combinations['house_type']=='SFH15':
            Backup_heater=design_param['bu_15']+2
            hp=pc.HP_tech(technology='ASHP',power=design_param['hp_15'])
        elif combinations['house_type']=='SFH45':
            Backup_heater=design_param['bu_45']+4
            hp=pc.HP_tech(technology='ASHP',power=design_param['hp_45'])
        else:
            Backup_heater=design_param['bu_100']+4
            hp=pc.HP_tech(technology='ASHP',power=design_param['hp_100'])
    elif combinations['HP']=='GSHP':
        #TODO
        pass
    if testing:
        
        #tank_sh=pc.heat_storage_tank(mass=0, surface=1.6564)
        #tank_dhw=pc.heat_storage_tank(mass=0, t_max=60+273.15, t_min=40+273.15,surface=1.6564)
        #data_input.iloc[:,14:19]=100 #prices
        #data_input.iloc[10:16,14:19]=20 #prices
        hp.power=100
        print(data_input.head())
        
    param={'conf':conf_aux,
    'delta_t':dt,'nyears':nyears,'T_min_cooling':T_min_cooling,
    'days':days,'ndays':ndays,'hp':hp,'tank_dhw':tank_dhw,'tank_sh':tank_sh,
    'Backup_heater':Backup_heater,'ht':combinations['house_type'],
    'HP_type':combinations['HP'],'testing':testing, 'Cooling_ind':cooling}
    return data_input,param

def expand_grid(dct):
    rows = itertools.product(*dct.values())
    return pd.DataFrame.from_records(rows, columns=dct.keys())

def main():
    print('in')
    dct={'country':['CH'],'conf':[3],'house_type':['SFH100','SFH15','SFH45'],'HP':['AS']}
    Total_combs=expand_grid(dct)
    print(Total_combs)
    combinations=Total_combs.loc[0]
    print(combinations)
    data_input,param=load_param(combinations)
    df=Optimize(data_input,param)
    df.to_csv('out.csv')

if __name__ == '__main__':
    main()