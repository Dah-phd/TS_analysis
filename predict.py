import numpy as np
from sklearn import linear_model
try:
    from . import data_tests
except Exception:
    import data_tests


class ARIMA:
    """
    Class ARIMA is used to predict time series data.

    The model combines AR - autoregression and MA - moving averages,
    also if the initial data is not stationary it integrates it until so.

    The model is brute-forced, or it will calculate all the possible models,
    such as AR1MA2, AR2MA2, AR3MA2 ... AR(lags)MA(lags),
    then select the one with least historic error.

    # Params####:

        data: imput data list of variables, starting from newst to oldest data,
        could be numpy array.

        lags: by default 31, could be changed,
        it determines how much possible lags will be tested.
        THE CALCULATION GROW EXPONENTIALLY!

    Every instance of the class will be stored in list current_models
    (call with any self.current_models)
    """
    current_models = []

    def __init__(self, data, lags=30):
        """
        Constructor params(could be invoked):
        -------------------------------------
            self.integrations: automated - returns the integrations done
            to make the data stationary.

            self.all_models: stores information on all models solved.

            self.data: input - initial data.

            self.lags: input - lags to be tested.

            self._test_data() and self._turn_to_np() called private methods.

            self.base: generated, backup of the used data, prior numpy.

            self.best: generated by self.build() - returns the best model,
            after testing all generated.

            self.prediction: generated by self.predict - returns initial
            prediction of the found best model.

        """
        self.current_models.append(self)
        self.integrations = 0
        self.all_models = {}
        self.data = data
        self.lags = lags+1
        self._test_data()

    def _test_data(self):
        # Private: checks stationarity by calling other module.
        # Private: transform into numpy array with proper shape/bachup.
        self.base = np.copy(self.data)
        self.integrations, self.data = data_tests.stationarity.forceSTAT(
            self.data)
        self.data = np.array(self.data).reshape(-1, 1)

    def _moving_averages(self, lag):
        # returns np array list of moving averages base on the lag.
        result = []
        for x, _ in enumerate(self.data[lag:]):
            result.append(np.mean(self.data[1+x:lag+x]))
        return np.array(result).reshape(-1, 1)

    def _equlize(self, AR, t1, MA, t):
        # balances the lenght of imput data
        if t > t1:
            base = self.data[:-t]
            AR = AR[:-(t-t1)]
        elif t1 > t:
            base = self.data[:-t1]
            MA = MA[:-(t1-t)]
        elif t1 == t:
            base = self.data[:-t]
        else:
            return 'Somethin went wrong'
        factor = np.hstack((AR, MA))
        return base, factor

    def _check_all_models(self):
        # returns the best model
        key, spec = 'model', {'R': 0}
        for t in self.all_models.items():
            if spec['R'] < t[1]['R']:
                key, spec = t[0], t[1]
        if key != 'model':
            return {key: spec}

    def build(self):
        '''
        Trigering the build function solves all models in order to
        find the best model, by score, then returns it as a result.
        Also generates self.all_models and self.best to store the information.
        '''
        for t in range(2, self.lags):
            MA = self._moving_averages(t)
            for t1 in range(1, self.lags):
                AR = self.data[t1:]
                base, factor = self._equlize(AR, t1, MA, t)
                model = linear_model.LinearRegression(
                    fit_intercept=False).fit(factor, base)
                regresion_values = {'R': model.score(factor, base)**2,
                                    'AR': model.coef_[0][0],
                                    'MA': model.coef_[0][1]}
            self.all_models['AR'+str(t1) +
                            'I'+str(self.integrations) +
                            'MA'+str(t)
                            ] = regresion_values
        self.best = self._check_all_models()
        return self.best

    def _decode_key(self, key):
        if 'I' in key:
            AR, MA = key.split('I')
            AR = int(AR[2:])
            MA = int(MA.split('MA')[-1])
            key = (AR, MA)
        elif 'MA' in key:
            AR, MA = key.split('MA')
            AR
            key = (int(AR), int(MA))
        else:
            key = ('broken key', 'broken key')
        return key

    def _key_integrity(self, key):
        # checks for expected mistakes in the key and corrects
        # if possible and close to normal
        if 'I' in key:
            key = key.split('I')
            MA = key[1].split('MA')
            key = key[0]+'I'+str(self.integrations)+'MA'+MA[1]
        elif 'MA' in key:
            key = key.split('MA')
            key = key[0]+'I'+str(self.integrations)+key[1]
        else:
            key = 'broken key'
        return key

    def predict(self, model='best', periods=31):
        '''
        Predict function:
        -----------------
        Use to predict expected values for the class, normal use:
        First use build, then invoke and it will generated 30 predictions.
        Starting with the most furthest and reachin to the closes (t+30...t+1).

        Params:
        -------
            model: default 'best', use the self.best model,
            could be given specific model.
            Example AR1MA1 or AR1I1MA1 in that case the function
            could be triggered prior build and make prediction.
            ### DATA STILL WILL BE INTEGRATED BY self.integration ###
        '''
        if model == 'best':
            key = next(iter(self.best.keys()))
            model_dict = self.best[key]
        else:
            key = self._key_integrity(model)
            model_dict = self.all_models[key]
        AR, MA = self._decode_key(key)
        data = AR if AR > MA else MA
        data = AR if AR > MA else MA
        data = self.data[:data]
        base = self.base[:self.integrations+1]
        for t in range(periods):
            result = data[AR-1]*model_dict['AR'] + \
                np.mean(data[:MA]*model_dict['MA'])
            data = np.insert(data, 0, result, 0)
            if self.integrations > 0:
                add = [base[0]]
                for t in range(self.integrations):
                    add.append(np.diff(base[:t+2]))
                base = np.insert(base, 0, result+sum(add))
            else:
                base = np.insert(base, 0, result)
            self.prediction = {'key': key,
                               'periods(t)': 't+n ... t+3, t+2, t+1',
                               'prediction': data[:periods],
                               're-integrated': base[:-(self.integrations+1)]}
        return self.prediction

    def __str__(self):
        # print the R2 of the best model and the model itself
        if self.best:
            self.best
        else:
            'Model builder'


