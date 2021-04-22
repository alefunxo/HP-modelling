# HP-modelling
Daily bill minimization of a heat pump with the possibilities of:
1. Use only space heating
2. Use space heating and DHW
3. Use a thermal storage for space heating

DHW is provided on-demand, whereas space heating is provided in 2-hr blocks

The script includes input data for three types of single family houses with annual demand of 15, 45 and 100 kWh/m2 p.a. 
To select a configuration system, the parameter "conf" should be selected as follows:
1. HP for space heating only
2. HP for space heating and DHW
3. HP and Thermal storage for space heating only
4. HP for space heating and DHW and thermal storage for space heating only

The parameter "house_type" allows the user to select among the three types of houses.

This parameters can be changed in the line 399 of Core_LP.py script:

dct={'country':['CH'],'conf':[3],'house_type':['SFH100','SFH15','SFH45'],'HP':['AS']}
