# the script used to train the predictor

from time import time

from pandas import DataFrame
from pandas import Series
from pandas import concat
from pandas import read_csv
from pandas import datetime
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from sklearn.externals import joblib
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
# from keras.callbacks import TensorBoard
from math import sqrt
import matplotlib
matplotlib.use('agg')
from matplotlib import pyplot
from numpy import array

import numpy as np
import keras as ks
import pandas as pd

import logging

logger = logging.getLogger('myapp')
hdlr = logging.FileHandler('myapp.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)

# date-time parsing function for loading the dataset
def parser(x):
    return datetime.strptime(x, '%m-%d-%H-%M')

# convert time series into supervised learning problem
def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
    n_vars = 1 if type(data) is list else data.shape[1]
    df = DataFrame(data)
    cols, names = list(), list()
    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j+1, i)) for j in range(n_vars)]
    # forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [('var%d(t)' % (j+1)) for j in range(n_vars)]
        else:
            names += [('var%d(t+%d)' % (j+1, i)) for j in range(n_vars)]
    # put it all together
    agg = concat(cols, axis=1)
    agg.columns = names
    # drop rows with NaN values
    if dropnan:
        agg.dropna(inplace=True)
    return agg

# create a differenced series
def difference(dataset, interval=1):
    diff = list()
    for i in range(interval, len(dataset)):
        value = dataset[i] - dataset[i - interval]
        diff.append(value)
    return Series(diff)

# transform series into train and test sets for supervised learning
def prepare_data(series, n_test, n_lag, n_seq):
    # extract raw values
    print('preparing data\n')
    raw_values = series.values
    # transform data to be stationary
    print('transform data to be stationary\n')
    diff_series = difference(raw_values, 1)
    diff_values = diff_series.values
    diff_values = diff_values.reshape(len(diff_values), 1)
    print(len(diff_values))
    diff_values = np.nan_to_num(diff_values)
    print(len(diff_values))
    # rescale values to -1, 1
    print('rescale values to -1, 1\n')
    scaler = MinMaxScaler(feature_range=(-1, 1))
    scaled_values = scaler.fit_transform(diff_values)
    scaled_values = scaled_values.reshape(len(scaled_values), 1)
    joblib.dump(scaler, 'my_scaler.save') 
    # transform into supervised learning problem X, y
    print('transform into supervised learning problem X, y\n')
    supervised = series_to_supervised(scaled_values, n_lag, n_seq)
    supervised_values = supervised.values
    # split into train and test sets
    print('split into train and test sets\n')
    train, test = supervised_values[0:-n_test], supervised_values[-n_test:]
    return scaler, train, test

# fit an LSTM network to training data
# def fit_lstm(train, test, scaler, n_lag, n_seq, n_batch, nb_epoch, n_neurons, n_test):
#     # reshape training into [samples, timesteps, features]
#     X, y = train[:, 0:n_lag], train[:, n_lag:]
#     X = X.reshape(X.shape[0], 1, X.shape[1])
#     # design network
#     model = Sequential()
#     model.add(LSTM(n_neurons, batch_input_shape=(n_batch, X.shape[1], X.shape[2]), stateful=True))
#     model.add(Dense(y.shape[1]))
#     model.compile(loss='mean_squared_error', optimizer='adam')

#     # tensorboard = TensorBoard(log_dir="logs/{}".format(time()))

#     # model.fit(X, y, epochs=nb_epoch, batch_size=n_batch, verbose=1, shuffle=False)
#     # return model
#     # fit network
#     for i in range(nb_epoch):
#         print('start traing epoch %d', i)
#         model.fit(X, y, epochs=1, batch_size=n_batch, verbose=1, shuffle=False)
#         model.reset_states()
        
#         model.save(str(i) + '_my_model_32.h5')
#         forecasts = make_forecasts(model, n_batch, train, test, n_lag, n_seq)
#         # inverse transform forecasts and test
#         forecasts = inverse_transform(series, forecasts, scaler, n_test+2)
#         actual = [row[n_lag:] for row in test]
#         actual = inverse_transform(series, actual, scaler, n_test+2)
#         evaluate_forecasts(actual, forecasts, n_lag, n_seq)
#     return model

# make one forecast with an LSTM,
def forecast_lstm(model, X, n_batch):
    # reshape input pattern to [samples, timesteps, features]
    X = X.reshape(1, 1, len(X))
    # make forecast
    forecast = model.predict(X, batch_size=n_batch)
    # convert to array
    return [x for x in forecast[0, :]]

# evaluate the persistence model
def make_forecasts(model, n_batch, train, test, n_lag, n_seq):
    forecasts = list()
    for i in range(len(test)):
        X, y = test[i, 0:n_lag], test[i, n_lag:]
        # make forecast
        forecast = forecast_lstm(model, X, n_batch)
        # store the forecast
        forecasts.append(forecast)
    return forecasts