class LinearProjection:
    '''
    Linear projection is modeling the expected values of a timeseries
    by using as factor the change of the period i.e. (1,2,3,4,5...n).

    current_models (invoked by self.current_models) - lists all instances
    of the class.

    #######
    self.build() is used to trigger the solution of the model.
        generates:
            self.rsq = score of the model
            self.intercept = constant queficient
            self.beta = coeficient of the relation
        !!! The model dose not consider the possibility of 0 intercept !!!

    self.predict() is used to generate predictions.

    #######
    Required params:

    data: The input data should include list or numpy array starting
    with the newest data to the oldest.

    integrate: optional bool, default = False.
    Determines should predict force stationarity.
    '''
    current_models = []

    def __init__(self, data, integrate=False):
        '''
        Constructor params:
        ------------------
        self.data: input data - list/np.array

        self.periods: generated, to track lenght of the timeseries

        self.integrations: generated, states the number of
        integrations if any.

        self._turn_to_np(): private method
        buils self.base - copy of the initial data.
        '''
        self.current_models.append(self)
        self.data = data
        self.periods = len(self.data)+1
        self.integrations = 0
        self._turn_to_np(integrate)

    def _turn_to_np(self, integrate):
        # convert to numpy and makes a backup
        if integrate:
            self.integrations, self.data = data_tests.forceSTAT(self.data)
        self.data = np.array(self.data).reshape(-1, 1)
        self.base = np.copy(self.data)

    def build(self):
        '''
        self.build(), no params is used to initialize the solution of the
        linear model, if not triggered the predict function will automate it.
        '''
        factor = [t for t in range(1, self.periods)]
        factor.reverse()
        factor = np.array(factor).reshape(-1, 1)
        model = linear_model.LinearRegression().fit(factor, self.data)
        self.rsq, self.intercept, self.beta = (model.score(factor,
                                                           self.data)**2,
                                               model.intercept_[0],
                                               model.coef_[0][0])

    def predict(self, periods=30):
        '''
        self.predict is used to generate predictions from the build model,
        if no model is build it will build it. Also stores the predictions in
        self.prediction

        Params:
        periods: int, how long should the prediction be, default is 30 periods
        '''
        if not self.rsq:
            self.build()
        x = self.periods
        periods_ = []
        predictions = []
        for _ in range(periods+1):
            y = x*self.beta+self.intercept
            predictions.insert(0, y)
            periods_.insert(0, x)
            x += 1
        self.prediction = {'R': self.rsq,
                           'periods(t)': periods_, 'prediction': predictions}
        return self.prediction


