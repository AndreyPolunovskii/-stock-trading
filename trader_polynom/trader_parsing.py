import pandas as pd
import os
from parsing_module import (par_fin,time,add_time)
import calendar

import warnings
pd.options.mode.chained_assignment = None # отключаем ненужные исключения
warnings.simplefilter(action='ignore',category = FutureWarning)



os.environ['TZ']='America/New_York'
time.tzset()
t =time.localtime()
clear = lambda: os.system('clear')
MKdir_data = lambda t: os.system('mkdir -p data/'+ str(t.tm_mday)+"-"+str(t.tm_mon)+"-"+str(t.tm_year) )

#tickers = ['TWTR','FB','GOOG','IQ','AMZN','TSLA','NVDA','AAPL']
tickers=['IQ','AAPL','GOOG']#,'FB']#,'AMZN','FB','TWTR']
#много времени занимает обработка нескольких компаний

# для каждой компании по прокси своему
proxies_list = open('list_proxies.txt').read().split('\n')
dict_proxies = {}
l1 = 0

for tick in tickers:
   if (l1 > (len(proxies_list) - 5) ):
       dict_proxies.update({tick : proxies_list[0]})
   else:
       dict_proxies.update({tick : proxies_list[l1]})
   l1 = l1 + 1


freq = 5*60 #(секунды) запрашиваем данные каждую минуту


str_delta_t = "1min"

#c сайта интервал запроса
if freq == 60:
   str_delta_t = "1min"

if freq == 5*60:
   str_delta_t = "5min"


#сколько точек показывать
print_point = 6

df = pd.DataFrame(columns=['Main Price'])
df.index.names=['time']
print_df=pd.DataFrame() 
Mass_df={}


for i in range(len(tickers)):
    Mass_df.update({tickers[i]:pd.DataFrame(df)})


i1=0
company=""


###################
fvar=open('VAR.txt','w')
fvar.write(str(freq))
fvar.close()
###################


##################
#если уже были созданы таблицы с данными
for str1 in tickers:
   path = 'data/full_data/'+str1+'.csv'
   if os.path.exists(path):
       Mass_df[str1] = pd.read_csv(path) #.dropna() - удаляет несуществующие значения None
       Mass_df[str1].index = Mass_df[str1]['time']
       del Mass_df[str1]['time']

##################


while(1):

    t = time.localtime()
    week_day = calendar.weekday(t.tm_year,t.tm_mon,t.tm_mday) + 1
    if (t.tm_hour < 9 or (t.tm_hour == 9  and t.tm_min < 30 ) or t.tm_hour >= 16 or week_day == 6 or week_day == 7):
        clear()
        print('ожидаем начало торгов, время = '+str(t.tm_mday)+"-"+str(t.tm_mon)+"-"+str(t.tm_year)+"  "+str(t.tm_hour)+":"+str(t.tm_min)+":"+str(t.tm_sec) )
        time.sleep(5)
        continue

    for tick in tickers:
       buf = par_fin(tick,str_delta_t,dict_proxies)
       Mass_df[tick].loc[buf['time']]=buf['Main Price']
         
       print_df = pd.concat([ print_df , Mass_df[tick]['Main Price'][-print_point:] ],axis=1)
       print_df.rename(columns = {'Main Price':tick},inplace = True)

       if (Mass_df[tick].shape[0] > 10000):
           Mass_df[tick].drop(df.index[0:3000]) # удаляем устаревшие записи
           
       Mass_df[tick].to_csv('data/full_data/'+tick+'.csv')

    clear()
    print(print_df.tail(print_point))
    print('количество записанных точек для первой в списке компании : %d ' % Mass_df[tickers[0]].shape[0] ) 
    print_df = pd.DataFrame()
    time.sleep(freq)