# invert differenced forecast
def inverse_difference(last_ob, forecast):
    # invert first forecast
    inverted = list()
    inverted.append(forecast[0] + last_ob)
    # propagate difference forecast using inverted first value
    for i in range(1, len(forecast)):
        inverted.append(forecast[i] + inverted[i-1])
    return inverted

# inverse data transform on forecasts
def inverse_transform(series, forecasts, scaler, n_test):
    inverted = list()
    for i in range(len(forecasts)):
        # create array from forecast
        forecast = array(forecasts[i])
        forecast = forecast.reshape(1, len(forecast))
        # invert scaling
        inv_scale = scaler.inverse_transform(forecast)
        inv_scale = inv_scale[0, :]
        # invert differencing
        index = len(series) - n_test + i - 1
        last_ob = series.values[index]
        inv_diff = inverse_difference(last_ob, inv_scale)
        # store
        inverted.append(inv_diff)
    return inverted

# evaluate the RMSE for each forecast time step
def evaluate_forecasts(epoch, test, forecasts, n_lag, n_seq):
    logger.info("evaluating epoch" + str(epoch))
    for i in range(n_seq):
        actual = [row[i] for row in test]
        predicted = [forecast[i] for forecast in forecasts]
        rmse = sqrt(mean_squared_error(actual, predicted))
        print('t+%d RMSE: %f' % ((i+1), rmse))
        logger.info('t+%d RMSE: %f' % ((i+1), rmse))

# plot the forecasts in the context of the original dataset
def plot_forecasts(series, forecasts, n_test):
    # plot the entire dataset in blue
    colors = ['red', 'blue', 'green']
    pyplot.plot(series.values[-n_test-1:])
    # plot the forecasts in red
    print(len(forecasts))
    yaxis1 = []
    yaxis1.append(0)
    yaxis2 = []
    yaxis2.append(0)
    yaxis3 = []
    yaxis3.append(0)
    for i in range(len(forecasts)):
        #print(len(forecasts[i]))
        off_s = len(series) - n_test + i - 1
        off_e = off_s + len(forecasts[i]) + 1
        #xaxis = [x - len(series) + n_test for x in range(off_s, off_e)]
        xaxis = i + 1
        #yaxis = [series.values[off_s]] + forecasts[i]
        yaxis1.append(forecasts[i][0])
        yaxis2.append(forecasts[i][1])
        yaxis3.append(forecasts[i][2])
        #pyplot.plot(xaxis, yaxis, color=colors[i%3])
#     # show the plot
    pyplot.plot(yaxis1, color='red')
    pyplot.plot(yaxis1, color='yellow')
    pyplot.plot(yaxis1, color='green')
    pyplot.savefig('fig.eps')
#     pyplot.show()

# load dataset
print('starting loading data\n')
series = read_csv('tweet_load.csv', header=0, parse_dates=[0], index_col=0, squeeze=True, date_parser=parser)
series = series[pd.notnull(series)]
print('data loaded\n')
# configure
n_lag = 1 #given 1 current data, forcast the next 3. must be 1 to support online
n_seq = 50
n_test = 1000 #size of test set
n_epochs = 50
n_batch = 1 #must be 1 because we want online prediction
n_neurons = 32
# prepare data
scaler, train, test = prepare_data(series, n_test, n_lag, n_seq)
# fit model
print('start training')

X, y = train[:, 0:n_lag], train[:, n_lag:]
X = X.reshape(X.shape[0], 1, X.shape[1])
# design network
model = Sequential()
model.add(LSTM(n_neurons, batch_input_shape=(n_batch, X.shape[1], X.shape[2]), stateful=True))
model.add(Dense(y.shape[1]))
model.compile(loss='mean_squared_error', optimizer='adam')

# fit network
for i in range(nb_epoch):
    print('start traing epoch %d', i)
    model.fit(X, y, epochs=1, batch_size=n_batch, verbose=1, shuffle=False)
    model.reset_states()
    
    model.save(str(i) + '_my_model_32.h5')
    forecasts = make_forecasts(model, n_batch, train, test, n_lag, n_seq)
    # inverse transform forecasts and test
    forecasts = inverse_transform(series, forecasts, scaler, n_test+2)
    actual = [row[n_lag:] for row in test]
    actual = inverse_transform(series, actual, scaler, n_test+2)
    evaluate_forecasts(i, actual, forecasts, n_lag, n_seq)

# model = fit_lstm(train, test, scaler, n_lag, n_seq, n_batch, n_epochs, n_neurons, n_test)
# model.save('my_model_32.h5')
#model = ks.models.load_model('my_model.h5')
# make forecasts
# forecasts = make_forecasts(model, n_batch, train, test, n_lag, n_seq)
# # inverse transform forecasts and test
# forecasts = inverse_transform(series, forecasts, scaler, n_test+2)
# actual = [row[n_lag:] for row in test]
# actual = inverse_transform(series, actual, scaler, n_test+2)
# # evaluate forecasts
# evaluate_forecasts(actual, forecasts, n_lag, n_seq)
# plot forecasts
# plot_forecasts(series, forecasts, n_test+2)