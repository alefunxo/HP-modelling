#Series

 # -*- coding: utf-8 -*-
## @namespace LP
# Created on Wed Nov  1 15:44:25 2017
# Author
# Alejandro Pena-Bello
# alejandro.penabello@unige.ch
# In this script the HP optimization is set up.
# This LP algorithm allows the user to minimize the daily electricity bill tied to the HP
# According to the Data it can be expanded to one month or n years optimization
# The delta_t allows the user to set the time step delta_t=fraction of hour, e.g.
# delta_t=0.25 is a 15 min time step


import pyomo.environ as en

#Model
def Concrete_model(Data):
    
    m = en.ConcreteModel()
    #Sets
    m.Time=en.Set(initialize=Data['Set_declare'][1:],ordered=True)
    m.Time_1=en.Set(initialize=Data['Set_declare'][1:9],ordered=True)
    m.Time_2=en.Set(initialize=Data['Set_declare'][9:17],ordered=True)
    m.Time_3=en.Set(initialize=Data['Set_declare'][17:25],ordered=True)
    m.Time_4=en.Set(initialize=Data['Set_declare'][25:33],ordered=True)
    m.Time_5=en.Set(initialize=Data['Set_declare'][33:41],ordered=True)
    m.Time_6=en.Set(initialize=Data['Set_declare'][41:49],ordered=True)
    m.Time_7=en.Set(initialize=Data['Set_declare'][49:57],ordered=True)
    m.Time_8=en.Set(initialize=Data['Set_declare'][57:65],ordered=True)
    m.Time_9=en.Set(initialize=Data['Set_declare'][65:73],ordered=True)
    m.Time_10=en.Set(initialize=Data['Set_declare'][73:81],ordered=True)
    m.Time_11=en.Set(initialize=Data['Set_declare'][81:89],ordered=True)
    m.Time_12=en.Set(initialize=Data['Set_declare'][89:],ordered=True)

    
    m.tm=en.Set(initialize=Data['Set_declare'],ordered=True)
    #Electric Parameters
    m.dt=en.Param(initialize=Data['delta_t'])
    m.doy=en.Param(initialize=Data['dayofyear'])
    m.toy=en.Param(initialize=Data['toy'])
    
    m.heating=en.Param(initialize=Data['conf'][1])
    m.T_storage=en.Param(initialize=Data['conf'][2])
    m.DHW=en.Param(initialize=Data['conf'][3])
    m.subset_tank_day=en.Param(initialize=Data['subset_tank_day'])
    m.retail_price=en.Param(m.Time,initialize=Data['retail_price'])
    
    #Heating parameters
    m.HP_power_SH=en.Param(m.Time,initialize=Data['hp_sh_cons'])#kWh/h=kW
    m.HP_power_tank=en.Param(m.Time,initialize=Data['hp_tank_cons'])#kWh/h=kW
    m.HP_dhw_power=en.Param(m.Time,initialize=Data['hp_dhw_cons'])#kWh/h=kW
    
    m.T_supply=en.Param(m.Time,initialize=Data['Temp_supply'])
    
    m.Set_T=en.Param(m.Time,initialize=Data['Set_T'])
    m.COP_SH=en.Param(m.Time,initialize=Data['COP_SH'])
    m.COP_DHW=en.Param(m.Time,initialize=Data['COP_DHW'])
    m.COP_tank=en.Param(m.Time,initialize=Data['COP_tank'])
    m.Req_kWh=en.Param(m.Time,initialize=Data['Req_kWh'])# In kWh!
    m.Req_kWh_DHW=en.Param(m.Time,initialize=Data['Req_kWh_DHW'])# In kWh!
    m.T_max=en.Param(m.Time,initialize=Data['T_aux_supply'])# In K

    m.T_min=en.Param(m.Time,initialize=Data['Temp_supply'])# In K
    m.T_max_dhw=en.Param(initialize=Data['tank_dhw'].t_max)# In K
    m.T_min_dhw=en.Param(initialize=Data['tank_dhw'].t_min)# In K

    m.T_init=en.Param(initialize=Data['T_init'])# In K

    m.A=en.Param(initialize=Data['tank_sh'].surface)#m2
    m.U=en.Param(initialize=Data['tank_sh'].U_value)#kW/(m2*K)!!!
    m.c_p=en.Param(initialize=Data['tank_sh'].specific_heat)#kWh/(K*l)
    m.m=en.Param(initialize=Data['tank_sh'].mass)#liters

    m.A_dhw=en.Param(initialize=Data['tank_dhw'].surface)#m2
    m.U_dhw=en.Param(initialize=Data['tank_dhw'].U_value)#kW/(m2*K)!!!
    m.c_p_dhw=en.Param(initialize=Data['tank_dhw'].specific_heat)#kWh/(K*l)
    m.m_dhw=en.Param(initialize=Data['tank_dhw'].mass)#liters
    m.Backup_heater=en.Param(initialize=Data['Backup_heater'])

    
    #Variables
    m.E_cons=en.Var(m.Time,bounds=(0,None),initialize=0)
    
    #HP variables
    m.E_hp=en.Var(m.Time,bounds=(0,None),initialize=0)
     
    #TS
    m.Q_ts_sh=en.Var(m.Time,bounds=(0,None),initialize=0)
    m.Q_hp_sh=en.Var(m.Time,bounds=(0,None),initialize=0)
    m.Q_hp_ts=en.Var(m.Time,bounds=(0,None),initialize=0)
    m.T_ts=en.Var(m.tm,bounds=(0,None),initialize=m.T_init)#Temperature storage
    m.Q_ts=en.Var(m.Time,bounds=(0,None),initialize=0)
    m.Q_ts_delta=en.Var(m.Time,bounds=(None,None),initialize=0)
    m.Q_loss_ts=en.Var(m.Time,bounds=(None,None),initialize=0)
    
    #hpdhwvariables
    m.E_hpdhw=en.Var(m.Time,bounds=(0,None),initialize=0)
    m.Bool_hp=en.Var(m.Time,within=en.Boolean,initialize=1)
    m.Bool_hpdhw=en.Var(m.Time,within=en.Boolean,initialize=0)

    #DHW
    m.Q_dhwst_hd=en.Var(m.Time,bounds=(0,None),initialize=0)
    m.T_dhwst=en.Var(m.tm,bounds=(m.T_min_dhw,m.T_max_dhw),initialize=40+273.15)#Temperature storage
    m.Q_loss_dhwst=en.Var(m.Time,bounds=(0,None),initialize=0)

    #Backup_heater
    m.E_bu=en.Var(m.Time,bounds=(0,m.Backup_heater*m.dt),initialize=0)
    m.E_budhw=en.Var(m.Time,bounds=(0,m.Backup_heater*m.dt),initialize=0)

    m.total_cost = en.Objective(rule=Obj_fcn,sense=en.minimize)

    #Constraints

    #HP Constraints
    
    m.Balance_space_heat_demand_r_1=en.Constraint(m.Time_1,rule=Balance_space_heat_demand_1)
    m.Balance_space_heat_demand_r_2=en.Constraint(m.Time_2,rule=Balance_space_heat_demand_2)
    m.Balance_space_heat_demand_r_3=en.Constraint(m.Time_3,rule=Balance_space_heat_demand_3)
    m.Balance_space_heat_demand_r_4=en.Constraint(m.Time_4,rule=Balance_space_heat_demand_4)
    m.Balance_space_heat_demand_r_5=en.Constraint(m.Time_5,rule=Balance_space_heat_demand_5)
    m.Balance_space_heat_demand_r_6=en.Constraint(m.Time_6,rule=Balance_space_heat_demand_6)
    m.Balance_space_heat_demand_r_7=en.Constraint(m.Time_7,rule=Balance_space_heat_demand_7)
    m.Balance_space_heat_demand_r_8=en.Constraint(m.Time_8,rule=Balance_space_heat_demand_8)
    m.Balance_space_heat_demand_r_9=en.Constraint(m.Time_9,rule=Balance_space_heat_demand_9)
    m.Balance_space_heat_demand_r_10=en.Constraint(m.Time_10,rule=Balance_space_heat_demand_10)
    m.Balance_space_heat_demand_r_11=en.Constraint(m.Time_11,rule=Balance_space_heat_demand_11)
    m.Balance_space_heat_demand_r_12=en.Constraint(m.Time_12,rule=Balance_space_heat_demand_12)
    
    
    m.Change_tank_thermal_energy_rule_r=en.Constraint(m.Time,rule=Change_tank_thermal_energy_rule)
    m.Available_tank_thermal_energy_rule_r=en.Constraint(m.Time,rule=Available_tank_thermal_energy_rule)
    m.Balance_hp_supply_r=en.Constraint(m.Time,rule=Balance_hp_supply_rule)#*
    m.Balance_hp_power_r=en.Constraint(m.Time,rule=Balance_hp_power)
    m.Balance_hp_dhw_power_r=en.Constraint(m.Time,rule=Balance_hp_dhw_power)
    m.Ts_losses_r=en.Constraint(m.Time,rule=Ts_losses)
    m.Balance_ts_r=en.Constraint(m.Time,rule=Balance_ts)#Verify if is necessary
    m.def_ts_state_r=en.Constraint(m.tm,rule=def_ts_state_rule)
    m.def_ts_state2_r=en.Constraint(m.Time,rule=def_ts_state2_rule)
    #hpdhw Constraints
    m.Balance_DHW_demand_r=en.Constraint(m.Time,rule=Balance_DHW_demand)
    m.Balance_hp_supply_r2=en.Constraint(m.Time,rule=Balance_hp_supply_rule2)#
    m.DHWST_losses_r=en.Constraint(m.Time,rule=DHWST_losses)
    m.Balance_dhwst_r=en.Constraint(m.tm,rule=Balance_dhwst)#Verify if is necessary
    m.def_dhwst_state_r=en.Constraint(m.tm,rule=def_dhwst_state_rule)

    m.hp_ch1=en.Constraint(m.Time,rule=Bool_hp_rule_1)
    m.hp_ch2=en.Constraint(m.Time,rule=Bool_hp_rule_2)
    m.hp_cd3=en.Constraint(m.Time,rule=Bool_hp_rule_3)
    m.hp_cd4=en.Constraint(m.Time,rule=Bool_hp_rule_4)
    m.HP_1_2_r=en.Constraint(m.Time,rule=HP_1_2)
    #Balance
    m.Grid_cons=en.Constraint(m.Time,rule=Grid_cons_rule)
    return m


