import numpy as np
from sklearn import linear_model
from concurrent.futures import ProcessPoolExecutor as PPE
from concurrent.futures import as_completed


if __name__ == "__main__":
    import data_tests
else:
    from modules import data_tests
# ORDER IS FROM NEWEST (UP) TO OLDEST (DOWN) DATA


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

    def __init__(self, data, lags=90):
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

    def _solve(self, t):
        # possble error is to trigger 136:
        # _check_all_models before finishing the processes
        MA = self._moving_averages(t)
        for t1 in range(1, self.lags):
            AR = self.data[t1:]
            base, factor = self._equlize(AR, t1, MA, t)
            model = linear_model.LinearRegression(
                fit_intercept=False).fit(factor, base)
            regresion_values = {'R': model.score(factor, base)**2,
                                'AR': model.coef_[0][0],
                                'MA': model.coef_[0][1]}
        return ('AR'+str(t1) +
                'I'+str(self.integrations) +
                'MA'+str(t), regresion_values)

    def build(self):
        '''
        Trigering the build function solves all models in order to
        find the best model, by score, then returns it as a result.
        Also generates self.all_models and self.best to store the information.
        '''
        with PPE() as exe:
            ppe = [exe.submit(self._solve, lag) for lag in range(2, self.lags)]
        for proc in as_completed(ppe):
            key, spec = proc.result()
            self.all_models[key] = spec
        del ppe
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
            key = (AR, MA)
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
            add = [base[0]]
            for t in range(self.integrations):
                add.append(np.diff(base[:t+2]))
            result = data[AR-1]*model_dict['AR'] + \
                np.mean(data[:MA]*model_dict['MA'])
            data = np.insert(data, 0, result, 0)
            base = np.insert(base, 0, result+sum(add))
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
