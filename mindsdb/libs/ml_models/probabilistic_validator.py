from sklearn.naive_bayes import GaussianNB, ComplementNB, MultinomialNB
from mindsdb.libs.constants.mindsdb import NULL_VALUES
import numpy as np
import pickle


class ProbabilisticValidator():
    """
    # The probabilistic validator is a quick to train model used for validating the predictions
    of our main model
    # It is fit to the results our model gets on the validation set
    """
    _smoothing_factor = 1
    _value_bucket_probabilities = {}
    _probabilistic_model = None
    X_buff = None
    Y_buff = None


    def __init__(self, histogram ):
        """
        Chose the algorithm to use for the rest of the model
        As of right now we go with ComplementNB
        """
        # <--- Pick one of the 3
        self._probabilistic_model = ComplementNB(alpha=self._smoothing_factor)
        #, class_prior=[0.5,0.5]
        #self._probabilistic_model = GaussianNB()
        #self._probabilistic_model = MultinomialNB(alpha=self._smoothing_factor)
        self.X_buff = []
        self.Y_buff = []
        self.bucket_keys = [1] + [i+2 for i in range(len(histogram))]
        self.buckets = histogram

    def pickle(self):
        """
        Returns a version of self that can be serialized into mongodb or tinydb

        :return: The data of a ProbabilisticValidator serialized via pickle and decoded as a latin1 string
        """

        return pickle.dumps(self).decode(encoding='latin1')

    @staticmethod
    def unpickle(pickle_string):
        """
        :param pickle_string: A latin1 encoded python str containing the pickle data
        :return: Returns a ProbabilisticValidator object generated from the pickle string
        """
        return pickle.loads(pickle_string.encode(encoding='latin1'))

    @staticmethod
    def _closest(arr, value):
        """
        :return: The index of the member of `arr` which is closest to `value`
        """

        for i,ele in enumerate(arr):
            if ele > value:
                return i - 1

        return len(arr)

    # For contignous values we want to use a bucket in the histogram to get a discrete label
    def _get_value_bucket(self, value):
        """
        :return: The bucket in the `histogram` in which our `value` falls
        """
        # @TODO maybe use stats type in constructor
        # Support for non numeric values
        if type(value) == type(''):
            if value in self.buckets:
                i = self.buckets.index(value) + 2
            else:
                i = 1 # todo make sure that there is an index for values not in list
        else:
            i = self._closest(self.buckets, value) + 2
        return i


    def register_observation(self, features_existence, real_value, predicted_value):
        """
        # Register an observation in the validator's internal buffers

        :param features_existence: A vector of 0 and 1 representing the existence of all the features (0 == not exists, 1 == exists)
        :param real_value: The real value/label for this prediction
        :param predicted_value: The predicted value/label
        :param histogram: The histogram for the predicted column, which allows us to bucketize the `predicted_value` and `real_value`
        """

        real_value_b = self._get_value_bucket(real_value)

        X = [predicted_value, *features_existence]
        Y = [real_value_b]

        self.X_buff.append(X)
        self.Y_buff.append(Y)

    def partial_fit(self):
        """
        # Fit the probabilistic validator on all observations recorder that haven't been taken into account yet
        """

        self._probabilistic_model.partial_fit(self.X_buff, self.Y_buff, classes=self.bucket_keys)
        self.X_buff= []
        self.Y_buff= []

    def evaluate_prediction_accuracy(self, features_existence, predicted_value):
        """
        # Fit the probabilistic validator on an observation

        :param features_existence: A vector of 0 and 1 representing the existence of all the features (0 == not exists, 1 == exists)
        :param predicted_value: The predicted value/label
        :param histogram: The histogram for the predicted column, which allows us to bucketize the `predicted_value`
        :return: The probability (from 0 to 1) of our prediction being accurate (within the same histogram bucket as the real value)
        """

        X = [[predicted_value, *features_existence]]

        return self._probabilistic_model.predict_proba(np.array(X))[0][1]


if __name__ == "__main__":
    feature_rows = [
        [None,2,3]
        ,[2,2,3]
        ,[1,None,6]
        ,[0,3,None]
        ,[2,0,1]
        ,[None,2,3]
        ,[2,2,3]
        ,[1,None,6]
        ,[0,3,None]
        ,[2,0,1]
        ]

    values = [2,2,2,3,5,2,2,2,3,5]
    predictions = [2,2,2,3,2,2,2,2,3,2]

    pbv = ProbabilisticValidator()

    for i in range(len(feature_rows)):
        pbv.register_observation(feature_rows[i],values[i], predictions[i])

    print(pbv.evaluate_prediction_accuracy([1,2,3], 2))
    print(pbv.evaluate_prediction_accuracy([1,None,3], 3))
    print(pbv.evaluate_prediction_accuracy([None,0,2], 5))
    print(pbv.evaluate_prediction_accuracy([None,2,3], 2))
    print(pbv.evaluate_prediction_accuracy([None,None,3], 2))
    print(pbv.evaluate_prediction_accuracy([2,2,None], 2))