#Instance
#Energy

def Balance_space_heat_demand_1(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_1)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_1)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_1)==0)#Balance

def Balance_space_heat_demand_2(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:

                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_2)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_2)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_2)==0)#Balance

def Balance_space_heat_demand_3(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_3)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_3)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_3)==0)#Balance

def Balance_space_heat_demand_4(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_4)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_4)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_4)==0)#Balance

def Balance_space_heat_demand_5(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_5)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_5)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_5)==0)#Balance

def Balance_space_heat_demand_6(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_6)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_6)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_6)==0)#Balance

def Balance_space_heat_demand_7(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_7)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_7)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_7)==0)#Balance

def Balance_space_heat_demand_8(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_8)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_8)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_8)==0)#Balance

def Balance_space_heat_demand_9(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_9)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_9)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_9)==0)#Balance

def Balance_space_heat_demand_10(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_10)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_10)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_10)==0)#Balance

def Balance_space_heat_demand_11(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_11)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_11)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_11)==0)#Balance

def Balance_space_heat_demand_12(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    TODO
    -------
    Verify without storage with cooling. I think we need return(-m.Q_ts_sh[i],m.Req_kWh[i])
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (sum(m.Q_ts_sh[i]+m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_12)==0)#Balance
            else:
                return (sum(m.Q_hp_sh[i]-m.Req_kWh[i] for i in m.Time_12)==0)#Balance
        else:
            return (sum(m.Q_ts_sh[i]-m.Req_kWh[i] for i in m.Time_12)==0)#Balance
            
def Change_tank_thermal_energy_rule(m,i):
    '''
    Description
    -------
    Change in tank thermal energy (Q_ts_delta [kWh]) is given by the change in tank temperature times the mass times the specific heat of water.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                if m.toy==1:
                    #return en.Constraint.Skip
                    return((m.T_ts[i] ),(m.T_min[i]))
                elif m.toy==3:
                    return((m.T_ts[i] ),(m.T_min[i]))
                elif m.toy==2:
                    return((m.T_ts[i] ),(m.T_min[i]))
                else:
                    return(m.Q_ts_delta[i],((m.T_ts[i]-m.T_ts[i-1])*m.m*m.c_p))
            else:
                return en.Constraint.Skip
        else:
            if m.toy==1:
                #return en.Constraint.Skip
                return((m.T_ts[i] ),(m.T_min[i]))
            elif m.toy==3:
                return((m.T_ts[i] ),(m.T_min[i]))
            elif m.toy==2:
                return((m.T_ts[i] ),(m.T_min[i]))
            else:
                return(m.Q_ts_delta[i],((m.T_ts[i]-m.T_ts[i-1])*m.m*m.c_p))

def Available_tank_thermal_energy_rule(m,i):
    '''
    Description
    -------
    Thermal energy available in the tank (Q_ts [kWh]) is given by the temperature of the tank at time t (T_ts) and the minimum temperature accepted in the tank (T_min) times the mass times the specific heat of water. If cooling T_min is 293.15 K (20°C).
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                if (m.doy>=120)and(m.doy<=274):#days of year where there is heating
                    return(m.Q_ts[i],(0)*m.m*m.c_p)
                else:
                    return(m.Q_ts[i],((m.T_ts[i]-m.T_supply[i])*m.m*m.c_p))
            else:
                return en.Constraint.Skip
        else:
            if (m.doy>=120)and(m.doy<=274):#days of year where there is heating
                return(m.Q_ts[i],(0)*m.m*m.c_p)
            else:
                return(m.Q_ts[i],((m.T_ts[i]-m.T_supply[i])*m.m*m.c_p))

def Balance_hp_supply_rule(m,i):
    '''
    Description
    -------
    Balance of thermal energy supplied by the HP and the backup heater according to the COP. If there is no storage the electricity consumed by the HP times the COP plus the electricity consumed by the backup heater times the COP of the backup heater (i.e. 1) must be equal to the heat provided for space heating (or cooling).
    If there is storage, the electricity supplied times COP must be equal to the delta Q supplied to the tank plus the heat provided for space heating (cooling) plus the losses of the tank. It can be assimiled as Q_char. For cooling signs and COP change.
    TODO
    -------
    Change COP_SH for cooling by COP for cooling (parameter).
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return ((m.E_hp[i]*m.COP_tank[i]+m.E_bu[i]),m.Q_hp_ts[i]+m.Q_hp_sh[i])
            else:
                return((m.E_hp[i]*m.COP_SH[i]+m.E_bu[i]),(m.Q_hp_sh[i]))

        else:
            return ((m.E_hp[i]*m.COP_tank[i]+m.E_bu[i]),m.Q_hp_ts[i])

def Balance_ts(m,i):
    '''
    Description
    -------
    Calcultes tank balance over the day.
    TODO
    -------
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return ((m.Q_hp_ts[i]),m.Q_ts_delta[i]+m.Q_ts_sh[i]+m.Q_loss_ts[i])#Balance
            else:
                return (m.Q_hp_ts[i],0)
        else:

            return ((m.Q_hp_ts[i]),m.Q_ts_delta[i]+m.Q_ts_sh[i]+m.Q_loss_ts[i])#Balance
def Balance_hp_power(m,i):
    '''
    Description
    -------
    Balance of thermal energy supplied by the HP and the backup heater according to the COP. If there is no storage the electricity consumed by the HP times the COP plus the electricity consumed by the backup heater times the COP of the backup heater (i.e. 1) must be equal to the heat provided for space heating (or cooling).
    If there is storage, the electricity supplied times COP must be equal to the delta Q supplied to the tank plus the heat provided for space heating (cooling) plus the losses of the tank. It can be assimiled as Q_char. For cooling signs and COP change.
    TODO
    -------
    Change COP_SH for cooling by COP for cooling (parameter).
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return((m.E_hp[i])<=m.HP_power_tank[i]*m.dt)
            else:
                return((m.E_hp[i])<=m.HP_power_SH[i]*m.dt)
        else:
            return((m.E_hp[i])<=m.HP_power_tank[i]*m.dt)

def Balance_hp_dhw_power(m,i):
    '''
    Description
    -------
    Balance of thermal energy supplied by the HP and the backup heater according to the COP. If there is no storage the electricity consumed by the HP times the COP plus the electricity consumed by the backup heater times the COP of the backup heater (i.e. 1) must be equal to the heat provided for space heating (or cooling).
    If there is storage, the electricity supplied times COP must be equal to the delta Q supplied to the tank plus the heat provided for space heating (cooling) plus the losses of the tank. It can be assimiled as Q_char. For cooling signs and COP change.
    TODO
    -------
    Change COP_SH for cooling by COP for cooling (parameter).
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        return((m.E_hpdhw[i])<=m.HP_dhw_power[i]*m.dt)

#TS Constraints
def Ts_losses(m,i):
    '''
    Description
    -------
    Calcultes tank losses as a function of the temperature difference between the tank and the room temperature (Set_T) times the U_value, the tank surface and delta t (since losses are per hour).
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            return(m.Q_loss_ts[i],0)
        else:
            if i==0:
                return(m.Q_loss_ts[i],0)
            else:
                return(m.Q_loss_ts[i],m.dt*m.U*m.A*(m.T_ts[i]-(m.Set_T[i])))



def def_ts_state_rule(m, t):
    '''
    Description
    -------
    Temperature of the tank must be lower than T_min (??) when cooling
    TODO
    -------
    Verify if needed and adjust nomenclature
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                if t==-1:
                    return(m.T_ts[t],m.T_init)# This is what is super important
                else:
                    return en.Constraint.Skip
            else:
                return en.Constraint.Skip
        else:
            if t==-1:
                return(m.T_ts[t],m.T_init)# This is what is super important
            else:
                return en.Constraint.Skip
def def_ts_state2_rule(m, i):
    '''
    Description
    -------
    Temperature of the tank must be lower than T_min (??) when cooling
    TODO
    -------
    Verify if needed and adjust nomenclature
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.DHW:
                return (m.T_ts[i]<=m.T_max[i])
            else:
                return en.Constraint.Skip
        else:
            return (m.T_ts[i]<=m.T_max[i])



#DHW Constraints

def Balance_DHW_demand(m,i):
    '''
    Description
    -------
    Balance demand DHWST (storage tank for DHW) in thermal terms (DHWST supply = Heat demand for DHW). Skip if not DHW.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.DHW==False:
            return en.Constraint.Skip
        else:
            return(m.Q_dhwst_hd[i],m.Req_kWh_DHW[i])#In kWh

def Balance_hp_supply_rule2(m,i):
    '''
    Description
    -------
    Balance supply DHWST (storage tank for DHW) in thermal terms (HP supply (backup heater included) = heat supplied to the DHWST). Skip if not DHW.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.DHW==False:
            return en.Constraint.Skip
        else:
            return ((m.E_hpdhw[i])*m.COP_DHW[i]+m.E_budhw[i],((m.T_dhwst[i]-m.T_dhwst[i-1])*m.m_dhw*m.c_p_dhw)+m.Q_dhwst_hd[i]+m.Q_loss_dhwst[i])#Q_char

#DHWST Constraints
def DHWST_losses(m,i):
    '''
    Description
    -------
    Calcultes DHW storage tank losses as a function of the temperature difference between the tank and the room temperature (Set_T) times the U_value, the tank surface and delta t (since losses are per hour).
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.DHW==False:
            return en.Constraint.Skip
        else:
            if i==0:
                return(m.Q_loss_dhwst[i],0)
            else:
                return(m.Q_loss_dhwst[i],m.dt*m.U_dhw*m.A_dhw*(m.T_dhwst[i]-(m.Set_T[i])))

def Balance_dhwst(m,t):
    '''
    Description
    -------
    Calcultes DHW storage tank balance over the day.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.DHW==False:
            return en.Constraint.Skip
        else:
            if t==-1:
                return en.Constraint.Skip
            else:
                return (sum(m.E_hpdhw[t]*m.COP_DHW[t]+m.E_budhw[t]for t in m.Time)
                -sum(((m.T_dhwst[t]-m.T_dhwst[t-1])*m.m_dhw*m.c_p_dhw)+m.Q_dhwst_hd[t]+m.Q_loss_dhwst[t] for t in m.Time)==False)#Balance


def def_dhwst_state_rule(m, t):
    '''
    Description
    -------
    Defines initial temperature of DHW storage tank.
    TODO
    -------
    Verify if useful, probably not. Maybe an easier way is possible.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.DHW==False:
            return en.Constraint.Skip
        else:
            if t==-1:
                return(m.T_dhwst[t],m.T_min_dhw)
            else:
                return en.Constraint.Skip
############################################################

def Bool_hp_rule_1(m,i):
    '''
    Description
    -------
    If DHW two HPs are used, one for heating/cooling and one for DHW. However, both cannot operate at the same time (in real world only one HP is used). BigM method to solve linear programming models using simplex algorithm. 1/4
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        bigM=500000

        return((m.E_hp[i]+m.E_bu[i])>=-bigM*(m.Bool_hp[i]))

def Bool_hp_rule_2(m,i):
    '''
    Description
    -------
    If DHW two HPs are used, one for heating/cooling and one for DHW. However, both cannot operate at the same time (in real world only one HP is used). BigM method to solve linear programming models using simplex algorithm.2/4
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        bigM=500000

        return((m.E_hp[i]+m.E_bu[i])<=bigM*(1-m.Bool_hpdhw[i]))

def Bool_hp_rule_3(m,i):
    '''
    Description
    -------
    If DHW two HPs are used, one for heating/cooling and one for DHW. However, both cannot operate at the same time (in real world only one HP is used). BigM method to solve linear programming models using simplex algorithm.3/4
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        bigM=500000
        return((m.E_hpdhw[i]+m.E_budhw[i])>=-bigM*(m.Bool_hpdhw[i]))

def Bool_hp_rule_4(m,i):
    '''
    Description
    -------
    If DHW two HPs are used, one for heating/cooling and one for DHW. However, both cannot operate at the same time (in real world only one HP is used). BigM method to solve linear programming models using simplex algorithm.4/4
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        bigM=500000
        return((m.E_hpdhw[i]+m.E_budhw[i])<=bigM*(1-m.Bool_hp[i]))

def HP_1_2(m,i):
    '''
    Description
    -------
    If DHW two HPs are used, one for heating/cooling and one for DHW. However, both cannot operate at the same time (in real world only one HP is used). BigM method to solve linear programming models using simplex algorithm. Restriction to operate only one at time.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        return (m.Bool_hp[i]+m.Bool_hpdhw[i],1)

###########################################################################

def Grid_cons_rule(m,i):
    '''
    Description
    -------
    Balance of grid consumption, includes the electricity consumed by the battery, the loads, HP1, hpdhw, BU, budhw and losses in the inverter (when charging the battery from the grid).
    TODO
    -------
    To include if elses to reduce the variables used?
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.DHW==False:
            return(m.E_cons[i],m.E_hp[i]+m.E_bu[i])
        else:
            return(m.E_cons[i],m.E_hp[i]+m.E_hpdhw[i]+m.E_bu[i]+m.E_budhw[i])

#Objective

def Obj_fcn(m):
    '''
    Description
    -------
    The bill is calculated in two parts, the energy related part is the retail price times the energy consumed from the grid minus the export price times the PV injection. If there is demand peak shaving (a capacity tariff is applied) the maximum power taken from the grid (in kW) is multiplied by the DAILY capacity tariff ($/kW per day).
    '''
    return(sum((m.retail_price[i]*m.E_cons[i]) for i in m.Time))