class _simple_lag:
    current_models = []
    # parent class

    def __init__(self, data, n_factors, lags, integrate=True):
        self.current_models.append(self)
        self.data = data
        self.lags = lags+1
        self.all_models = {}
        self.n_factors = n_factors
        self._turn_to_np

    def _turn_to_np(self, integrate):
        # convert to numpy and makes a backup
        if integrate:
            self.integrations, self.data = data_tests.forceSTAT(self.data)
        self.data = np.array(self.data).reshape(-1, 1)
        self.base = np.copy(self.data)

    def _check_all_models(self):
        # under the condition that we use dict starting with the model than R
        key, spec = 'model', {'R': 0}
        for t in self.all_models.items():
            if t[1]['R'] > spec['R']:
                key, spec = t[0], t[1]
        if key != 'model':
            return {key: spec}

    def _cascade(self, n, m_type, model=''):
        if n >= 1:
            for t in range(2 if m_type == 'MA' else 1, self.lags):
                self._cascade(n-1, model=model+m_type+str(t), m_type=m_type)
            return
        elif n == 0:
            model_list = model.split(m_type)
            model_list.pop(0)
            model_list = [int(t) for t in model_list]
            factor = np.hstack(
                [np.array(
                    self._solve(t, max(model_list))).reshape(-1, 1)
                 for t in model_list]
            )
            base = self.data[:-max(model_list)]
            model_reg = linear_model.LinearRegression().fit(factor, base)
            self.all_models[model] = {
                str(n)+'_'+m_type: t for n, t in enumerate(
                    model_reg.coef_,
                    start=1)
            }
            self.all_models[model]['Intercept'] = model_reg.intercept_
            self.all_models[model]['R'] = model_reg.score(factor, base)**2
        else:
            print('n_factors incorrect!')


class AutoReg(_simple_lag):
    # first child using multiple autoregressive factors (3 def)
    # make predictions
    def __init__(self, data, lags=30, n_factors=3, integrate=True):
        super().__init__(data, n_factors, lags, integrate=True)

    def _solve(self, lag, max_lenght):
        end = lag-max_lenght if lag != max_lenght else None
        return self.data[lag:end]

    def build(self):
        self._cascade(self.n_factors, m_type='AR')
        self.best = self._check_all_models()
        return self.best

    def predict(self, periods=30, model='best'):
        if model == 'best':
            key = next(iter(self.best.keys()))
            spec = self.best[key]
        else:
            key = model
            spec = self.all_models[key]
        key = key.split('AR')
        key.pop(0)
        key = [int(t) for t in key]
        data = self.data[:self.lags]
        for _ in range(periods+1):
            base = 0
            for n, t1 in enumerate(key, start=1):
                base += spec[str(n)+'_AR']*data[t1-1]
            data = np.insert(data, 0, base+spec['Intercept'])
        self.prediction = {model: data[:periods+1],
                           'periods': 't+n ... t+3, t+2, t+1'}
        return self.prediction


class MovingAvg(_simple_lag):
    # first child using multiple autoregressive factors (3 def)
    # make predictions
    def __init__(self, data, lags=30, n_factors=3, integrate=True):
        super().__init__(data, n_factors, lags, integrate=True)

    def _solve(self, lag, max_lenght):
        return np.array(
            [np.mean(
                self.data[0+t: lag+t]) for t in range(len(
                    self.data[max_lenght:]))
             ])

    def build(self):
        self._cascade(self.n_factors, m_type='MA')
        self.best = self._check_all_models()
        return self.best

    def predict(self, periods=30, model='best'):
        if model == 'best':
            key = next(iter(self.best.keys()))
            spec = self.best[key]
        else:
            key = model
            spec = self.all_models[key]
        key = key.split('MA')
        key.pop(0)
        key = [int(t) for t in key]
        data = self.data[:self.lags]
        for _ in range(periods+1):
            base = 0
            for n, t1 in enumerate(key, start=1):
                base += spec[str(n)+'_MA']*np.mean(data[0:t1-1])
            data = np.insert(data, 0, base+spec['Intercept'])
        self.prediction = {model: data[:periods+1],
                           'periods': 't+n ... t+3, t+2, t+1'}
        return self.prediction
