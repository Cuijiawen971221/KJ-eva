import numpy as np

def calc_f(td,p,e):
# this code copy from VAISALA calculator
    td = td - 273.15
    if td>=0:
        a0 = 3.536e-4
        a1 = 2.933e-5
        a2 = 2.616e-7
        a3 = 8.581e-9
        a = [a0,a1,a2,a3]
        b0 = -1.0759e1
        b1 = 6.326e-2
        b2 = -2.536e-4
        b3 = 6.3405e-7
        b = [b0,b1,b2,b3]
    elif td >=-50 and td< 0:
        a = [ 3.621e-4,  2.606e-5, 3.8667e-7, 3.8268e-9]
        b = [ -1.076e1,  6.398e-2,-2.6355e-4, 1.6725e-6]
    else:
        a = [ 3.644e-4,  2.936e-5, 4.8874e-7, 4.3670e-9]
        b = [-1.0727e1,7.62115e-2, -1.749e-4,  2.466e-6]

    f = np.exp(np.sum([a[i]*td**i for i in range(4)]) * (1-e/p)+np.exp(np.sum([b[i]*td**i for i in range(4)]))*(p/e-1))

    return f

def calc_q(t,td,p,flag):
# this code copy from VAISALA calculator
# input:
#   t   : temperature in unit K
#   td  : temperature in unit K
#   p   : pressure in Pa
#   flag: The flag decides whether to use td as tdew or depending on td's value.
#         True = td is tdew
#         False = td is depend on itself

    if t<0 or td<0: return -999
#   depend on td's value

    if td>=273.15 or flag: #water
        a0,a1,a2,a3,a4,a5,a6 = 1,-6.0969e3,2.124e1,-2.7111e-2,1.6739e-5,2.4335,1
    else: #ice
        a0,a1,a2,a3,a4,a5,a6 = 1,-6.0245e3,2.933e1,1.06138e-2,-1.31988e-5,-4.938e-1,1

    e = a0*np.exp(a1/td + a2 + a3*td + a4*td**2 + a5*np.log(a6*td))
    e = e*calc_f(td,p,e)/100
    q = 622000*e/(p/100-0.378*e)

    return q

def hum(t,td,p,flag):
#   t   : temperature in unit K
#   td  : temperature in unit K
#   p   : pressure in Pa
    if t==-999 or td==-999 :
        return -999
    E = calc_q(t,t,p,True)
    e = calc_q(t,td,p,flag)
    return e/E*100



if __name__ == "__main__":
#    case 1 
    t = 273.15-40
    td = 273.15-60
    p = 1013e2
    print("flag:{:b} temperature: {:f} dew temperature: {:f} pressure: {:f} hum: {:f}".format(True,t,td,p,hum(t,td,p,True)))
    print("flag:{:b} temperature: {:f} dew temperature: {:f} pressure: {:f} hum: {:f}".format(False,t,td,p,hum(t,td,p,False)))
#    case 2
    t = 273.15+20
    td = 273.15+10
    p = 500e2
    print("flag:{:b} temperature: {:f} dew temperature: {:f} pressure: {:f} hum: {:f}".format(True,t,td,p,hum(t,td,p,True)))
    print("flag:{:b} temperature: {:f} dew temperature: {:f} pressure: {:f} hum: {:f}".format(False,t,td,p,hum(t,td,p,False)))
