import urllib.request , time ,  re
import pandas as pd
import numpy , xgboost ,os
from sklearn.model_selection import (StratifiedKFold,cross_val_score,cross_val_predict)  
from sklearn.metrics import (mean_squared_error,confusion_matrix)
import matplotlib.pyplot as plt
from matplotlib import dates
from matplotlib.ticker import FormatStrFormatter ,AutoMinorLocator ,MultipleLocator
import datetime as dt
import math
import requests
from mymetric import *



############################################
def par_fin(ticker):
    url="https://finance.yahoo.com/quote/"+ticker+"?p="+ticker

    f = open('info','w')
    #настраиваем прокси
    proxy =urllib.request.ProxyHandler( {'http':'http://www.someproxy.com:3128'} )
    opener = urllib.request.build_opener(proxy)
    opener.addheaders =[('User-agent', 'Mozilla/5.0')]

    try:
        response = opener.open(url)
    except:
        print('Сработало какое-то исключение, возможно сервер не отвечает')
        time.sleep(30)
        response = opener.open(url)
  #  urllib.request.install_opener(opener)
   # URL_obj = urllib.request.urlopen(url)

    txt=response.read()
    response.close()
    inform = str(txt)
    f.write(inform)


    l={}

    Main_price = re.search('b\)" data-reactid="14">(.*?)<', inform)
    if Main_price:
        tmp = Main_price.group(1)
        tmp = tmp.replace(",", "")
        l.update({"Main Price":float(tmp)})

    Close = re.search('s\) " data-reactid="15">(.*?)<', inform)
    if Close:
        tmp = Close.group(1)
        tmp = tmp.replace(",", "")
        l.update({"Prev Close":float(tmp)})

    Open = re.search('s\) " data-reactid="20">(.*?)<', inform)
    if Open:
        tmp = Open.group(1)
        tmp = tmp.replace(",", "")
        l.update({"Open":float(tmp)})

    Bid = re.search('s\) " data-reactid="25">(.*?)<',inform)
    if Bid:
        tmp=Bid.group(1)
        tmp = tmp.replace(",", "")
        l.update({"Bid":tmp})


    Ask = re.search('s\) " data-reactid="30">(.*?)<', inform)
    if Ask:
        tmp = Ask.group(1)
        tmp = tmp.replace(",", "")
        l.update({"Ask":tmp})


    Volume = re.search('s\) " data-reactid="48">(.*?)<', inform)
    if Volume:
        tmp = Volume.group(1)
        tmp = tmp.replace(",","")
        l.update({"Volume":int(tmp)})
    else:
        l.update({"err":'error'})
        return l

    return l

####################################################
def add_time(mass):
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    t=time.localtime()
    mass.update({"time":str(t.tm_mday)+"-"+str(t.tm_mon)+"-"+str(t.tm_year)+"  "+str(t.tm_hour)+":"+str(t.tm_min)+":"+str(t.tm_sec)})
    return mass
####################################################
def preprocess_mass(strings,t,init_point):
    Mass_DF={}

    for str1 in strings:
   #     Mass_DF[str1]=pd.read_csv('data/'+ str(t.tm_mday)+"-"+str(t.tm_mon)+"-"+str(t.tm_year)+'/' + str1 + '.csv')
        Mass_DF[str1] = pd.read_csv('data/full_data/'+str1+'.csv')
        Mass_DF[str1] = Mass_DF[str1].iloc[-init_point:]
        del Mass_DF[str1]['time.1'] 
        Mass_DF[str1].index = Mass_DF[str1]['time']
        del Mass_DF[str1]['time'] # убираем созданный в csv файле столбец с датой и временем
        Mass_DF[str1].index =Mass_DF[str1].index.to_datetime()

        Mass_DF[str1]["hour"] = Mass_DF[str1].index.hour
        Mass_DF[str1]["minute"] = Mass_DF[str1].index.minute
        Mass_DF[str1]["sec"] = Mass_DF[str1].index.second

    return Mass_DF
#######################################################
MKdir_gr = lambda t: os.system('mkdir -p graphics/'+ str(t.tm_mday)+"-"+str(t.tm_mon)+"-"+str(t.tm_year) )
#######################################################

def drowing_picture(str1,Y,y_pred,y_pred1,X,test_col,train_point_print,col_p,point_pred,t,PC,rolling_mean,check_drow):
    # делаем вид времени

    time_interval = pd.DataFrame({"hour": X[-col_p:, 0], "minute": X[-col_p:, 1], "sec": X[-col_p:, 2]})   
    time_interval['date'] = time_interval['hour'].astype('str') + ":" + time_interval['minute'].astype('str') + ":" + \
                            time_interval['sec'].astype('str')
    fmt = dates.DateFormatter("%H:%M:%S")
    time_interval1 = [dt.datetime.strptime(i, "%H:%M:%S") for i in time_interval['date']]

    # оцениваем качество предсказаний
    accuracy = my_mean_sqeared_error(Y[-(test_col):] , y_pred1[-(test_col):] )
    acc_str = "mean squared error: %.4f%%" % accuracy
   # print(acc_str)

    ma = my_average(Y[-(test_col):] , y_pred1[-(test_col):] )
    ma_str = "average error: %.3f%%" % ma 
 #   print(ma_str)

    mde,tuk = max_delta(Y[-(test_col):], y_pred1[-(test_col):] )
    mde_str = "max delta error: %.3f%%" % mde


    # рисуем
    if check_drow:
      fig = plt.figure(figsize=(12, 8))
      ax = fig.add_subplot(111)

      text1 = acc_str + '\n' + ma_str +'\n' +mde_str

      ax.text(0.02, 0.90, text1, bbox=dict(facecolor='white', alpha=0.7), transform=ax.transAxes, fontsize=12)

      ax.plot(time_interval1, y_pred, 'r-', label="predict", linewidth=2)
      ax.plot(time_interval1[:-point_pred], Y[-(test_col + train_point_print):], 'bo--', label="averaged sample", linewidth=1)
    #  ax.plot(time_interval1[:-point_pred], Y[-(test_col + train_point_print):], 'bo', label="test", linewidth=2)
      ax.plot(time_interval1[:-point_pred],rolling_mean[-(test_col + train_point_print):])

      plt.axvline(x=time_interval1[train_point_print - 1], color='k', linestyle='--', label='bound_train', linewidth=2)
      plt.axvline(x=time_interval1[test_col + train_point_print - 1], color='g', linestyle='--', label='bound_test',
                linewidth=2)

  #  plt.axhline(y=0, color='m', linestyle='--', label='zero', linewidth=2)

      def price(x):
        return "%"+"%.5f" % x

      ax.set_ylabel('procent of diff price')
      ax.set_xlabel('time (h:m:s)')

      ax.format_ydata = price
      ax.xaxis.set_major_formatter(fmt)

      majorFormatter = FormatStrFormatter('%.3f%%')
      ax.yaxis.set_major_formatter(majorFormatter)

      minorLocator = AutoMinorLocator(n=2)
      ax.xaxis.set_minor_locator(minorLocator)
      ax.xaxis.set_minor_formatter(fmt)

      ax.set_title('стоимость акций ' + str1)

      for label in ax.xaxis.get_ticklabels(minor=True):
        label.set_rotation(30)
        label.set_fontsize(10)

      for label in ax.xaxis.get_ticklabels():
        label.set_rotation(30)
        label.set_fontsize(10)

      ax.legend(loc='upper right')
    # рисуем сетку
      ax.grid(True, which='major', color='grey', linestyle='dashed')
      ax.grid(True, which='minor', color='grey', linestyle='dashed')

    #  fig.autofmt_xdate()
   # plt.show()

      MKdir_gr(t)
      fig.savefig('graphics/'+ str(t.tm_mday)+"-"+str(t.tm_mon)+"-"+str(t.tm_year)+'/цена акции компании '+str1+ '.pdf',format = 'pdf',dpi=1000)


      fig.clf()

    #все эти свободные числа нужно вывести как управляющие параметры
    last_price = my_single_average(y_pred[-4:]) #y_pred[-3:-2] #

    av_Y = my_single_average(Y[-(test_col):])

    #считаем Гауссову вероятность
    if abs(ma) > abs(av_Y):
       P = Gauss_probability(0.1,abs(ma),accuracy,mde)
    else:
       P = Gauss_probability(abs(1-abs(ma/av_Y)),abs(ma),accuracy,mde)

    #выводим на экран данные
    print(str1 +": procent %.3f%% of price in %d:%d:%d, probability: %.3f%% " % (last_price,time_interval[-3:-2]['hour'],time_interval[-3:-2]['minute'],time_interval[-3:-2]['sec'], P * 100) )


#######################################################
def boosting_solver(Mass_df,str1,delta_t,t,param_points,param_model,n,m,check_drow,cross_working):

  #  Mass_df[str1]['diff_price'] = Mass_df[str1]['Main Price'].diff() # изменение цены
    Mass_df[str1]['procent_diff'] = ( Mass_df[str1]['Main Price'] - Mass_df[str1]['Prev Close'] ) / Mass_df[str1]['Prev Close'] *100

    PC = Mass_df[str1]['Prev Close'][1]
   
   # print(Mass_df[str1].columns)

    X = Mass_df[str1][['hour','minute','sec']][n-1:].values #преобразовали тип dataFrame в тип array Numpy

    # скользящая средняя
    rolling_mean = Mass_df[str1]['procent_diff'].rolling(window=n).mean()
    Y = rolling_mean[n-1:].values

    test_col= param_points['test_col']
    point_pred = param_points['point_pred']
    train_point_print = param_points['train_point_print']

    col_p = point_pred + test_col + train_point_print

    #разделяем X и Y на обучающий и тестовый набор данных
    X_train = X[:-test_col]
    y_train = Y[:-test_col]
   

    model = xgboost.XGBRegressor(max_depth=param_model['max_depth'],
                                 learning_rate=param_model['learning_rate'],
                                 n_estimators=param_model['n_estimators'],
                                  subsample=param_model['subsample'])

  #  print(X_train,y_train)
    
    result_score = cross_val_score(model,X,Y,cv=6)
   # print(result_score)

    # обучаем модель
    model.fit(X_train,y_train)#,eval_metric='rmse')
    model.score(X,Y)

   # print(model) #параметры модели

    # dobavluem predskaz (pervoe slagaemoe 'to colichestvo cdelok ,vtoroe -vrema v sekundax)
    for i in range(point_pred):
        sum_sek = X[X.shape[0] - 1][2] + 60 * X[X.shape[0] - 1][1] + 3600*X[X.shape[0] - 1][0] + delta_t
        X = numpy.vstack([X, [  sum_sek//3600,(sum_sek%3600)//60, (sum_sek%3600)%60  ] ])

    # делаем прогноз
    y_pred = model.predict(X[-(col_p+m-1):])

    # применим кросс валидацию
    if cross_working != 0:
        y_pred = cross_val_predict(model,X[-(col_p+m-1):],y_pred,cv=cross_working)

    # усредняем прогноз
    pred_df = pd.DataFrame(data = y_pred,columns = ['pd'])
    rolling_mean_pred_df = pred_df.rolling(window=m).mean()
    y_pred = rolling_mean_pred_df['pd'][m-1:].values

    #функция рисования
    drowing_picture(str1, Y, y_pred, y_pred[:-point_pred], X, test_col, train_point_print, col_p, point_pred,t,PC,rolling_mean,check_drow)


    DF_print = pd.DataFrame({"price_pred": list(y_pred[-point_pred:]), "time_sec": list(X[-point_pred:, 1])})

    return DF_print

############################################################################
def fourier_transform(Mass_df,str,delta_t):
    del Mass_df[str]['Unnamed: 0']
    Mass_df[str]['diff_price'] = Mass_df[str]['Main Price'].diff(1) # изменение цены
  #  print(Mass_df[str][['diff_price','Main Price']])

  #  print(Mass_df[str].columns)

    dataset = Mass_df[str].values #преобразовали тип dataFrame в тип array Numpy
    X = dataset[1:,6:9]

    #рассматриваем увеличение или уменьшение цены!!
    Y = dataset[1:,9]

    #на скольки точках тестим
    test_col=5

    # на сколько точек предсказываем
    point_pred = 4

    # сколько обученных точек показываем
    train_point_print = 7

    col_p = point_pred + test_col + train_point_print

    # частота Найквиста равна половине частоты дискретизацииtxyач
    # период дискретизации (обратная величина частоте)
    FD =23050

    n = Y.shape[0]

    spectr = numpy.fft.rfft(Y)

    plt.plot(numpy.fft.rfftfreq(n,1./float(FD)),numpy.abs(spectr)/n)

    plt.grid(True)
    plt.xlabel('Частота, Гц')
    plt.ylabel('Амплитуда')
    plt.show()

    return 0
